"""
API gateway: combines auth and events blueprints and runs a single Flask app.
Defines the app, registers routes/blueprints, and calls app.run() to listen for HTTP requests on a port.
This is the local entrypoint for development.
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# basic console logging during API requests
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s")


def create_app():
    app = Flask(__name__)
    CORS(app)

    # register blueprints
    from backend.auth_service.routes import auth_bp
    from backend.events_service.routes import events_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(events_bp, url_prefix="/events")

    @app.route("/")
    def ping():
        return jsonify({"status": "ok"}), 200

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"}), 200
    
    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("GATEWAY_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)