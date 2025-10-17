"""
Shared authentication helpers.
Provides token verification and role enforcement.
"""

import jwt, os
from dotenv import load_dotenv
from flask import jsonify, request

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET", "change_me")

def verify_token_from_request(required_roles=None):
    """
    Verify the JWT in the Authorization header.
    Returns (user_id, role) if valid, otherwise (None, None) and a Flask response.
    If required_roles is provided, ensure the user's role is allowed.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, None, jsonify({"error": "missing token"}), 401
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None, None, jsonify({"error": "invalid token"}), 401

    user_id = payload.get("sub")
    role = payload.get("role")

    if required_roles and role not in required_roles:
        return None, None, jsonify({"error": "permission denied"}), 403

    return user_id, role, None, None