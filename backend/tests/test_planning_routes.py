import pytest
from unittest.mock import MagicMock
from datetime import datetime

def test_list_tasks(client, mocker):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None
    mock_conn.cursor.return_value = mock_cursor
    
    mocker.patch("backend.planning_service.routes.get_db", return_value=mock_conn)
    mocker.patch("backend.planning_service.routes.verify_token_from_request", return_value=(1, "organizer", None, None))

    mock_cursor.fetchall.return_value = [
        {
            "task_id": 1,
            "title": "Task 1",
            "due_date": datetime(2025, 1, 1, 10, 0, 0),
            "position": 1000.0
        }
    ]

    response = client.get("/planning/tasks")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["title"] == "Task 1"

def test_create_task(client, mocker):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None
    mock_conn.cursor.return_value = mock_cursor
    
    mocker.patch("backend.planning_service.routes.get_db", return_value=mock_conn)
    mocker.patch("backend.planning_service.routes.verify_token_from_request", return_value=(1, "organizer", None, None))

    mock_cursor.fetchone.side_effect = [[1000.0], {"task_id": 2}]

    payload = {
        "title": "New Task",
        "due_date": "2025-01-01T10:00:00Z"
    }
    
    response = client.post("/planning/tasks", json=payload)
    assert response.status_code == 201
    assert response.get_json()["task_id"] == 2

def test_update_task(client, mocker):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None
    mock_conn.cursor.return_value = mock_cursor
    
    mocker.patch("backend.planning_service.routes.get_db", return_value=mock_conn)
    mocker.patch("backend.planning_service.routes.verify_token_from_request", return_value=(1, "organizer", None, None))

    payload = {"title": "Updated Task"}
    response = client.put("/planning/tasks/1", json=payload)
    assert response.status_code == 200
    assert response.get_json()["status"] == "updated"

def test_delete_task(client, mocker):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None
    mock_conn.cursor.return_value = mock_cursor
    
    mocker.patch("backend.planning_service.routes.get_db", return_value=mock_conn)
    mocker.patch("backend.planning_service.routes.verify_token_from_request", return_value=(1, "organizer", None, None))

    response = client.delete("/planning/tasks/1")
    assert response.status_code == 200
    assert response.get_json()["status"] == "deleted"
