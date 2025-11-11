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
        "location": {"type": "string", "description": "A suggested physical location, building name, or address. (e.g., 'Chapel Auditorium' or '123 Main St')"}
    },
    "required": ["title", "description"]
}

DRAFTING_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {"type": "string", "description": "The conversational, user-facing chat response (can be markdown)."},
        "eventDraft": {
            "type": ["object", "null"],
            "description": "The event draft object. This MUST be null unless the user explicitly asks for a draft or a new event idea.",
            "properties": EVENT_DRAFT_SCHEMA["properties"]
        }
    },
    "required": ["response", "eventDraft"]
}


# 1. Try to initialize OpenAI first (as requested)
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        ACTIVE_AI_SERVICE = "openai"
        print("INFO: Successfully initialized OpenAI client. Using as default AI service.")
    except Exception as e:
        openai_client = None
        print(f"WARNING: OpenAI client initialization failed: {e}. Trying fallback.")

# 2. If OpenAI failed, try Gemini
if ACTIVE_AI_SERVICE is None and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        gemini_schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                'response': types.Schema(type=types.Type.STRING, description=DRAFTING_RESPONSE_SCHEMA['properties']['response']['description']),
                'eventDraft': types.Schema(
                    type=types.Type.OBJECT,
                    description=DRAFTING_RESPONSE_SCHEMA['properties']['eventDraft']['description'],
                    properties={
                        'title': types.Schema(type=types.Type.STRING, description=EVENT_DRAFT_SCHEMA['properties']['title']['description']),
                        'description': types.Schema(type=types.Type.STRING, description=EVENT_DRAFT_SCHEMA['properties']['description']['description']),
                        'location': types.Schema(type=types.Type.STRING, description=EVENT_DRAFT_SCHEMA['properties']['location']['description']),
                    },
                    nullable=True
                )
            },
            required=["response", "eventDraft"]
        )

        gemini_model = genai.GenerativeModel(
            'gemini-1.5-flash',
            generation_config=types.GenerationConfig(
                response_mime_type="application/json",
                response_schema=gemini_schema,
            )
        )
        ACTIVE_AI_SERVICE = "gemini"
        print("INFO: Successfully initialized Gemini client with JSON mode. Using as fallback AI service.")
    except Exception as e:
        gemini_model = None
        print(f"WARNING: Gemini client initialization failed: {e}.")

if ACTIVE_AI_SERVICE is None:
    print("CRITICAL: No AI service could be initialized. AI endpoints will fail.")


# --- System Prompt (Main Chatbot) ---
# --- FIX: Added "You MUST reply in the specified JSON format." to fix 400 error ---
MAIN_SYSTEM_PROMPT = f"""
You are an AI assistant for the "EventEcho" campus event planning app.
Your identity: You are the "EventEcho AI Assistant". You are powered by {ACTIVE_AI_SERVICE}.
Your role is to be helpful, professional, and concise.
*** CRITICAL: You MUST reply in the specified JSON format. ***

**CRITICAL RULE: DO NOT HALLUCINATE OR INVENT EVENTS.**
You will be given a list of "Upcoming Public Events". This is the *only* source of truth.
If the list is empty or an event is not on the list, you MUST state that you do not have that information or that there are no upcoming events.
*Do not, under any circumstances, create a fake event, even as an example.*

You have two main capabilities:
1. CONVERSATION: Answer questions about event planning, campus, or the provided event data.
2. EVENT DRAFTING: If the user asks you to create, draft, or "make an event" about something, you MUST generate a draft.

**RULES:**
- You will be given the user's conversation history. Use it to understand the context.
- **DRAFTING:** If the user's latest prompt is a request for a new event (e.g., "draft a description for a workshop", "make an event for a fundraiser"), you MUST populate the `eventDraft` object.
- **NO DRAFTING:** If the user is just chatting or asking a question, you MUST set `eventDraft` to `null`.
- Always provide a friendly, conversational `response` in markdown.
"""

@ai_blueprint.route('/chat', methods=['POST'])
def handle_chat():
    if ACTIVE_AI_SERVICE is None:
        return jsonify({"error": "AI service is not configured."}), 500

    data = request.json or {}
    user_prompt = data.get("prompt")
    history = data.get("history", [])
    event_context = data.get("event_context", "No live event data was provided.")

    if not user_prompt:
        return jsonify({"error": "No prompt provided."}), 400

    try:
        # --- FIX: Prioritize OpenAI as requested ---
        if ACTIVE_AI_SERVICE == "openai":
            messages = [{"role": "system", "content": MAIN_SYSTEM_PROMPT}]
            messages.append({"role": "system", "content": f"--- UPCOMING PUBLIC EVENTS ---\n{event_context}\n------------------------------"})
            
            for item in history:
                role = "assistant" if item["role"] == "ai" else item["role"]
                messages.append({"role": role, "content": item["content"]})
            
            messages.append({"role": "user", "content": user_prompt})

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                response_format={"type": "json_object"} # Request JSON output
            )
            result_json = json.loads(response.choices[0].message.content)
            return jsonify(result_json)

        elif ACTIVE_AI_SERVICE == "gemini":
            # --- Gemini Logic (Fallback) ---
            
            # --- FIX: Correctly map 'ai' to 'model' for Gemini history ---
            gemini_history = []
            for item in history:
                role = "model" if item["role"] == "ai" else "user"
                gemini_history.append(types.Part(text=item["content"], role=role))
            
            # --- FIX: Use system_instruction for main prompt, contents for history ---
            system_instruction = f"{MAIN_SYSTEM_PROMPT}\n\n--- UPCOMING PUBLIC EVENTS ---\n{event_context}\n------------------------------"
            
            contents = [
                *gemini_history,
                types.Part(text=user_prompt, role="user"),
                types.Part(text="", role="model") # Start the response
            ]

            response = gemini_model.generate_content(
                contents=contents,
                system_instruction=system_instruction
            )
            result_json = json.loads(response.text)
            return jsonify(result_json)

    # --- Error Handling ---
    except (OpenAIAuthError, GeminiAPIError) as e:
        if "API key" in str(e): return jsonify({"error": f"{ACTIVE_AI_SERVICE} Authentication failed. Check API key."}), 401
    except (OpenAIRateLimitError, GeminiAPIError) as e:
        if "rate limit" in str(e): return jsonify({"error": f"{ACTIVE_AI_SERVICE} rate limit reached."}), 429
    except (OpenAIAPIError, OpenAIConnectionError, GeminiAPIError) as e:
        print(f"AI API error: {e}")
        return jsonify({"error": f"The {ACTIVE_AI_SERVICE} service encountered an internal error: {str(e)}"}), 503
    except Exception as e:
        print(f"Unexpected error in /chat: {e}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}", "service": ACTIVE_AI_SERVICE}), 500


# --- Wizard Helper Chatbot ---
# --- FIX: Updated prompt to be a brainstormer, not a guardrail ---
WIZARD_SYSTEM_PROMPT = """
You are an AI brainstorming partner for an event creation wizard.
Your role is to provide creative, concise, and helpful suggestions.
The user is on a specific step, provided in the 'context'.
Your answer MUST be helpful for that context.
Be friendly, but stay on topic. DO NOT be conversational.
If the user asks for "3 titles", give 3 titles.
If the user asks for a "description", write a 1-2 sentence description.
If the user asks something unrelated (e.g., "what's the weather"),
politely decline: "I can only help with ideas for your event. For other questions, please use the main 'AI Assistant' tab."
"""

@ai_blueprint.route('/wizard-helper', methods=['POST'])
def handle_wizard_helper():
    if ACTIVE_AI_SERVICE is None:
        return jsonify({"error": "AI service is not configured."}), 500

    data = request.json or {}
    user_prompt = data.get("prompt")
    context = data.get("context", "the current step")

    if not user_prompt:
        return jsonify({"error": "No prompt provided."}), 400

    full_prompt = f"Context: {context}\nUser: {user_prompt}"

    try:
        ai_response = ""
        # --- FIX: Prioritize OpenAI ---
        if ACTIVE_AI_SERVICE == "openai":
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": WIZARD_SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7
            )
            ai_response = response.choices[0].message.content.strip()

        elif ACTIVE_AI_SERVICE == "gemini":
            text_only_model = genai.GenerativeModel('gemini-1.5-flash')
            response = text_only_model.generate_content(
                [WIZARD_SYSTEM_PROMPT, full_prompt],
                generation_config=types.GenerationConfig(temperature=0.7)
            )
            ai_response = response.text.strip()

        if not ai_response:
            return jsonify({"error": "Empty response from AI."}), 500
            
        return jsonify({"response": ai_response})

    except Exception as e:
        print(f"Unexpected error in /wizard-helper: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500