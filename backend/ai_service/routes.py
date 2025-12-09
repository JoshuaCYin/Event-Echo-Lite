import os
from datetime import datetime
import json
from typing import Dict, Any, Optional, Union, Tuple

from flask import Blueprint, request, jsonify, Response

# --- DATABASE IMPORT ---
try:
    from backend.database.db_connection import get_db
except ImportError:
    print("WARNING: Could not import get_db. AI service will not have live DB access.")
    get_db = None

# --- OPENAI IMPORTS ---
from openai import OpenAI

# --- GEMINI IMPORTS ---
import google.genai as genai
from google.genai import types

# --- BLUEPRINT SETUP ---
ai_blueprint = Blueprint('ai', __name__)

# --- API KEY RETRIEVAL ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- CLIENT INITIALIZATION ---
openai_client = None
gemini_model = None
ACTIVE_AI_SERVICE = None

# --- JSON SCHEMA DEFINITIONS ---
EVENT_DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "A creative and descriptive event title."
        },
        "description": {
            "type": "string",
            "description": "A 1-2 paragraph event description, formatted with markdown (e.g., line breaks)."
        },
        "location": {
            "type": "string",
            "description": "A suggested physical location, building name, or address. (e.g., 'Chapel Auditorium' or '123 Main St')"
        },
        "start_time": {
            "type": "string",
            "description": "The ISO 8601 formatted start date and time for the event, **MUST END IN 'Z'** to denote UTC (e.g., 2024-10-25T10:00:00Z)."
        },
        "end_time": {
            "type": "string",
            "description": "The ISO 8601 formatted end date and time for the event, **MUST END IN 'Z'** to denote UTC (e.g., 2024-10-25T10:00:00Z). Should be after start_time"}
    },
    "required": ["title", "description"]
}

CHAT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {"type": "string", "description": "The AI's conversational response to the user."},
        "eventDraft": {
            "type": "object",
            "nullable": True,
            "description": "An event draft object, or null.",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "location": {"type": "string"},
                "start_time": {"type": "string"},
                "end_time": {"type": "string"}
            }
        }
    },
    "required": ["response"]
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


# --- SYSTEM PROMPTS ---
MAIN_SYSTEM_PROMPT = f"""
You are the "EventEcho AI Assistant".
Your goal is to be a helpful event planning assistant.
You MUST call the `submit_chat_response` tool to respond.

**CONTEXT:**
You will be given the current user's time, a list of "Upcoming Public Events", and a "User Profile".
This event list is your source of truth. It *only* contains future events.
Current User Time: {{user_time_placeholder}}

**USER PROFILE:**
{{user_profile_placeholder}}

CRITICAL TIME RULES:
- When the user asks for "the time", "the date", "what day is it", or any similar question:
  ALWAYS answer using the provided User Time.
- NEVER generate or guess the current time yourself.
- NEVER use UTC or the server's timezone.
- ALWAYS use the timezone encoded inside User Time (e.g., "-05:00" or "+02:00").
- ALWAYS show the time in the user's local timezone.
- You MUST assume the user lives in that timezone.

When presenting the time, restate it clearly in the user's local timezone, e.g.:
"Your local time is 3:12 PM (UTC-05:00) on November 27, 2025."

IMPORTANT: User Time is the *only* correct current time.

**TASKS:**
1.  **Answer Questions:** Answer user questions about event planning or the provided event data.
2.  **Check Events:** When asked to "check upcoming events", ONLY use the event context. Do NOT invent events or show past events unless specifically asked "show me past events".
3.  **Personalized Recommendations:**
    * If the user asks for recommendations (e.g., "What should I attend?", "Recommend something"), compare the **User Profile** (interests, major, bio) with the **Upcoming Public Events**.
    * Prioritize events that match their major or hobbies.
    * Explain *why* you are recommending them (e.g., "Since you are a Computer Science major, you might like the Hackathon.").
    * If no events match their profile specifically, recommend general popular events but mention that.
4.  **Event Drafts:**
    * Your conversational reply goes in the `response` field of the tool.
    * For simple chats, the `eventDraft` field MUST be `null`.
    * If the user asks "Help me draft an event", you MUST first ask follow-up questions to get (at minimum) a title, description, and suggested date/time.
    * Once you have those details, populate the `eventDraft` object in the tool.
    * `start_time` and `end_time` MUST be in future ISO 8601 format ('YYYY-MM-DDTHH:MM:SS').
"""

WIZARD_SYSTEM_PROMPT = """
You are an AI Co-Pilot for an event creation form.
**CRITICAL:** You MUST reply in JSON format.

Your Goal: Help the user fill out the form fields based on their request and the `current_values` provided.
1. `response`: A short, friendly, helpful message.
2. `actions`: An array of objects to autofill fields if applicable.

**Targetable Fields (IDs/Names):**
- Title: "w-title" (Wizard) or "evTitle" (Main Form)
- Description: "w-description" (Wizard) or "evDescription" (Main Form)
- Start Time: "w-start" (Wizard) or "evStart" (Main Form) - Use ISO 'YYYY-MM-DDTHH:MM' format
- End Time: "w-end" (Wizard) or "evEnd" (Main Form) - Use ISO 'YYYY-MM-DDTHH:MM' format
- w-start and w-end MUST use datetime-local format: "YYYY-MM-DDTHH:MM"
- Location Type: "w-location_type" (Wizard) or "location_type" (Main Form) - Value must be "custom" or "venue"
- Venue (Select): "w-venue" (Wizard) - Value should be a venue ID (e.g., '1', '2') if known, or just a name.
- Custom Address: "w-customLocation" (Wizard) or "evCustomLocation" (Main Form)
- Visibility: "w-visibility" (Wizard) or "visibility" (Main Form) - Value must be "public" or "private"
- Apply actions when the user requests or hints at a change.

**Rules:**
- **CRITICAL: Only return ONE action per field.** For example, do not return two separate actions for "w-description" in the same response.
- If the user asks for suggestions (e.g., "Give me 3 titles"), provide them in the `response` text using Markdown lists. DO NOT fill `actions` yet.
- If the user asks to "Rewrite this", "Change the title to X", or "Make it start at 2pm", populate the `actions` array with the specific field and new value.
- If you update `w-venue` or `w-customLocation`, also add an action to update `w-location_type` to "venue" or "custom" respectively.
- Keep `response` brief (under 100 words).
"""

# --- ROUTES ---

@ai_blueprint.route('/chat', methods=['POST'])
def handle_chat() -> Tuple[Response, int]:
    """
    Handle chat interactions with OpenAI or Gemini.
    
    Expects:
    - prompt (str)
    - history (list)
    - event_context (str)
    - user_profile (dict)
    - user_time (str or dict)
    
    Returns:
        200: JSON response from AI.
        500: Server/AI error.
    """
    if ACTIVE_AI_SERVICE is None:
        return jsonify({"error": "AI service is not configured."}), 500

    data: Dict[str, Any] = request.json or {}
    user_prompt = data.get("prompt")
    history = data.get("history", [])
    event_context = data.get("event_context", "No live event data provided.")
    user_profile_data = data.get("user_profile", {}) 

    # Normalize user_time into a readable string for the system prompt
    raw_user_time = data.get("user_time")
    user_time = "Unknown"

    if isinstance(raw_user_time, dict):
        iso = raw_user_time.get("iso")
        offset = raw_user_time.get("offset")
        local = raw_user_time.get("local")
        user_time = f"{local} (ISO={iso}, UTC offset={offset} minutes)"
    else:
        if raw_user_time:
            user_time = str(raw_user_time)
        else:
            user_time = datetime.now().astimezone().isoformat()

    if not user_prompt:
        return jsonify({"error": "No prompt provided."}), 400
        
    # --- Format User Profile for Prompt ---
    if user_profile_data and "error" not in user_profile_data:
        profile_str = (
            f"- Name: {user_profile_data.get('first_name')} {user_profile_data.get('last_name')}\n"
            f"- Major: {user_profile_data.get('major_department', 'Undeclared')}\n"
            f"- Hobbies/Interests: {user_profile_data.get('hobbies', 'None listed')}\n"
            f"- Bio: {user_profile_data.get('bio', 'None')}"
        )
    else:
        profile_str = "No specific user profile data available (User might be guest or has empty profile)."

    # --- Insert dynamic data into the system prompt ---
    system_prompt = MAIN_SYSTEM_PROMPT.replace(
        "{user_time_placeholder}", 
        user_time
    ).replace(
        "{user_profile_placeholder}",
        profile_str
    )

    try:
        if ACTIVE_AI_SERVICE == "openai":
            messages = [{"role": "system", "content": system_prompt}]
            for item in history:
                role = "assistant" if item["role"] == "ai" else item["role"]
                messages.append({"role": role, "content": item["content"]})
            
            messages.append({"role": "user", "content": user_prompt})
            messages.append({"role": "system", "content": f"--- EVENTS ---\n{event_context}"})

            # --- Use tool calling with schema ---
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "submit_chat_response",
                            "description": "Submit your final response and event draft.",
                            "parameters": CHAT_RESPONSE_SCHEMA
                        }
                    }
                ],
                tool_choice={"type": "function", "function": {"name": "submit_chat_response"}}
            )
            
            # Extract the tool call arguments
            tool_call = response.choices[0].message.tool_calls[0]
            if tool_call.function.name == "submit_chat_response":
                result_json = json.loads(tool_call.function.arguments)

                draft = result_json.get('eventDraft')

                if draft:
                    # PATCH to enforce UTC format (YYYY-MM-DDTHH:MM:SSZ)
                    for key in ['start_time', 'end_time']:
                        time_str = draft.get(key)
                        if (time_str and 
                            len(time_str) == 19 and 
                            time_str.count(':') == 2 and 
                            time_str.count('-') >= 2 and 
                            'T' in time_str and 
                            not (time_str.endswith('Z') or time_str[-6] in ('+', '-'))):
                            
                            draft[key] = time_str + 'Z'
                    
                    result_json['eventDraft'] = draft
                
                if "eventDraft" in result_json and result_json["eventDraft"]:
                    result_json["eventDraft"] = result_json["eventDraft"] 

                return jsonify(result_json)
            else:
                raise Exception("AI did not use the correct tool.")

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

            contents = [types.Part(text=system_prompt, role="user")]
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

            # --- PATCH to enforce UTC format in eventDraft ---
            draft = result_json.get('eventDraft')

            if draft:
                # PATCH to enforce UTC format (YYYY-MM-DDTHH:MM:SSZ)
                for key in ['start_time', 'end_time']:
                    time_str = draft.get(key)
                    if (time_str and 
                        len(time_str) == 19 and 
                        time_str.count(':') == 2 and 
                        time_str.count('-') >= 2 and 
                        'T' in time_str and 
                        not (time_str.endswith('Z') or time_str[-6] in ('+', '-'))):
                        
                        draft[key] = time_str + 'Z'
                
                result_json['eventDraft'] = draft

            if "eventDraft" in result_json and result_json["eventDraft"]:
                 result_json["eventDraft"] = result_json["eventDraft"]
            return jsonify(result_json)

    except Exception as e:
        print(f"Chat Error: {e}")
        return jsonify({"error": f"AI Error: {str(e)}"}), 500


@ai_blueprint.route('/wizard-helper', methods=['POST'])
def handle_wizard_helper() -> Tuple[Response, int]:
    """
    Handles specific field-level assistance (Wizard & Main Form).
    
    Returns:
        200: JSON with 'response' and 'actions'.
        500: AI/Server error.
    """
    if ACTIVE_AI_SERVICE is None:
        return jsonify({"error": "AI service is not configured."}), 500

    data = request.json or {}
    user_prompt = data.get("prompt")
    context = data.get("context", "general")
    history = data.get("history", [])
    
    current_values = data.get("current_values", {})
    user_time = data.get("user_time") 
    
    current_context_block = (
        f"Context: {context}\n"
        f"User Time: {user_time}\n"
        f"Current Values: {json.dumps(current_values)}\n"
    )

    try:
        if ACTIVE_AI_SERVICE == "openai":
            messages = [{"role": "system", "content": WIZARD_SYSTEM_PROMPT}]
            
            for item in history:
                role = "assistant" if item["role"] == "ai" else item["role"]
                messages.append({"role": role, "content": item["content"]})
            
            messages.append({"role": "user", "content": f"{current_context_block}\nUser Request: {user_prompt}"})

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            if "actions" not in result or result["actions"] is None:
                result["actions"] = []

            return jsonify(result)

        elif ACTIVE_AI_SERVICE == "gemini":
            gemini_wizard_schema = types.Schema(
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

            contents = [types.Part(text=WIZARD_SYSTEM_PROMPT, role="user")]
            
            for item in history:
                role = "model" if item["role"] == "ai" else "user"
                contents.append(types.Part(text=item["content"], role=role))
            
            contents.append(types.Part(text=f"{current_context_block}\nUser Request: {user_prompt}", role="user"))

            response = gemini_model.generate_content(
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=gemini_wizard_schema,
                    temperature=0.7
                )
            )
            result = json.loads(response.text)
            return jsonify(result)

    except Exception as e:
        print(f"Wizard Helper Error: {e}")
        return jsonify({"error": "Failed to process request."}), 500