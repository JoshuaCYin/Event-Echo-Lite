"""
Auth service routes: register, login, delete account.
Uses Argon2 for password hashing and JWT for simple token auth.
"""

from flask import Blueprint, request, jsonify
from argon2 import PasswordHasher
from backend.database.db_connection import get_db
import os
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

auth_bp = Blueprint("auth", __name__)
ph = PasswordHasher()
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET", os.getenv("JWT_SECRET", os.getenv("JWT_SECRET", os.getenv("JWT_SECRET", ""))))  # ensure defined
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET", "change_me")

# helper: create JWT token
def create_token(user_id: int, expires_minutes: int = 60*24):
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=expires_minutes),
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token

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

    if not email or not password:
        return jsonify({"error": "email and password required"}), 400

    pw_hash = ph.hash(password)

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (email, password_hash, display_name) VALUES (?, ?, ?)",
            (email, pw_hash, display_name),
        )
        conn.commit()
        user_id = cur.lastrowid
    except Exception as e:
        conn.rollback()
        if "UNIQUE" in str(e).upper():
            return jsonify({"error": "email already exists"}), 400
        return jsonify({"error": "registration failed"}), 500
    finally:
        conn.close()

    token = create_token(user_id)
    return jsonify({"id": user_id, "token": token}), 201

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
        return jsonify({"error": "email and password required"}), 400

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "invalid credentials"}), 401

        user_id = row["id"]
        pw_hash = row["password_hash"]
        try:
            ph.verify(pw_hash, password)
        except Exception:
            return jsonify({"error": "invalid credentials"}), 401

    finally:
        conn.close()

    token = create_token(user_id)
    return jsonify({"id": user_id, "token": token}), 200

@auth_bp.route("/delete", methods=["POST"])
def delete_account():
    """
    Delete the authenticated user's account.
    Request header: Authorization: Bearer <token>
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing token"}), 401
    token = auth.split(" ", 1)[1]
    user_id = verify_token(token)
    if not user_id:
        return jsonify({"error": "invalid token"}), 401

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()

    return jsonify({"status": "deleted"}), 200
