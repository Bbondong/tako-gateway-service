from flask import Flask
from src.routes.gateway_routes import gateway_bp

app = Flask(__name__)
app.register_blueprint(gateway_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
