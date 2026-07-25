from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "Gateway service is up and running!"}), 200

# Exemple de route pour rediriger vers un autre service
@app.route("/auth/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def auth_proxy(path):
    # Ici, vous implémenteriez la logique de redirection vers le service d'authentification
    # Pour l'instant, c'est un placeholder
    return jsonify({"message": f"Proxying request to Auth service: /{path}"}), 200

@app.route("/transactions/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def transactions_proxy(path):
    # Logique de redirection vers le service de transactions
    return jsonify({"message": f"Proxying request to Transactions service: /{path}"}), 200

@app.route("/payment/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def payment_proxy(path):
    # Logique de redirection vers le service de paiement
    return jsonify({"message": f"Proxying request to Payment service: /{path}"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
