import pytest
from unittest.mock import MagicMock

def test_register_success(client, mock_db, mocker):
    mock_conn, mock_cursor = mock_db
    
    # Mock database return for successful insert
    # RETURNING user_id, role
    mock_cursor.fetchone.return_value = {"user_id": 1, "role": "attendee"}
    
    # Mock PasswordHasher instance
    mock_ph = mocker.patch("backend.auth_service.routes.ph")
    mock_ph.hash.return_value = "hashed_secret"
    
    payload = {
        "email": "test@example.com",
        "password": "password123",
        "first_name": "Test",
        "last_name": "User"
    }
    
    response = client.post("/auth/register", json=payload)
    
    assert response.status_code == 201
    data = response.get_json()
    assert data["user_id"] == 1
    assert data["role"] == "attendee"
    assert "token" in data
    
    # Verify DB interaction
    assert mock_cursor.execute.called
    args, _ = mock_cursor.execute.call_args
    assert args[1][0] == "test@example.com" # email
    assert args[1][1] == "hashed_secret" # password hash

def test_register_missing_fields(client):
    response = client.post("/auth/register", json={})
    assert response.status_code == 400
    assert "Email and password required" in response.get_json()["error"]

def test_login_success(client, mock_db, mocker):
    mock_conn, mock_cursor = mock_db
    
    # Mock finding user
    mock_cursor.fetchone.return_value = {
        "user_id": 1,
        "password_hash": "hashed_secret",
        "role": "attendee"
    }
    
    # Mock PasswordHasher instance
    mock_ph = mocker.patch("backend.auth_service.routes.ph")
    mock_ph.verify.return_value = True
    
    payload = {
        "email": "test@example.com",
        "password": "password123"
    }
    
    response = client.post("/auth/login", json=payload)
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["user_id"] == 1
    assert "token" in data

def test_login_invalid_credentials(client, mock_db, mocker):
    mock_conn, mock_cursor = mock_db
    
    # Mock user found
    mock_cursor.fetchone.return_value = {
        "user_id": 1,
        "password_hash": "hashed_secret",
        "role": "attendee"
    }
    
    # Mock PasswordHasher instance
    mock_ph = mocker.patch("backend.auth_service.routes.ph")
    mock_ph.verify.side_effect = Exception("Verify failed")
    
    payload = {
        "email": "test@example.com",
        "password": "wrongpassword"
    }
    
    response = client.post("/auth/login", json=payload)
    
    assert response.status_code == 401
    assert "Invalid credentials" in response.get_json()["error"]

def test_get_me_success(client, mock_db, mocker):
    mock_conn, mock_cursor = mock_db
    
    # Create a valid token
    from backend.auth_service.utils import create_token
    token = create_token(1, "attendee")
    
    # Mock DB return for user profile
    mock_cursor.fetchone.return_value = {
        "user_id": 1,
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "role": "attendee"
    }
    
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["email"] == "test@example.com"

def test_get_me_unauthorized(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
