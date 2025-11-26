import os
from datetime import datetime
import pytz
from flask import Blueprint, request, jsonify
import json

# --- Database Import ---
try:
    from backend.database.db_connection import get_db
except ImportError:
    print("WARNING: Could not import get_db. AI service will not have live DB access.")
    get_db = None

# --- OpenAI Imports ---
from openai import OpenAI
from openai import APIError as OpenAIAPIError
from openai import APIConnectionError as OpenAIConnectionError
from openai import AuthenticationError as OpenAIAuthError
from openai import RateLimitError as OpenAIRateLimitError

# --- Gemini Imports ---
import google.genai as genai
from google.genai import types
from google.genai.errors import APIError as GeminiAPIError

# --- Blueprint Setup ---
ai_blueprint = Blueprint('ai', __name__)

# --- API Key Retrieval ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- Client Initialization ---
openai_client = None
gemini_model = None
ACTIVE_AI_SERVICE = None

# --- JSON Schema Definitions ---
EVENT_DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "A creative and descriptive event title."},
        "description": {"type": "string", "description": "A 1-2 paragraph event description, formatted with markdown (e.g., line breaks)."},
        "location": {"type": "string", "description": "A suggested physical location, building name, or address. (e.g., 'Chapel Auditorium' or '123 Main St')"},
        "start_time": {"type": "string", "description": "Suggested start date and time in ISO 8601 format (e.g., '2025-11-25T14:00:00'). If user doesn't specify, suggest a reasonable future date/time."},
        "end_time": {"type": "string", "description": "Suggested end date and time in ISO 8601 format (e.g., '2025-11-25T16:00:00'). Should be after start_time."}
    },
    "required": ["title", "description"]
}

# Used for the Side-Car Wizard Helper
WIZARD_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {"type": "string", "description": "Helpful, concise text response to the user."},
        "actions": {
            "type": "array",
            "description": "List of actions to populate form fields.",
            "items": {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string", 
                        "enum": ["w-title", "w-description", "w-customLocation", "evTitle", "evDescription", "evCustomLocation"],
                        "description": "The specific HTML ID of the input field to populate."
                    },
                    "value": {"type": "string", "description": "The text value to put into the field."}
                },
                "required": ["field", "value"]
            }
        }
    },
    "required": ["response", "actions"]
}

# 1. Try to initialize OpenAI first
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        ACTIVE_AI_SERVICE = "openai"
        print("INFO: Successfully initialized OpenAI client.")
    except Exception as e:
        openai_client = None
        print(f"WARNING: OpenAI client initialization failed: {e}. Trying fallback.")

# 2. If OpenAI failed, try Gemini
if ACTIVE_AI_SERVICE is None and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Configure the schemas for Gemini
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        
        ACTIVE_AI_SERVICE = "gemini"
        print("INFO: Successfully initialized Gemini client.")
    except Exception as e:
        gemini_model = None
        print(f"WARNING: Gemini client initialization failed: {e}.")


# --- System Prompts ---

MAIN_SYSTEM_PROMPT = f"""
You are the "EventEcho AI Assistant". 
**CRITICAL:** You MUST reply in JSON format.

**CONTEXT:**
You will be given a list of "Upcoming Public Events" and "Conversation History".
This event list is the source of truth.

**TASKS:**
1. Answer user questions about event planning or data.
2. If the user asks to create/draft an event, populate the `eventDraft` object.

**EVENT DRAFT RULES:**
* For simple chats, `eventDraft` MUST be `null`.
* For creation requests, populate `eventDraft`.
* `start_time` and `end_time` MUST be ISO 8601 ('YYYY-MM-DDTHH:MM:SS').
"""

WIZARD_SYSTEM_PROMPT = """
You are an AI Co-Pilot for an event creation form.
**CRITICAL:** You MUST reply in JSON format.

Your Goal: Help the user fill out the form fields.
1. `response`: A short, friendly, helpful message.
2. `actions`: An array of objects to autofill fields if applicable.

**Targetable Fields (IDs):**
- Title: "w-title" (Wizard) or "evTitle" (Main Form)
- Description: "w-description" (Wizard) or "evDescription" (Main Form)
- Custom Address: "w-customLocation" (Wizard) or "evCustomLocation" (Main Form)

**Rules:**
- If the user asks for suggestions (e.g., "Give me 3 titles"), provide them in the `response` text using Markdown lists. DO NOT fill `actions` yet, as we don't know which one they want.
- If the user asks to "Rewrite this" or "Use [X] as the title", populate the `actions` array with the best option.
- Keep `response` brief (under 50 words).
"""

# --- Routes ---

@ai_blueprint.route('/chat', methods=['POST'])
def handle_chat():
    if ACTIVE_AI_SERVICE is None:
        return jsonify({"error": "AI service is not configured."}), 500

    data = request.json or {}
    user_prompt = data.get("prompt")
    history = data.get("history", [])
    event_context = data.get("event_context", "No live event data provided.")

    if not user_prompt:
        return jsonify({"error": "No prompt provided."}), 400

    try:
        if ACTIVE_AI_SERVICE == "openai":
            messages = [{"role": "system", "content": MAIN_SYSTEM_PROMPT}]
            for item in history:
                role = "assistant" if item["role"] == "ai" else item["role"]
                messages.append({"role": role, "content": item["content"]})
            
            messages.append({"role": "user", "content": user_prompt})
            messages.append({"role": "system", "content": f"--- EVENTS ---\n{event_context}"})

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                response_format={"type": "json_object"}
            )
            result_json = json.loads(response.choices[0].message.content)
            if "eventDraft" in result_json and result_json["eventDraft"]:
                result_json["showEventCreationButton"] = True
            return jsonify(result_json)

        elif ACTIVE_AI_SERVICE == "gemini":
            # Gemini JSON Schema Config
            response_schema = types.Schema(
                type=types.Type.OBJECT,
                properties={
                    'response': types.Schema(type=types.Type.STRING),
                    'eventDraft': types.Schema(
                        type=types.Type.OBJECT,
                        nullable=True,
                        properties={
                            'title': types.Schema(type=types.Type.STRING),
                            'description': types.Schema(type=types.Type.STRING),
                            'location': types.Schema(type=types.Type.STRING),
                            'start_time': types.Schema(type=types.Type.STRING),
                            'end_time': types.Schema(type=types.Type.STRING),
                        }
                    )
                },
                required=["response"]
            )

            contents = [types.Part(text=MAIN_SYSTEM_PROMPT, role="user")]
            for item in history:
                role = "model" if item["role"] == "ai" else "user"
                contents.append(types.Part(text=item["content"], role=role))
            
            contents.append(types.Part(text=f"{user_prompt}\n\nEvents Context:\n{event_context}", role="user"))

            response = gemini_model.generate_content(
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema
                )
            )
            result_json = json.loads(response.text)
            if "eventDraft" in result_json and result_json["eventDraft"]:
                result_json["showEventCreationButton"] = True
            return jsonify(result_json)

    except Exception as e:
        print(f"Chat Error: {e}")
        return jsonify({"error": f"AI Error: {str(e)}"}), 500


@ai_blueprint.route('/wizard-helper', methods=['POST'])
def handle_wizard_helper():
    """
    Handles specific field-level assistance (Wizard & Main Form).
    Returns JSON with 'response' and optional 'actions'.
    """
    if ACTIVE_AI_SERVICE is None:
        return jsonify({"error": "AI service is not configured."}), 500

    data = request.json or {}
    user_prompt = data.get("prompt")
    context = data.get("context", "general")
    
    # Optional: Allow passing current field values to help the AI rewrite them
    current_values = data.get("current_values", {})
    
    full_prompt = f"Context: {context}\nCurrent Values: {json.dumps(current_values)}\nUser Request: {user_prompt}"

    try:
        if ACTIVE_AI_SERVICE == "openai":
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": WIZARD_SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            return jsonify(result)

        elif ACTIVE_AI_SERVICE == "gemini":
            # Gemini Schema for Actions
            wizard_schema = types.Schema(
                type=types.Type.OBJECT,
                properties={
                    'response': types.Schema(type=types.Type.STRING),
                    'actions': types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                'field': types.Schema(type=types.Type.STRING),
                                'value': types.Schema(type=types.Type.STRING)
                            },
                            required=['field', 'value']
                        )
                    )
                },
                required=["response", "actions"]
            )

            response = gemini_model.generate_content(
                contents=[
                    types.Part(text=WIZARD_SYSTEM_PROMPT, role="user"),
                    types.Part(text=full_prompt, role="user")
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=wizard_schema,
                    temperature=0.7
                )
            )
            result = json.loads(response.text)
            return jsonify(result)

    except Exception as e:
        print(f"Wizard Helper Error: {e}")
        return jsonify({"error": "Failed to process request."}), 500