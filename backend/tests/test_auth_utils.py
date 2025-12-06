import pytest
from backend.auth_service.utils import create_token, verify_token, verify_token_from_request
import jwt
import os
from datetime import datetime, timedelta

@pytest.fixture(autouse=True)
def mock_jwt_secret(mocker):
    mocker.patch("backend.auth_service.utils.JWT_SECRET", "test_secret")


def test_create_token(mocker):
    # Patch the secret used in utils
    mocker.patch("backend.auth_service.utils.JWT_SECRET", "test_secret")
    
    user_id = 123
    role = "admin"
    token = create_token(user_id, role)
    
    assert isinstance(token, str)
    
    # Decode to verify contents using the same secret
    payload = jwt.decode(token, "test_secret", algorithms=["HS256"])
    assert payload["sub"] == user_id
    assert payload["role"] == role
    assert "exp" in payload
    assert "iat" in payload

def test_verify_token():
    user_id = 456
    role = "attendee"
    token = create_token(user_id, role)
    
    decoded_user_id = verify_token(token)
    assert decoded_user_id == user_id

def test_verify_token_invalid():
    assert verify_token("invalid.token.here") is None

def test_verify_token_from_request_valid(app):
    user_id = 789
    role = "organizer"
    token = create_token(user_id, role)
    
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        uid, r, err, code = verify_token_from_request()
        assert uid == user_id
        assert r == role
        assert err is None
        assert code is None

def test_verify_token_from_request_missing_header(app):
    with app.test_request_context():
        uid, r, err, code = verify_token_from_request()
        assert uid is None
        assert code == 401
        assert err.json["error"] == "missing token"

def test_verify_token_from_request_invalid_format(app):
    with app.test_request_context(headers={"Authorization": "InvalidFormat"}):
        uid, r, err, code = verify_token_from_request()
        assert uid is None
        assert code == 401
        assert err.json["error"] == "missing token"  # Logic says if not startswith Bearer

def test_verify_token_from_request_wrong_role(app):
    user_id = 111
    role = "attendee"
    token = create_token(user_id, role)
    
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        uid, r, err, code = verify_token_from_request(required_roles=["admin"])
        assert uid is None
        assert code == 403
        assert err.json["error"] == "permission denied"
