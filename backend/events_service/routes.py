"""
Events service routes: create, read, update, delete events, and RSVP.
"""

from flask import Blueprint, request, jsonify
from backend.database.db_connection import get_db
from backend.auth_service.utils import verify_token_from_request
from backend.auth_service.routes import verify_token # Simple token check
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

events_bp = Blueprint("events", __name__)

def parse_dt(val):
    """
    Safely parse an ISO-8601 or datetime-local string.
    """
    if not val:
        return None
    try:
        # Handles 'YYYY-MM-DDTHH:MM' and '...Z' or '...+00:00'
        if val.endswith('Z'):
            val = val[:-1] + '+00:00'
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None

@events_bp.route("/", methods=["GET"])
def list_events():
    """
    Return all events based on user authentication.
    - Not logged in: Returns 'public' events only.
    - Logged in: Returns all 'public' events, user's private events,
      AND the user's RSVP status for each event.
    """
    auth_user_id = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        auth_user_id = verify_token(token)

    # --- SQL Update ---
    # 1. Added r.rsvp_status AS my_rsvp_status
    # 2. Added LEFT JOIN for rsvps table ON the logged-in user's ID
    # 3. Added e.created_by to the SELECT list for organizer checks
    base_sql = """
        SELECT 
            e.event_id, e.title, e.description, e.start_time, e.end_time,
            e.location_type, e.custom_location_address, e.google_maps_link,
            e.status, e.visibility, e.organizer_id, e.created_by,
            v.name AS venue_name, v.building AS venue_building, v.room_number AS venue_room,
            u.first_name AS organizer_first_name, u.last_name AS organizer_last_name,
            r.rsvp_status AS my_rsvp_status
        FROM events e
        LEFT JOIN venues v ON e.venue_id = v.venue_id
        LEFT JOIN users u ON e.organizer_id = u.user_id
        LEFT JOIN rsvps r ON e.event_id = r.event_id AND r.user_id = %s
        WHERE e.status = 'upcoming'
    """
    
    params = [auth_user_id] # First param is for the RSVP JOIN
    
    if auth_user_id:
        # User is logged in: show public events OR their own private events
        base_sql += "AND (e.visibility = 'public' OR e.organizer_id = %s OR e.created_by = %s)"
        params.extend([auth_user_id, auth_user_id])
    else:
        # Not logged in: show only public events
        base_sql += "AND e.visibility = 'public'"

    base_sql += " ORDER BY e.start_time;"

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(base_sql, params)
                rows = [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"Database error listing events: {e}")
        return jsonify({"error": "Failed to retrieve events"}), 500
        
    return jsonify(rows), 200

# ... [create_event, update_event, delete_event functions remain the same] ...
# (Assuming they exist from the previous file content)

@events_bp.route("/<int:event_id>/rsvp", methods=["POST"])
def rsvp(event_id):
    """
    RSVP to an event. Uses PostgreSQL's "UPSERT" (ON CONFLICT)
    """
    user_id, _, err, code = verify_token_from_request()
    if err:
        return err, code

    data = request.get_json() or {}
    status = data.get("status") # 'going', 'maybe', 'canceled', or None
    
    sql = ""
    params = []

    if status:
        # --- Create or Update RSVP (UPSERT) ---
        if status not in ["going", "maybe", "canceled"]:
            return jsonify({"error": "Invalid status. Must be 'going', 'maybe', or 'canceled'"}), 400
        
        sql = """
            INSERT INTO rsvps (user_id, event_id, rsvp_status) 
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, event_id) 
            DO UPDATE SET rsvp_status = EXCLUDED.rsvp_status;
        """
        params = (user_id, event_id, status)
    else:
        # --- Delete RSVP (if status is null or empty) ---
        sql = "DELETE FROM rsvps WHERE user_id = %s AND event_id = %s;"
        params = (user_id, event_id)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                conn.commit()
    except Exception as e:
        print(f"Database error RSVPing: {e}")
        return jsonify({"error": "Failed to RSVP. The event may not exist."}), 500

    return jsonify({"status": status or "cleared"}), 200


# --- NEW ENDPOINT: Get RSVP List ---
@events_bp.route("/<int:event_id>/rsvps", methods=["GET"])
def get_rsvps(event_id):
    """
    Get the list of attendees for an event.
    Protected: Only the event creator/organizer or an admin can see this.
    """
    user_id, role, err, code = verify_token_from_request()
    if err:
        return err, code

    sql = """
        SELECT u.user_id, u.first_name, u.last_name, u.email, r.rsvp_status
        FROM rsvps r
        JOIN users u ON r.user_id = u.user_id
        WHERE r.event_id = %s AND r.rsvp_status IN ('going', 'maybe');
    """
    
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # --- Permission Check ---
                cur.execute("SELECT organizer_id, created_by FROM events WHERE event_id = %s;", (event_id,))
                event = cur.fetchone()
                
                if not event:
                    return jsonify({"error": "Event not found"}), 404
                
                is_creator = (event["organizer_id"] == user_id) or (event["created_by"] == user_id)
                if role not in ['admin', 'organizer'] and not is_creator:
                    return jsonify({"error": "Permission denied. You are not the organizer."}), 403

                # --- Get Attendee List ---
                cur.execute(sql, (event_id,))
                attendees = [dict(row) for row in cur.fetchall()]
                
    except Exception as e:
        print(f"Database error getting RSVPs: {e}")
        return jsonify({"error": "Failed to retrieve attendee list"}), 500

    return jsonify(attendees), 200


# --- NEW ENDPOINT: Get User Profile (Read-Only) ---
@events_bp.route("/users/<int:user_id>/profile", methods=["GET"])
def get_user_profile(user_id):
    """
    Get public-facing profile info for a user.
    This is a read-only endpoint available to all logged-in users.
    """
    # Verify any logged-in user can access this
    _, _, err, code = verify_token_from_request()
    if err:
        return err, code
        
    sql = """
        SELECT user_id, first_name, last_name, email, 
               major_department, hobbies, bio, profile_picture
        FROM users
        WHERE user_id = %s;
    """
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                profile = cur.fetchone()
                if not profile:
                    return jsonify({"error": "User not found"}), 404
                return jsonify(dict(profile)), 200
                
    except Exception as e:
        print(f"Database error getting profile: {e}")
        return jsonify({"error": "Failed to retrieve profile"}), 500