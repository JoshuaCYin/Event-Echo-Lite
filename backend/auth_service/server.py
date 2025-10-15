# """
# Authentication service
# - Runs on port 5000
# - Handles user registration and login


# Section             What it does
# -----------------------------------------------------------------------
# init_db()	        Makes sure tables exist before starting the server.
# /register route	    Saves a new user into the database.
# /login route	    Looks up the user and checks password.
# hashlib	            Turns passwords into a hash (a scrambled string).
# app.run(port=5000)	Starts the server on port 5000 (auth service).

# """

# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from sqlalchemy.orm import Session
# from database.db_connection import SessionLocal, init_db
# from backend.auth_service.models import User
# import hashlib

# app = Flask(__name__)
# CORS(app)
# app.debug = True  # Enable debug mode for logging when troubleshooting

# # Create tables if they don't exist yet
# init_db()


# def get_password_hash(password: str) -> str:
#     """
#     Simple password hashing using SHA256.
#     (Later can replace with argon2 if desired.)
#     """
#     return hashlib.sha256(password.encode()).hexdigest()


# @app.route("/register", methods=["POST"])
# def register():
#     """
#     Receives JSON: { "full_name": "...", "email": "...", "password": "..." }
#     Creates a new user in the database.
#     """
#     data = request.get_json()

#     full_name = data.get("full_name")
#     email = data.get("email")
#     password = data.get("password")

#     if not all([full_name, email, password]):
#         return jsonify({"success": False, "message": "Missing fields"}), 400

#     db: Session = SessionLocal()

#     # Check for duplicate email
#     existing = db.query(User).filter(User.email == email).first()
#     if existing:
#         db.close()
#         return jsonify({"success": False, "message": "Email already registered"}), 400

#     hashed = get_password_hash(password)
#     new_user = User(full_name=full_name, email=email, password=hashed)

#     db.add(new_user)
#     db.commit()
#     db.close()

#     return jsonify({"success": True, "message": "Account created successfully"}), 201


# @app.route("/login", methods=["POST"])
# def login():
#     """
#     Receives JSON: { "email": "...", "password": "..." }
#     Verifies credentials.
#     """
#     data = request.get_json()
#     email = data.get("email")
#     password = data.get("password")

#     if not all([email, password]):
#         return jsonify({"success": False, "message": "Missing credentials"}), 400

#     db: Session = SessionLocal()
#     user = db.query(User).filter(User.email == email).first()

#     if user and user.password == get_password_hash(password):
#         db.close()
#         return jsonify({"success": True, "message": "Login successful"})
#     else:
#         db.close()
#         return jsonify({"success": False, "message": "Invalid email or password"}), 401


# @app.route("/", methods=["GET"])
# def home():
#     return jsonify({"message": "Auth Service is running"})


# @app.route("/test", methods=["GET"])
# def test():
#     return jsonify({"message": "Test route works!"}), 200

# @app.errorhandler(403)
# def forbidden_error(error):
#     return jsonify({"error": "Forbidden: You don't have permission to access this resource"}), 403

# @app.errorhandler(500)
# def internal_error(error):
#     return jsonify({"error": "Internal Server Error"}), 500


# if __name__ == "__main__":
#     # Run the auth service on port 8080
#     app.run(port=8080)