"""
Auth service routes: register, login, delete account.
Uses Argon2 for password hashing and JWT for simple token auth.
"""

from flask import Blueprint, request, jsonify
from argon2 import PasswordHasher
from backend.database.db_connection import get_db
from backend.auth_service.utils import verify_token_from_request
import os
import jwt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

auth_bp = Blueprint("auth", __name__)
ph = PasswordHasher()
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET", os.getenv("JWT_SECRET", os.getenv("JWT_SECRET", os.getenv("JWT_SECRET", ""))))  # ensure defined
# JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET", "change_me")

# helper: create JWT token
def create_token(user_id: int, role: str, expires_minutes: int = 60*24):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,     # subject (user ID)
        "role": role,       # role (e.g. attendee, organizer, admin)
        "exp": now + timedelta(minutes=expires_minutes), #expiry
        "iat": now          # issued at
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# helper: require token (simple)
def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except Exception:
        return None

@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Request JSON: { "email": "...", "password": "...", "display_name": "..." }
    Response: 201 on success, 400 on error.
    """
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")
    display_name = data.get("display_name") or None

    if not email or not password:   # missing field check
        return jsonify({"error": "Email and password required"}), 400

    pw_hash = ph.hash(password)

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (email, password_hash, display_name) VALUES (?, ?, ?)",
            (email, pw_hash, display_name)
        )
        conn.commit()
        user_id = cur.lastrowid
        role = "attendee"   # attendee is default for all new users
    except Exception as e:
        conn.rollback()
        if "UNIQUE" in str(e).upper():
            return jsonify({"error": "Email already exists"}), 400 # Error message shown to user
        return jsonify({"error": "Registration failed"}), 500 # Error message shown to user
    finally:
        conn.close()

    token = create_token(user_id, role)
    return jsonify({"id": user_id, "role": role, "token": token}), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Request JSON: { "email": "...", "password": "..." }
    Response: token on success (200), 401 on failure.
    """
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400 # Error message shown to user

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, password_hash, role FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Invalid credentials"}), 401 # Error message shown to user

        user_id = row["id"]
        pw_hash = row["password_hash"]
        role = row["role"] if "role" in row.keys() else "attendee"

        try:
            ph.verify(pw_hash, password)
        except Exception:
            return jsonify({"error": "Invalid credentials"}), 401 # Error message shown to user

    finally:
        conn.close()

    token = create_token(user_id, role)
    return jsonify({"id": user_id, "role": role, "token": token}), 200

@auth_bp.route("/delete", methods=["POST"])
def delete_account():
    """
    Delete the authenticated user's account.
    Request header: Authorization: Bearer <token>
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Missing token"}), 401
    token = auth.split(" ", 1)[1]
    user_id = verify_token(token)
    if not user_id:
        return jsonify({"error": "Invalid token"}), 401

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()

    return jsonify({"status": "deleted"}), 200

@auth_bp.route("/me", methods=["GET"])
def current_user():
    """
    Return current user info (id, email, role) based on JWT token.
    Header: Authorization: Bearer <token>
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Missing token"}), 401
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return jsonify({"error": "Invalid token"}), 401

    user_id = payload.get("sub")
    role = payload.get("role")

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT email, display_name FROM users WHERE id = ?", (user_id,))
        user = cur.fetchone()
    finally:
        conn.close()

    if not user:
        return jsonify({"error": "Not found"}), 404

    return jsonify({
        "id": user_id,
        "email": user["email"],
        "display_name": user["display_name"],
        "role": role
    }), 200

@auth_bp.route("/set-role", methods=["POST"])
def set_role():
    """
    Admin-only endpoint to change a user's role.
    Body: { "user_id": int, "role": "attendee"|"organizer"|"admin" }
    """
    user_id, role, err, code = verify_token_from_request(required_roles=["admin"])
    if err:
        return err, code

    data = request.get_json() or {}
    target_id = data.get("user_id")
    new_role = data.get("role")

    if not target_id or new_role not in ["attendee", "organizer", "admin"]:
        return jsonify({"error": "Invalid input"}), 400

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, target_id))
        conn.commit()
    finally:
        conn.close()

    return jsonify({"status": f"user {target_id} role set to {new_role}"}), 200
