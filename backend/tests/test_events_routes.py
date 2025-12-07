import pytest
from unittest.mock import MagicMock

def test_list_events(client, mocker):
    # Mock database connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None
    mock_conn.cursor.return_value = mock_cursor
    
    # Mock get_db in events_service
    mocker.patch("backend.events_service.routes.get_db", return_value=mock_conn)
    
    # Mock verify_token (optional, if we want to test authenticated flow)
    mocker.patch("backend.events_service.routes.verify_token", return_value=1)

    # Mock DB response
    from datetime import datetime
    mock_cursor.fetchall.return_value = [
        {
            "event_id": 1, 
            "title": "Test Event", 
            "description": "Desc", 
            "start_time": datetime(2025, 1, 1, 10, 0, 0),
            "end_time": datetime(2025, 1, 1, 12, 0, 0),
            "visibility": "public",
            "avg_rating": 4.5
        }
    ]

    response = client.get("/events/")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Event"
    assert data[0]["avg_rating"] == 4.5

def test_get_event_detail(client, mocker):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None
    mock_conn.cursor.return_value = mock_cursor
    
    mocker.patch("backend.events_service.routes.get_db", return_value=mock_conn)

    # Mock DB response
    from datetime import datetime
    mock_cursor.fetchone.return_value = {
        "event_id": 1, 
        "title": "Test Event", 
        "description": "Desc", 
        "start_time": datetime(2025, 1, 1, 10, 0, 0),
        "end_time": datetime(2025, 1, 1, 12, 0, 0),
        "visibility": "public",
        "organizer_id": 1,
        "created_by": 1,
        "avg_rating": 4.5
    }

    response = client.get("/events/1")
    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "Test Event"

def test_create_event_success(client, mocker):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None
    mock_conn.cursor.return_value = mock_cursor
    
    mocker.patch("backend.events_service.routes.get_db", return_value=mock_conn)
    
    # Mock verify_token_from_request to return a valid user
    mocker.patch("backend.events_service.routes.verify_token_from_request", return_value=(1, "organizer", None, None))

    mock_cursor.fetchone.return_value = {"event_id": 100}

    payload = {
        "title": "New Event",
        "description": "Description",
        "start_time": "2025-05-01T10:00:00Z",
        "end_time": "2025-05-01T12:00:00Z",
        "location_type": "custom",
        "custom_location_address": "123 Main St",
        "visibility": "public"
    }

    response = client.post("/events/", json=payload)
    assert response.status_code == 201
    assert response.get_json()["event_id"] == 100

def test_create_event_invalid_input(client, mocker):
    mocker.patch("backend.events_service.routes.verify_token_from_request", return_value=(1, "organizer", None, None))
    
    payload = {
        "title": "New Event"
        # Missing start_time, end_time, etc.
    }
    response = client.post("/events/", json=payload)
    assert response.status_code == 400

def test_update_event(client, mocker):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None
    mock_conn.cursor.return_value = mock_cursor
    
    mocker.patch("backend.events_service.routes.get_db", return_value=mock_conn)
    mocker.patch("backend.events_service.routes.verify_token_from_request", return_value=(1, "organizer", None, None))

    # Mock fetchone for existing event check
    from datetime import datetime
    mock_cursor.fetchone.return_value = {
        "organizer_id": 1,
        "created_by": 1,
        "start_time": datetime(2025, 1, 1, 10, 0, 0),
        "end_time": datetime(2025, 1, 1, 12, 0, 0),
        "location_type": "custom",
        "venue_id": None,
        "custom_location_address": "Old Address",
        "visibility": "public"
    }

    payload = {"title": "Updated Title"}
    response = client.put("/events/1", json=payload)
    assert response.status_code == 200
    assert response.get_json()["status"] == "updated"

def test_delete_event(client, mocker):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None
    mock_conn.cursor.return_value = mock_cursor
    
    mocker.patch("backend.events_service.routes.get_db", return_value=mock_conn)
    mocker.patch("backend.events_service.routes.verify_token_from_request", return_value=(1, "organizer", None, None))

    mock_cursor.fetchone.return_value = {"organizer_id": 1, "created_by": 1}
    mock_cursor.rowcount = 1

    response = client.delete("/events/1")
    assert response.status_code == 200
    assert response.get_json()["status"] == "deleted"

def test_rsvp_event(client, mocker):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None
    mock_conn.cursor.return_value = mock_cursor
    
    mocker.patch("backend.events_service.routes.get_db", return_value=mock_conn)
    mocker.patch("backend.events_service.routes.verify_token_from_request", return_value=(1, "attendee", None, None))

    payload = {"status": "going"}
    response = client.post("/events/1/rsvp", json=payload)
    assert response.status_code == 200
    assert response.get_json()["status"] == "going"
