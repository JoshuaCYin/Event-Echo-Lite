import os
from datetime import datetime
import pytz  # pip install pytz
from flask import Blueprint, request, jsonify
from openai import OpenAI, APIError, APIConnectionError, AuthenticationError, RateLimitError

# Create a Blueprint for AI routes
ai_blueprint = Blueprint('ai', __name__)

# Retrieve the OpenAI API key from environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Initialize the OpenAI client
try:
    if OPENAI_API_KEY:
        client = OpenAI(api_key=OPENAI_API_KEY)
    else:
        client = None
        print("WARNING: OPENAI_API_KEY is missing. AI Service will not function.")
except Exception as e:
    client = None
    print(f"Error initializing OpenAI client: {e}")

# System prompt defining assistant behavior and tone
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
    Expects JSON input: {"prompt": "User's message", "user_time": "...", "timezone": "..."}
    Returns JSON output: {"response": "AI's reply"}
    """

    if not client:
        return jsonify({
            "error": "AI service is not configured or failed to initialize (check OPENAI_API_KEY).",
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

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # fast GPT-4 model, supports markdown
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": contextual_prompt}
            ],
            temperature=0.7
        )

        ai_response = response.choices[0].message.content.strip()

        if not ai_response:
            return jsonify({
                "error": "Empty response received from the AI service. Please try again."
            }), 500

        # Return markdown-ready text, frontend can render directly
        return jsonify({"response": ai_response})

    except AuthenticationError:
        return jsonify({"error": "Authentication failed. Check your OPENAI_API_KEY."}), 401

    except RateLimitError:
        return jsonify({"error": "Rate limit reached. Please try again later."}), 429

    except APIError as e:
        print(f"OpenAI API error: {e}")
        return jsonify({"error": "The AI service encountered an internal API error."}), 503

    except APIConnectionError as e:
        print(f"API connection error: {e}")
        return jsonify({"error": "Could not connect to the OpenAI API."}), 503

    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred while processing your request."}), 500
