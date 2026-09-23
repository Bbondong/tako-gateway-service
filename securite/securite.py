import os
import re
import time
import logging
import hashlib
from flask import request, jsonify
from werkzeug.utils import secure_filename

# --- CONFIGURATION DU LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 5 Mo max

# --- RATE LIMITING & BRUTE-FORCE ---
RATE_LIMIT = 50
RATE_LIMIT_WINDOW = 60
BAN_STAGES = [300, 600, 1200, 1800, 3600]

ip_requests = {}
ip_bans = {}

SQLI_PATTERN = re.compile(
    r"(?i)(UNION\s+SELECT|DROP\s+TABLE|INSERT\s+INTO|UPDATE\s+.*SET|DELETE\s+FROM|--|;\s*--|OR\s+1\s*=\s*1|AND\s+1\s*=\s*1|<script|eval\(|\.\./)"
)


def register_infraction(ip):
    """
    Applique une pénalité progressive à une IP malveillante.
    """
    if ip not in ip_bans:
        ip_bans[ip] = {'level': 0, 'ban_until': time.time() + BAN_STAGES[0], 'permanent': False}
    elif not ip_bans[ip]['permanent']:
        next_level = ip_bans[ip]['level'] + 1
        if next_level >= len(BAN_STAGES) - 1:
            ip_bans[ip]['level'] = next_level
            ip_bans[ip]['permanent'] = True
            ip_bans[ip]['ban_until'] = float('inf')
        else:
            ip_bans[ip]['level'] = next_level
            ip_bans[ip]['ban_until'] = time.time() + BAN_STAGES[next_level]
    
    logger.warning(f"[INFRACTION] Pénalité appliquée à l'IP {ip} (Niveau: {ip_bans[ip]['level']})")


def verify_request_security():
    """
    Filtre principal du Gateway : Vérification Clé Client + WAF + Anti-BruteForce
    """
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()

    # ---------------------------------------------------------
    # 1. VÉRIFICATION DE LA CLÉ API CLIENT (App Mobile / Web)
    # ---------------------------------------------------------
    client_key = request.headers.get("X-Client-Key")
    
    # On récupère la clé dynamique pour s'assurer qu'elle est bien chargée (utile si on utilise dotenv)
    expected_key = os.environ.get("TAKO_CLIENT_API_KEY")

    # Legacy routes retain the old client key. The public versioned API uses JWT
    # on account-scoped endpoints; a key embedded in Flutter cannot remain secret.
    if not request.path.startswith('/api/v1/'):
        if not client_key or not expected_key or client_key != expected_key:
            register_infraction(client_ip)
            return jsonify({"error": "Clé API client manquante ou invalide."}), 401

    # ---------------------------------------------------------
    # 2. VÉRIFICATION BANNISSEMENT IP (BRUTE-FORCE & ROBOTS)
    # ---------------------------------------------------------
    if client_ip in ip_bans:
        ban_info = ip_bans[client_ip]
        if ban_info['permanent']:
            return jsonify({"error": "Votre IP a été bannie définitivement suite à des comportements malveillants."}), 403
        
        if time.time() < ban_info['ban_until']:
            remaining_min = max(1, int((ban_info['ban_until'] - time.time()) // 60))
            return jsonify({"error": f"Accès suspendu. Réessayez dans {remaining_min} minute(s)."}), 429

    # ---------------------------------------------------------
    # 3. RATE LIMITING (BRUTE-FORCE)
    # ---------------------------------------------------------
    current_time = time.time()
    bearer = request.headers.get('Authorization', '')
    rate_key = client_ip
    if request.path.startswith('/api/v1/') and bearer.startswith('Bearer '):
        # Users behind a shared mobile NAT must not exhaust one another's quota.
        rate_key += ':' + hashlib.sha256(bearer.encode()).hexdigest()
    if rate_key not in ip_requests:
        ip_requests[rate_key] = []

    ip_requests[rate_key] = [t for t in ip_requests[rate_key] if current_time - t < RATE_LIMIT_WINDOW]

    if len(ip_requests[rate_key]) >= RATE_LIMIT:
        logger.warning(f"[RATE LIMIT] Brute-force détecté pour l'IP {client_ip}")
        register_infraction(client_ip)
        ban_level = ip_bans[client_ip]['level']
        ban_minutes = BAN_STAGES[ban_level] // 60
        return jsonify({"error": f"Brute-force/Bot détecté. IP bloquée {ban_minutes} minute(s)."}), 429

    ip_requests[rate_key].append(current_time)

    # ---------------------------------------------------------
    # 4. PARE-FEU WAF (Injections SQL & Scripts)
    # ---------------------------------------------------------
    def check_payload(data_str):
        if data_str and SQLI_PATTERN.search(str(data_str)):
            logger.warning(f"[WAF] Injection SQL/XSS détectée venant de {client_ip}: {data_str}")
            register_infraction(client_ip)
            return True
        return False

    for _, value in request.args.items():
        if check_payload(value):
            return jsonify({"error": "Attaque détectée dans l'URL."}), 400

    if request.is_json:
        try:
            json_payload = request.get_json(silent=True)
            if json_payload and check_payload(str(json_payload)):
                return jsonify({"error": "Payload JSON suspect."}), 400
        except Exception:
            pass

    for _, value in request.form.items():
        if check_payload(value):
            return jsonify({"error": "Formulaire malveillant détecté."}), 400

    # ---------------------------------------------------------
    # 5. SÉCURITÉ DES FICHIERS
    # ---------------------------------------------------------
    if request.files:
        for key in request.files:
            file_obj = request.files[key]
            if file_obj and file_obj.filename:
                is_safe, err_msg = is_safe_file(file_obj)
                if not is_safe:
                    logger.warning(f"[WAF FICHIER] Fichier refusé ({file_obj.filename}): {err_msg}")
                    register_infraction(client_ip)
                    return jsonify({"error": f"Fichier rejeté ({key}) : {err_msg}"}), 400

    return None


def is_safe_file(file):
    if not file or not file.filename:
        return False, "Fichier invalide."

    filename = secure_filename(file.filename)

    if filename.count('.') > 1:
        return False, "Doubles extensions interdites."

    if '.' not in filename:
        return False, "Extension manquante."

    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Extension '.{ext}' non autorisée."

    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)

    if size > MAX_FILE_SIZE:
        return False, "Fichier supérieur à 5 Mo."

    return True, filename
