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

print("DEBUG_DATABASE_URL:", os.getenv("DATABASE_URL")) # For database URL debugging

# Basic console logging during API requests
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s")

def create_app() -> Flask:
    """
    Application factory for creating the Flask app.
    
    Returns:
        Flask: The configured Flask application.
    """
    app = Flask(__name__)
    # Configure CORS for S3 bucket
    # For local development include common dev origins (add more as needed)
    CORS(app, resources={
        r"/*": {
            "origins": [
                "http://event-echo-s3.s3-website.us-east-2.amazonaws.com",  # S3 website endpoint
                "http://localhost:5500",  # Local development (some editors)
                "http://localhost:5050",  # Local development gateway (if served from same host)
                "http://localhost:8080",  # Local static server used in this workspace
                "null"  # For local file testing
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    # Add the project root to Python path
    # This allows imports like 'from backend.auth_service.routes import auth_bp'
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    # --- REGISTER BLUEPRINTS ---
    try:
        from backend.auth_service.routes import auth_bp
        from backend.events_service.routes import events_bp
        from backend.venues_service.routes import venues_bp
        from backend.ai_service.routes import ai_blueprint
        from backend.planning_service.routes import planning_bp

        app.register_blueprint(auth_bp, url_prefix="/auth")
        app.register_blueprint(events_bp, url_prefix="/events")
        app.register_blueprint(venues_bp, url_prefix="/venues")
        app.register_blueprint(ai_blueprint, url_prefix="/ai")
        app.register_blueprint(planning_bp, url_prefix='/planning')
        
        logging.info("All blueprints registered successfully.")

    except ImportError as e:
        logging.error(f"Failed to import blueprints. Module not found: {e}")
        sys.exit(1)

    # --- BASIC HEALTH CHECKPOINTS ---
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
    port = int(os.getenv("GATEWAY_PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=True)
