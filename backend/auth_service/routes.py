"""
Auth service routes: register, login, delete account, and profile management.
"""

from flask import Blueprint, request, jsonify
from argon2 import PasswordHasher
from backend.database.db_connection import get_db
from backend.auth_service.utils import verify_token_from_request
import os
import jwt
import psycopg2.errors
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

auth_bp = Blueprint("auth", __name__)
ph = PasswordHasher()

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set. Please set the environment variable.")

# --- Helper Functions ---

def create_token(user_id: int, role: str, expires_minutes: int = 60 * 24):
    """
    Generates a new JWT for a given user.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,     # subject (user ID)
        "role": role,       # role (e.g. attendee, organizer, admin)
        "exp": now + timedelta(minutes=expires_minutes), # expiry
        "iat": now          # issued at
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_token(token: str):
    """
    Verifies a JWT and returns the user ID if valid, otherwise None.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except Exception:
        return None

# --- Routes ---

@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user.
    Request JSON: { 
        "email": "...", 
        "password": "...", 
        "first_name": "...", 
        "last_name": "..." 
    }
    Response: 201 on success, 400 on error.
    """
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")
    first_name = data.get("first_name")
    last_name = data.get("last_name")

    # --- Validation ---
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    if not first_name or not last_name:
        return jsonify({"error": "First and last name required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    try:
        pw_hash = ph.hash(password)
    except Exception as e:
        print(f"Password hashing failed: {e}")
        return jsonify({"error": "Registration failed during hashing"}), 500

    sql = """
        INSERT INTO users (email, password_hash, first_name, last_name) 
        VALUES (%s, %s, %s, %s)
        RETURNING user_id, role;
    """

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (email, pw_hash, first_name, last_name))
                new_user = cur.fetchone()
                conn.commit()
                
                user_id = new_user["user_id"]
                role = new_user["role"] # 'attendee' is the default in schema
                
    except psycopg2.errors.UniqueViolation:
        return jsonify({"error": "Email already exists"}), 400
    except Exception as e:
        print(f"Database error during registration: {e}")
        return jsonify({"error": "Registration failed"}), 500

    token = create_token(user_id, role)
    return jsonify({"user_id": user_id, "role": role, "token": token}), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate a user and return a token.
    Request JSON: { "email": "...", "password": "..." }
    Response: token on success (200), 401 on failure.
    """
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    sql = "SELECT user_id, password_hash, role FROM users WHERE email = %s;"
    
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (email,))
                user = cur.fetchone()

        if not user:
            return jsonify({"error": "Invalid credentials"}), 401

        user_id = user["user_id"]
        pw_hash = user["password_hash"]
        role = user["role"]

        try:
            ph.verify(pw_hash, password)
        except Exception:
            return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        print(f"Database error during login: {e}")
        return jsonify({"error": "Login failed"}), 500

    token = create_token(user_id, role)
    return jsonify({"user_id": user_id, "role": role, "token": token}), 200

@auth_bp.route("/delete", methods=["POST"])
def delete_account():
    """
    Delete the authenticated user's account.
    Request header: Authorization: Bearer <token>
    """
    user_id, _, err, code = verify_token_from_request()
    if err:
        return err, code

    sql = "DELETE FROM users WHERE user_id = %s;"

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                conn.commit()
    except Exception as e:
        print(f"Database error during account deletion: {e}")
        return jsonify({"error": "Failed to delete account"}), 500

    return jsonify({"status": "deleted"}), 200

@auth_bp.route("/me", methods=["GET"])
def get_current_user():
    """
    Return all profile info for the current user based on JWT token.
    Header: Authorization: Bearer <token>
    """
    user_id, role, err, code = verify_token_from_request()
    if err:
        return err, code

    sql = """
        SELECT user_id, email, first_name, last_name, role, created_at,
               major_department, phone_number, hobbies, bio, profile_picture
        FROM users 
        WHERE user_id = %s;
    """

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                user = cur.fetchone()
    except Exception as e:
        print(f"Database error fetching /me: {e}")
        return jsonify({"error": "Could not retrieve user data"}), 500

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(dict(user)), 200

@auth_bp.route("/me", methods=["PUT"])
def update_current_user():
    """
    Update the current user's profile information.
    Header: Authorization: Bearer <token>
    Body: { "first_name": "...", "last_name": "...", "major_department": "...", ... }
    """
    user_id, _, err, code = verify_token_from_request()
    if err:
        return err, code

    data = request.get_json() or {}
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Build partial update query
    fields = []
    values = []
    
    allowed_fields = [
        "first_name", "last_name", "major_department", 
        "phone_number", "hobbies", "bio", "profile_picture"
    ]
    
    for key in allowed_fields:
        if key in data:
            fields.append(f"{key} = %s")
            values.append(data[key])
    
    if not fields:
        return jsonify({"error": "No valid fields to update"}), 400

    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(user_id)
    
    sql = f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s RETURNING *;"

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, values)
                updated_user = cur.fetchone()
                conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Database error updating profile for user {user_id}: {e}")
        return jsonify({"error": "Failed to update profile"}), 500

    return jsonify(dict(updated_user)), 200


@auth_bp.route("/set-role", methods=["POST"])
def set_role():
    """
    Admin-only endpoint to change a user's role.
    Body: { "user_id": int, "role": "attendee"|"organizer"|"admin" }
    """
    admin_id, admin_role, err, code = verify_token_from_request(required_roles=["admin"])
    if err:
        return err, code

    data = request.get_json() or {}
    target_id = data.get("user_id")
    new_role = data.get("role")

    if not target_id or new_role not in ["attendee", "organizer", "admin"]:
        return jsonify({"error": "Invalid input: user_id and valid role required"}), 400

    sql = "UPDATE users SET role = %s WHERE user_id = %s;"
    
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (new_role, target_id))
                conn.commit()
    except Exception as e:
        print(f"Database error setting role: {e}")
        return jsonify({"error": "Failed to update role"}), 500

    return jsonify({"status": f"user {target_id} role set to {new_role}"}), 200