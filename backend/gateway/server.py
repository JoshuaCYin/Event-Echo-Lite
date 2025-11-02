"""
API gateway: combines auth, events, and venues blueprints.
This is the local entrypoint for development.
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging
import sys
from dotenv import load_dotenv

load_dotenv()

# Basic console logging during API requests
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s")


def create_app():
    """
    Application factory for creating the Flask app.
    """
    app = Flask(__name__)
    CORS(app)

    # Add the project root to Python path
    # This allows imports like 'from backend.auth_service.routes import auth_bp'
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    # --- Register Blueprints ---
    try:
        from backend.auth_service.routes import auth_bp
        from backend.events_service.routes import events_bp
        from backend.venues_service.routes import venues_bp

        app.register_blueprint(auth_bp, url_prefix="/auth")
        app.register_blueprint(events_bp, url_prefix="/events")
        app.register_blueprint(venues_bp, url_prefix="/venues")
        
        logging.info("All blueprints registered successfully.")

    except ImportError as e:
        logging.error(f"Failed to import blueprints. Module not found: {e}")
        sys.exit(1)

    # --- Basic Health Checkpoints ---
    @app.route("/")
    def ping():
        """
        Root URL for simple 'online' check.
        """
        return jsonify({"status": "gateway_ok"}), 200

    @app.route("/health")
    def health():
        """
        Health check endpoint.
        """
        return jsonify({"status": "ok"}), 200
    
    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("GATEWAY_PORT", 5050)) # Use 5050 from .env
    app.run(host="0.0.0.0", port=port, debug=True)
