import pytest
from flask import Flask
from backend.auth_service.routes import auth_bp
import os

# Ensure JWT_SECRET is set for tests
os.environ["JWT_SECRET"] = "test_secret"

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    
    from backend.events_service.routes import events_bp
    app.register_blueprint(events_bp, url_prefix="/events")

    from backend.ai_service.routes import ai_blueprint
    app.register_blueprint(ai_blueprint, url_prefix="/ai")

    from backend.planning_service.routes import planning_bp
    app.register_blueprint(planning_bp, url_prefix="/planning")

    app.config["TESTING"] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def mock_db(mocker):
    """
    Mocks the database connection and cursor.
    """
    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()
    
    # Setup the context manager for connection
    mock_conn.__enter__ = mocker.Mock(return_value=mock_conn)
    mock_conn.__exit__ = mocker.Mock(return_value=None)
    
    # Setup the context manager for cursor
    mock_cursor.__enter__ = mocker.Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = mocker.Mock(return_value=None)
    
    # Connect cursor to connection
    mock_conn.cursor.return_value = mock_cursor
    
    # Mock get_db to return our mock connection
    mocker.patch("backend.auth_service.routes.get_db", return_value=mock_conn)
    
    return mock_conn, mock_cursor
