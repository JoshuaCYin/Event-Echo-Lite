import os
from datetime import datetime
import pytz  # pip install pytz
from flask import Blueprint, request, jsonify
from google import genai
from google.genai import types
from google.genai.errors import APIError

# Create a Blueprint for AI routes
ai_blueprint = Blueprint('ai', __name__)

# Retrieve the Gemini API key from environment variables
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize the Gemini client
# The client will automatically pick up the GEMINI_API_KEY environment variable.
try:
    if GEMINI_API_KEY:
        client = genai.Client()
    else:
        # Client needs to be defined even if key is missing for the check below
        client = None
        print("WARNING: GEMINI_API_KEY is missing. AI Service will not function.")
except Exception as e:
    # Handle environment or library initialization issues
    client = None
    print(f"Error initializing Gemini client: {e}")

# System prompt defining assistant behavior and tone
SYSTEM_PROMPT = """
Tell the user if you are an OpenAI model or Gemini model.
You are an AI assistant designed to help users with event-related inquiries. 
Be concise, professional, and friendly. 
If a question is unclear or unrelated, politely indicate that.
Always consider the user's current local date and time when providing time-sensitive advice.
"""

@ai_blueprint.route('/chat', methods=['POST'])
def handle_chat():
    """
    Handles incoming chat messages.
    Expects JSON input: {"prompt": "User's message", "user_time": "...", "timezone": "..."}
    Returns JSON output: {"response": "AI's reply"}
    """

    # Ensure the Gemini API key is configured and client is initialized
    if not client:
        return jsonify({
            "error": "AI service is not configured or failed to initialize (check GEMINI_API_KEY).",
            "client_status": "uninitialized"
        }), 500

    data = request.json or {}
    user_prompt = data.get("prompt")
    user_time = data.get("user_time") or datetime.utcnow().isoformat() + "Z"
    timezone = data.get("timezone", "UTC")

    if not user_prompt:
        return jsonify({"error": "No prompt provided."}), 400

    # Build a readable current time string for context
    try:
        # Convert provided user_time (ISO 8601 string) to datetime
        dt = datetime.fromisoformat(user_time.replace("Z", "+00:00"))
        tz = pytz.timezone(timezone)
        local_dt = dt.astimezone(tz)
        formatted_time = local_dt.strftime("%A, %B %d, %Y %I:%M %p %Z")
    except Exception as e:
        print(f"Time conversion error: {e}")
        formatted_time = "Unknown local time"

    # Add system context about current date/time
    contextual_prompt = (
        f"The user's local date and time is {formatted_time}.\n\n"
        f"User: {user_prompt}"
    )

    try:
        # Use the generate_content method
        response = client.models.generate_content(
            model='gemini-2.5-flash',  # A powerful, fast, and cost-effective model
            contents=contextual_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT
            )
        )

        # Extract the assistant's response
        ai_response = response.text.strip()

        # Check if the response contains text (may be empty if blocked)
        if not ai_response:
            # This happens if the prompt is blocked by safety filters
            reason = response.candidates[0].finish_reason.name
            error_msg = f"Request blocked due to safety policy. Finish Reason: {reason}"
            print(f"Content Blocked: {error_msg}")
            return jsonify({"error": error_msg}), 400

        return jsonify({"response": ai_response})

    except APIError as e:
        # Catch API-specific errors (e.g., rate limits, invalid keys, server issues)
        print(f"Gemini API error: {e}")
        error_message = str(e)
        if "API key not valid" in error_message:
            return jsonify({"error": "Authentication failed. Check your GEMINI_API_KEY."}), 401
        elif "rate limit" in error_message:
            return jsonify({"error": "Rate limit reached. Please try again later."}), 429
        else:
            return jsonify({"error": "The AI service encountered an internal API error."}), 503

    except Exception as e:
        # Catch unexpected errors to avoid crashing the server
        print(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred while processing your request."}), 500
