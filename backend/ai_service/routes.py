import os
from datetime import datetime
import pytz  # pip install pytz
from flask import Blueprint, request, jsonify

# --- OpenAI Imports ---
# pip install openai
from openai import OpenAI
from openai import APIError as OpenAIAPIError
from openai import APIConnectionError as OpenAIConnectionError
from openai import AuthenticationError as OpenAIAuthError
from openai import RateLimitError as OpenAIRateLimitError

# --- Gemini Imports ---
# pip install google-generativeai
from google import genai
from google.genai import types
from google.genai.errors import APIError as GeminiAPIError

# --- Blueprint Setup ---
ai_blueprint = Blueprint('ai', __name__)

# --- API Key Retrieval ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- Client Initialization ---
openai_client = None
gemini_client = None
ACTIVE_AI_SERVICE = None  # Will be 'openai' or 'gemini'

# 1. Try to initialize OpenAI first
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        ACTIVE_AI_SERVICE = "openai"
        print("INFO: Successfully initialized OpenAI client. Using as default AI service.")
    except Exception as e:
        openai_client = None
        print(f"WARNING: OpenAI client initialization failed: {e}. Trying fallback.")

# 2. If OpenAI failed or wasn't configured, try to initialize Gemini
if ACTIVE_AI_SERVICE is None and GEMINI_API_KEY:
    try:
        # The client automatically uses the env var
        gemini_client = genai.Client() 
        ACTIVE_AI_SERVICE = "gemini"
        print("INFO: Successfully initialized Gemini client. Using as fallback AI service.")
    except Exception as e:
        gemini_client = None
        print(f"WARNING: Gemini client initialization failed: {e}.")

# 3. Final check
if ACTIVE_AI_SERVICE is None:
    print("CRITICAL: No AI service could be initialized. Check OPENAI_API_KEY and GEMINI_API_KEY.")

# --- System Prompt (Shared) ---
SYSTEM_PROMPT = """
Tell the user if you are an OpenAI model or Gemini model.
You are an AI assistant designed to help users with event-related inquiries. 
Be concise, professional, and friendly. 
If a question is unclear or unrelated, politely indicate that.
Always consider the user's current local date and time when providing time-sensitive advice.
Your responses may include markdown formatting (e.g., **bold**, *italics*, lists, or code blocks) when appropriate for clarity.
"""

@ai_blueprint.route('/chat', methods=['POST'])
def handle_chat():
    """
    Handles incoming chat messages.
    Routes to OpenAI if available, otherwise falls back to Gemini.
    """

    # Check if any service was successfully initialized
    if ACTIVE_AI_SERVICE is None:
        return jsonify({
            "error": "No AI service is configured or available. Check server logs for API key errors.",
            "client_status": "uninitialized"
        }), 500

    # --- Common Request Handling ---
    data = request.json or {}
    user_prompt = data.get("prompt")
    user_time = data.get("user_time") or datetime.utcnow().isoformat() + "Z"
    timezone = data.get("timezone", "UTC")

    if not user_prompt:
        return jsonify({"error": "No prompt provided."}), 400

    # Build a readable current time string for context
    try:
        dt = datetime.fromisoformat(user_time.replace("Z", "+00:00"))
        tz = pytz.timezone(timezone)
        local_dt = dt.astimezone(tz)
        formatted_time = local_dt.strftime("%A, %B %d, %Y %I:%M %p %Z")
    except Exception as e:
        print(f"Time conversion error: {e}")
        formatted_time = "Unknown local time"

    contextual_prompt = (
        f"The user's local date and time is {formatted_time}.\n\n"
        f"User: {user_prompt}"
    )

    # --- Service-Specific Logic ---
    try:
        ai_response = ""

        if ACTIVE_AI_SERVICE == "openai":
            # --- OpenAI Logic ---
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": contextual_prompt}
                ],
                temperature=0.7
            )
            ai_response = response.choices[0].message.content.strip()

        elif ACTIVE_AI_SERVICE == "gemini":
            # --- Gemini Logic ---
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contextual_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT
                )
            )
            ai_response = response.text.strip()
            
            # Check for safety blocks
            if not ai_response:
                reason = response.candidates[0].finish_reason.name
                error_msg = f"Request blocked due to safety policy. Finish Reason: {reason}"
                print(f"Content Blocked: {error_msg}")
                return jsonify({"error": error_msg}), 400

        # --- Common Success Response ---
        if not ai_response:
            return jsonify({
                "error": "Empty response received from the AI service. Please try again."
            }), 500
        
        return jsonify({"response": ai_response})

    # --- Service-Specific Error Handling ---
    except OpenAIAuthError:
        return jsonify({"error": "OpenAI Authentication failed. Check your OPENAI_API_KEY."}), 401
    except OpenAIRateLimitError:
        return jsonify({"error": "OpenAI rate limit reached. Please try again later."}), 429
    except OpenAIAPIError as e:
        print(f"OpenAI API error: {e}")
        return jsonify({"error": "The OpenAI service encountered an internal API error."}), 503
    except OpenAIConnectionError as e:
        print(f"OpenAI connection error: {e}")
        return jsonify({"error": "Could not connect to the OpenAI API."}), 503

    except GeminiAPIError as e:
        print(f"Gemini API error: {e}")
        error_message = str(e)
        if "API key not valid" in error_message:
            return jsonify({"error": "Gemini Authentication failed. Check your GEMINI_API_KEY."}), 401
        elif "rate limit" in error_message:
            return jsonify({"error": "Gemini rate limit reached. Please try again later."}), 429
        else:
            return jsonify({"error": "The Gemini AI service encountered an internal API error."}), 503

    # --- Generic Error Handling ---
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred while processing your request."}), 500