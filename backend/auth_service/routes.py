"""
Authentication service route handlers.

Provides routes for:
- User registration
- User login
- Account deletion
- Profile retrieval (/me)
- Profile update (/me PUT)
- Admin role assignment
- Admin user listing

All JWT logic is delegated to `auth_service.utils`.
"""

import logging
from typing import Tuple, Dict, Any, Union

import psycopg2.errors
from argon2 import PasswordHasher
from flask import Blueprint, request, jsonify, Response
from backend.database.db_connection import get_db
from backend.auth_service.utils import create_token, verify_token_from_request

auth_bp = Blueprint("auth", __name__)
ph = PasswordHasher()


# --- REQUEST LOGGING ---
@auth_bp.before_request
def before_request() -> None:
    """
    Log every incoming request header and method to the authentication service.
    Useful for debugging and audit trails.
    """
    logging.info(
        f"[Auth] Incoming {request.method} {request.path} "
        f"Headers={dict(request.headers)}"
    )


@auth_bp.after_request
def after_request(response: Response) -> Response:
    """
    Log the response status code for every request.

    Args:
        response (Response): The Flask response object.

    Returns:
        Response: The passed-through response object.
    """
    logging.info(f"[Auth] Response {response.status}")
    return response


# --- REGISTER ---
@auth_bp.route("/register", methods=["POST"])
def register() -> Tuple[Response, int]:
    """
    Register a new user in the system.

    Expects a JSON body with:
    - email (str): Unique email address.
    - password (str): Minimum 8 characters.
    - first_name (str)
    - last_name (str)

    Returns:
        201: JSON with user_id, role, and a new JWT token.
        400: Missing fields, invalid input, or email already exists.
        500: Server-side error (hashing or database).
    """
    data: Dict[str, Any] = request.get_json() or {}
    email: str = (data.get("email") or "").strip().lower()
    password: str = data.get("password", "")
    first_name: str = data.get("first_name")
    last_name: str = data.get("last_name")

    # Validate input
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    if not first_name or not last_name:
        return jsonify({"error": "First and last name required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    # Hash password using Argon2
    try:
        pw_hash = ph.hash(password)
    except Exception:
        return jsonify({"error": "Password hashing failed"}), 500

    sql = """
        INSERT INTO users (email, password_hash, first_name, last_name)
        VALUES (%s, %s, %s, %s)
        RETURNING user_id, role;
    """

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (email, pw_hash, first_name, last_name))
                user = cur.fetchone()
                conn.commit()
    except psycopg2.errors.UniqueViolation:
        return jsonify({"error": "Email already exists"}), 400
    except Exception:
        return jsonify({"error": "Registration failed"}), 500

    user_id = user["user_id"]
    role = user["role"]

    # Generate initial token for immediate login
    token = create_token(user_id, role)

    return jsonify({"user_id": user_id, "role": role, "token": token}), 201


# --- LOGIN ---
@auth_bp.route("/login", methods=["POST"])
def login() -> Tuple[Response, int]:
    """
    Authenticate a user and return a JWT.

    Expects a JSON body with:
    - email (str)
    - password (str)

    Returns:
        200: JSON with user_id, role, and JWT token.
        400: Missing credentials.
        401: Invalid credentials (wrong password or email).
        500: Database error.
    """
    data: Dict[str, Any] = request.get_json() or {}
    email: str = (data.get("email") or "").strip().lower()
    password: str = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    sql = "SELECT user_id, password_hash, role FROM users WHERE email = %s;"

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (email,))
                user = cur.fetchone()
    except Exception:
        return jsonify({"error": "Login failed"}), 500

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    # Verify password against hash
    try:
        ph.verify(user["password_hash"], password)
    except Exception:
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_token(user["user_id"], user["role"])

    return jsonify({
        "user_id": user["user_id"],
        "role": user["role"],
        "token": token
    }), 200


# --- DELETE ACCOUNT ---
@auth_bp.route("/delete", methods=["POST"])
def delete_account() -> Union[Tuple[Response, int], Tuple[Dict[str, str], int]]:
    """
    Delete the authenticated user's account permanently.
    
    Requires Authorization header: Bearer <token>

    Returns:
        200: JSON status "deleted".
        401/403: Authentication failure.
        500: Database error.
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
    except Exception:
        return jsonify({"error": "Deletion failed"}), 500

    return jsonify({"status": "deleted"}), 200


# --- GET CURRENT USER ---
@auth_bp.route("/me", methods=["GET"])
def get_current_user() -> Tuple[Response, int]:
    """
    Retrieve the current user's full profile details.

    Requires Authorization header: Bearer <token>

    Returns:
        200: User profile object.
        401/403: Authentication failure.
        404: User not found in DB (edge case).
        500: Database error.
    """
    user_id, _, err, code = verify_token_from_request()
    if err:
        return err, code

    sql = """
        SELECT user_id, email, first_name, last_name, role,
               created_at, major_department, phone_number,
               hobbies, bio, profile_picture
        FROM users
        WHERE user_id = %s;
    """

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                user = cur.fetchone()
    except Exception:
        return jsonify({"error": "Could not retrieve user"}), 500

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(dict(user)), 200


# --- UPDATE CURRENT USER ---
@auth_bp.route("/me", methods=["PUT"])
def update_current_user() -> Tuple[Response, int]:
    """
    Update specific fields of the current user's profile.

    Allowed fields:
    - first_name, last_name
    - major_department
    - phone_number
    - hobbies, bio
    - profile_picture

    Requires Authorization header: Bearer <token>

    Returns:
        200: Updated user object.
        400: No valid fields provided.
        401/403: Authentication failure.
        500: Update failed.
    """
    user_id, _, err, code = verify_token_from_request()
    if err:
        return err, code

    data: Dict[str, Any] = request.get_json() or {}

    allowed = [
        "first_name",
        "last_name",
        "major_department",
        "phone_number",
        "hobbies",
        "bio",
        "profile_picture",
    ]

    fields = {k: v for k, v in data.items() if k in allowed}

    if not fields:
        return jsonify({"error": "No valid fields provided"}), 400

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    set_clause += ", updated_at = CURRENT_TIMESTAMP"

    values = list(fields.values()) + [user_id]

    sql = f"UPDATE users SET {set_clause} WHERE user_id = %s RETURNING *;"

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, values)
                updated_user = cur.fetchone()
                conn.commit()
    except Exception:
        return jsonify({"error": "Update failed"}), 500

    return jsonify(dict(updated_user)), 200


# --- LIST USERS (ADMIN ONLY) ---
@auth_bp.route("/users", methods=["GET"])
def list_users() -> Tuple[Response, int]:
    """
    Admin-only endpoint to list all users in the system.

    Returns:
        200: List of user objects.
        401/403: Unauthorized (not an admin).
        500: Database error.
    """
    _, _, err, code = verify_token_from_request(required_roles=["admin"])
    if err:
        return err, code

    sql = """
        SELECT user_id, email, first_name, last_name, role, created_at, major_department 
        FROM users 
        ORDER BY user_id ASC;
    """
    
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                users = [dict(row) for row in cur.fetchall()]
                # Convert timestamps to ISO string for JSON serialization
                for u in users:
                    if u.get('created_at'):
                        u['created_at'] = u['created_at'].isoformat()
    except Exception as e:
        print(f"Error listing users: {e}")
        return jsonify({"error": "Failed to retrieve users"}), 500

    return jsonify(users), 200


# --- SET ROLE (ADMIN ONLY) ---
@auth_bp.route("/set-role", methods=["POST"])
def set_role() -> Tuple[Response, int]:
    """
    Admin-only endpoint to promote or demote a user's role.

    Expects JSON:
        { "user_id": int, "role": "attendee" | "organizer" | "admin" }

    Returns:
        200: Success status.
        400: Invalid role or user_id.
        401/403: Unauthorized.
        500: Database error.
    """
    _, _, err, code = verify_token_from_request(required_roles=["admin"])
    if err:
        return err, code

    data: Dict[str, Any] = request.get_json() or {}
    target_id = data.get("user_id")
    new_role = data.get("role")

    if not target_id or new_role not in ("attendee", "organizer", "admin"):
        return jsonify({"error": "Invalid input"}), 400

    sql = "UPDATE users SET role = %s WHERE user_id = %s;"

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (new_role, target_id))
                conn.commit()
    except Exception:
        return jsonify({"error": "Failed to update role"}), 500

    return jsonify({"status": "ok"}), 200