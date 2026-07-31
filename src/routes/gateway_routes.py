import os
import requests
from flask import Blueprint, jsonify, request, redirect  # Importation de redirect
from securite.securite import verify_request_security

gateway_bp = Blueprint("gateway", __name__)

SERVICE_URLS = {
    "auth": os.getenv("AUTH_SERVICE_URL"),
    "transactions": os.getenv("TRANSACTIONS_SERVICE_URL"),
    "payment": os.getenv("PAYMENT_SERVICE_URL")
}

# Clé secrète uniquement partagée entre le Gateway et les Microservices
INTERNAL_API_KEY = os.getenv("TAKO_API_KEY_INTER_SERVICES")


@gateway_bp.before_request
def apply_security_filter():
    # Exemption de la racine "/" pour permettre la redirection sans exiger de clé client
    if request.path == "/":
        return None

    # Vérifie la clé client, l'IP, le brute-force et les injections SQL pour toutes les autres routes
    security_error = verify_request_security()
    if security_error:
        return security_error


def proxy_request(service_name, path):
    target_base = SERVICE_URLS.get(service_name)
    if not target_base:
        return jsonify({"message": f"Service {service_name} non configuré."}), 500

    target_url = f"{target_base}/{path}"

    # Copie des entêtes + Nettoyage de la clé client + Injection de la clé interne
    headers = {key: value for (key, value) in request.headers if key.lower() not in ['host', 'x-client-key']}
    headers["X-Internal-Key"] = INTERNAL_API_KEY  # Clé serveur-à-serveur

    try:
        data = request.get_data() if not request.files else None
        files = {key: (f.filename, f.stream, f.content_type) for key, f in request.files.items()} if request.files else None

        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=request.args,
            data=data,
            files=files,
            cookies=request.cookies,
            allow_redirects=False
        )

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]

        try:
            return jsonify(resp.json()), resp.status_code, response_headers
        except Exception:
            return resp.content, resp.status_code, response_headers

    except requests.exceptions.RequestException as e:
        return jsonify({"message": f"Le service '{service_name}' est indisponible.", "error": str(e)}), 503


@gateway_bp.route("/", methods=["GET"])
def redirect_to_tako():
    # Redirection automatique vers le site web officiel
    return redirect("https://tako.africa", code=302)

@gateway_bp.route("/auth/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def auth_proxy(path):
    return proxy_request("auth", path)

@gateway_bp.route("/transactions/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def transactions_proxy(path):
    return proxy_request("transactions", path)

@gateway_bp.route("/payment/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def payment_proxy(path):
    return proxy_request("payment", path)