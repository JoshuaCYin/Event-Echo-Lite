"""
Authentication service route handlers.

Provides routes for:
- User registration
- User login
- Account deletion
- Profile retrieval (/me)
- Profile update (/me PUT)
- Admin role assignment
- Admin user listing (New)

All JWT logic is delegated to `auth_service.utils`.
"""

from flask import Blueprint, request, jsonify
from argon2 import PasswordHasher
from backend.database.db_connection import get_db
from backend.auth_service.utils import create_token, verify_token_from_request
import psycopg2.errors
import logging

auth_bp = Blueprint("auth", __name__)
ph = PasswordHasher()


# ----------------------------------------------------
# REQUEST LOGGING
# ----------------------------------------------------
@auth_bp.before_request
def before_request():
    """
    Log every incoming request to the authentication service.
    """
    logging.info(
        f"[Auth] Incoming {request.method} {request.path} "
        f"Headers={dict(request.headers)}"
    )


@auth_bp.after_request
def after_request(response):
    """
    Log the response status code for every request.
    """
    logging.info(f"[Auth] Response {response.status}")
    return response


# ----------------------------------------------------
# REGISTER
# ----------------------------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user.

    Expected JSON body:
        {
            "email": "example@example.com",
            "password": "password123",
            "first_name": "John",
            "last_name": "Doe"
        }

    Returns:
        201: { "user_id": int, "role": str, "token": str }
        400: missing fields or invalid input
        400: email already exists
        500: hashing or database failure
    """
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")
    first_name = data.get("first_name")
    last_name = data.get("last_name")

    # Validate input
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    if not first_name or not last_name:
        return jsonify({"error": "First and last name required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    # Hash password
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

    token = create_token(user_id, role)

    return jsonify({"user_id": user_id, "role": role, "token": token}), 201


# ----------------------------------------------------
# LOGIN
# ----------------------------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate a user and return a JWT.

    Expected JSON body:
        {
            "email": "example@example.com",
            "password": "password123"
        }

    Returns:
        200: { "user_id": int, "role": str, "token": str }
        400: missing credentials
        401: invalid credentials
        500: database error
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
    except Exception:
        return jsonify({"error": "Login failed"}), 500

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    # Verify password
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


# ----------------------------------------------------
# DELETE ACCOUNT
# ----------------------------------------------------
@auth_bp.route("/delete", methods=["POST"])
def delete_account():
    """
    Delete the authenticated user's account.

    Authorization:
        Requires header:
            Authorization: Bearer <token>

    Returns:
        200: { "status": "deleted" }
        401/403: auth failure
        500: database error
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


# ----------------------------------------------------
# GET CURRENT USER
# ----------------------------------------------------
@auth_bp.route("/me", methods=["GET"])
def get_current_user():
    """
    Retrieve the current user's full profile.

    Authorization:
        Requires header:
            Authorization: Bearer <token>

    Returns:
        200: user object
        401/403: auth failure
        404: not found
        500: database error
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


# ----------------------------------------------------
# UPDATE CURRENT USER
# ----------------------------------------------------
@auth_bp.route("/me", methods=["PUT"])
def update_current_user():
    """
    Update any editable fields of the current user's profile.

    Allowed fields:
        - first_name
        - last_name
        - major_department
        - phone_number
        - hobbies
        - bio
        - profile_picture

    Authorization:
        Requires header:
            Authorization: Bearer <token>

    Returns:
        200: updated user object
        400: no valid fields
        401/403: auth failure
        500: database error
    """
    user_id, _, err, code = verify_token_from_request()
    if err:
        return err, code

    data = request.get_json() or {}

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
    except Exception as e:
        return jsonify({"error": "Update failed"}), 500

    return jsonify(dict(updated_user)), 200


# ----------------------------------------------------
# LIST USERS (ADMIN ONLY)
# ----------------------------------------------------
@auth_bp.route("/users", methods=["GET"])
def list_users():
    """
    Admin-only endpoint to list all users.
    Returns:
        200: [ {user_id, email, first_name, last_name, role}, ... ]
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
                # Convert timestamps to string
                for u in users:
                    if u.get('created_at'):
                        u['created_at'] = u['created_at'].isoformat()
    except Exception as e:
        print(f"Error listing users: {e}")
        return jsonify({"error": "Failed to retrieve users"}), 500

    return jsonify(users), 200


# ----------------------------------------------------
# SET ROLE (ADMIN ONLY)
# ----------------------------------------------------
@auth_bp.route("/set-role", methods=["POST"])
def set_role():
    """
    Admin-only endpoint to change a user's role.

    Expected JSON body:
        {
            "user_id": <int>,
            "role": "attendee" | "organizer" | "admin"
        }

    Authorization:
        Requires header:
            Authorization: Bearer <admin-token>
        AND token.role must be "admin".

    Returns:
        200: { "status": "ok" }
        400: invalid input
        401/403: unauthorized
        500: database failure
    """
    _, _, err, code = verify_token_from_request(required_roles=["admin"])
    if err:
        return err, code

    data = request.get_json() or {}
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