import os
from dotenv import load_dotenv

# 1. CHARGEMENT DU .ENV EN PREMIER ABSOLU (Avant d'importer le Gateway)
load_dotenv()

from flask import Flask, jsonify
from src.routes.gateway_routes import gateway_bp

app = Flask(__name__)

# 2. Enregistrement du Blueprint du Gateway
app.register_blueprint(gateway_bp)


# 3. Injection des Headers de Sécurité HTTP (Protection du navigateur)
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# 4. Gestion globale des erreurs
@app.errorhandler(404)
def handle_404(e):
    return jsonify({"error": "Route introuvable."}), 404

@app.errorhandler(500)
def handle_500(e):
    return jsonify({"error": "Une erreur interne du serveur est survenue."}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)