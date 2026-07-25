from flask import Blueprint, jsonify, request
import requests

gateway_bp = Blueprint("gateway", __name__)

# Configuration des services (peut être déplacé vers un fichier de config ou des variables d'environnement)
SERVICE_URLS = {
    "auth": "http://localhost:5001", # URL du service d'authentification
    "transactions": "http://localhost:5002", # URL du service de transactions
    "payment": "http://localhost:5003" # URL du service de paiement
}

def proxy_request(service_name, path):
    target_url = f"{SERVICE_URLS[service_name]}/{path}"
    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers={key: value for (key, value) in request.headers if key != 'Host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False)

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]

        return jsonify(resp.json()), resp.status_code, headers
    except requests.exceptions.RequestException as e:
        return jsonify({"message": f"Service {service_name} unavailable", "error": str(e)}), 503

@gateway_bp.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "Gateway service is up and running!"}), 200

@gateway_bp.route("/auth/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def auth_proxy(path):
    return proxy_request("auth", path)

@gateway_bp.route("/transactions/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def transactions_proxy(path):
    return proxy_request("transactions", path)

@gateway_bp.route("/payment/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def payment_proxy(path):
    return proxy_request("payment", path)
