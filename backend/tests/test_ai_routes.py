import pytest
from unittest.mock import MagicMock
import json

def test_chat_openai_success(client, mocker):
    # Mock ACTIVE_AI_SERVICE
    mocker.patch("backend.ai_service.routes.ACTIVE_AI_SERVICE", "openai")
    
    # Mock OpenAI client
    mock_openai = MagicMock()
    mocker.patch("backend.ai_service.routes.openai_client", mock_openai)
    
    # Mock response
    mock_response = MagicMock()
    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "submit_chat_response"
    mock_tool_call.function.arguments = json.dumps({
        "response": "Hello!",
        "eventDraft": None
    })
    mock_response.choices[0].message.tool_calls = [mock_tool_call]
    mock_openai.chat.completions.create.return_value = mock_response

    payload = {
        "prompt": "Hello",
        "history": [],
        "user_time": "2025-01-01T10:00:00"
    }
    
    response = client.post("/ai/chat", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["response"] == "Hello!"

def test_chat_gemini_success(client, mocker):
    # Mock ACTIVE_AI_SERVICE
    mocker.patch("backend.ai_service.routes.ACTIVE_AI_SERVICE", "gemini")
    
    # Mock Gemini model
    mock_gemini = MagicMock()
    mocker.patch("backend.ai_service.routes.gemini_model", mock_gemini)
    
    # Mock types to avoid validation error
    mock_types = MagicMock()
    mocker.patch("backend.ai_service.routes.types", mock_types)
    
    # Mock response
    mock_gen_response = MagicMock()
    mock_gen_response.text = json.dumps({
        "response": "Hello from Gemini!",
        "eventDraft": None
    })
    mock_gemini.generate_content.return_value = mock_gen_response

    payload = {
        "prompt": "Hello",
        "history": [],
        "user_time": "2025-01-01T10:00:00"
    }
    
    response = client.post("/ai/chat", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["response"] == "Hello from Gemini!"

def test_wizard_helper_openai(client, mocker):
    mocker.patch("backend.ai_service.routes.ACTIVE_AI_SERVICE", "openai")
    mock_openai = MagicMock()
    mocker.patch("backend.ai_service.routes.openai_client", mock_openai)
    
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "response": "Sure, I can help.",
        "actions": [{"field": "w-title", "value": "New Title"}]
    })
    mock_openai.chat.completions.create.return_value = mock_response

    payload = {
        "prompt": "Change title to New Title",
        "context": "wizard",
        "current_values": {}
    }
    
    response = client.post("/ai/wizard-helper", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["actions"][0]["value"] == "New Title"

def test_chat_no_service_configured(client, mocker):
    mocker.patch("backend.ai_service.routes.ACTIVE_AI_SERVICE", None)
    
    payload = {"prompt": "Hello"}
    response = client.post("/ai/chat", json=payload)
    assert response.status_code == 500
    assert "AI service is not configured" in response.get_json()["error"]
