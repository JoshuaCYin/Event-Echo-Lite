"""
Quick API test for Event Echo Lite using local database, frontend, and backend
Tests: register, login, create event, list events.
"""

import requests

BASE = "http://localhost:5050"

# 1) Register a user
r = requests.post(f"{BASE}/auth/register", json={
    "email": "test@example.com",
    "password": "pass123",
    "display_name": "Test User"
})
print("REGISTER:", r.status_code, r.json())

# Extract token from register response
token = r.json().get("token")

# 2) Login with same credentials
r = requests.post(f"{BASE}/auth/login", json={
    "email": "test@example.com",
    "password": "pass123"
})
print("LOGIN:", r.status_code, r.json())
token = r.json().get("token")

# 3) Create a new event
headers = {"Authorization": f"Bearer {token}"}
r = requests.post(f"{BASE}/events/", json={
    "title": "First Test Event",
    "description": "Simple test",
    "start_time": "2025-10-20 10:00:00",
    "end_time": "2025-10-20 11:00:00",
    "location": "Room 101"
}, headers=headers)
print("CREATE EVENT:", r.status_code, r.json())

# 4) List all events
r = requests.get(f"{BASE}/events/")
print("LIST EVENTS:", r.status_code, r.json())
