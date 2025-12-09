"""
Shared authentication helpers.
Provides token creation, verification, and role enforcement.
"""

import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional, Any
from flask import jsonify, request, Response
from dotenv import load_dotenv

# Load .env only once here
load_dotenv()

# Load secrets & configs
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is missing. Set it in .env")

TOKEN_EXPIRATION_MINUTES = int(os.getenv("TOKEN_EXPIRATION_MINUTES", 1440))  # Default 24 hours

# --- JWT CREATION ---
def create_token(user_id: int, role: str) -> str:
    """
    Generates a new JWT for a given user.

    Args:
        user_id (int): The unique ID of the user.
        role (str): The role of the user (admin, organizer, attendee).

    Returns:
        str: Encoded JWT string.
    """
    now = datetime.now(timezone.utc)

    payload = {
        "sub": user_id,
        "role": role,
        "exp": now + timedelta(minutes=TOKEN_EXPIRATION_MINUTES),
        "iat": now
    }

    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# --- JWT VALIDATION ---
def verify_token_from_request(required_roles: Optional[list] = None) -> Tuple[Optional[int], Optional[str], Optional[Response], Optional[int]]:
    """
    Verify the JWT in the Authorization header.

    Args:
        required_roles (list, optional): List of allowed roles.

    Returns:
        tuple: (user_id, role, error_response, status_code)
               If successful, error_response and status_code are None.
               If failed, user_id and role are None.
    """

    auth = request.headers.get("Authorization", "")

    if not auth.startswith("Bearer "):
        return None, None, jsonify({"error": "missing token"}), 401

    token = auth.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None, None, jsonify({"error": "token expired"}), 401
    except Exception:
        return None, None, jsonify({"error": "invalid token"}), 401

    user_id = payload.get("sub")
    role = payload.get("role")

    if required_roles and role not in required_roles:
        return None, None, jsonify({"error": "permission denied"}), 403

    return user_id, role, None, None


def verify_token(token: str) -> Optional[int]:
    """
    Validate a JWT manually (optional usage).

    Args:
        token (str): JWT string.

    Returns:
        int: user_id if valid, None otherwise.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except Exception:
        return None
