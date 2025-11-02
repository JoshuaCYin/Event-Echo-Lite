"""
Events service routes: create, read, update, delete events, and RSVP.
"""

from flask import Blueprint, request, jsonify
from backend.database.db_connection import get_db
from backend.auth_service.utils import verify_token_from_request
from backend.auth_service.routes import verify_token
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

events_bp = Blueprint("events", __name__)

def parse_dt(val):
    """
    Safely parse an ISO-8601 datetime string.
    """
    if not val:
        return None
    try:
        # datetime-local input format is 'YYYY-MM-DDTHH:MM'
        # fromisoformat handles this, and also full ISO strings
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
    - Logged in: Returns all 'public' events AND 'private' events
      created by the authenticated user.
    """
    # Check for authentication token (optional)
    auth_user_id = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        auth_user_id = verify_token(token) # Simple verify, doesn't reject

    # Base query selects public, upcoming events
    base_sql = """
        SELECT 
            e.event_id, e.title, e.description, e.start_time, e.end_time,
            e.location_type, e.custom_location_address, e.google_maps_link,
            e.status, e.visibility,
            v.name AS venue_name, v.building AS venue_building, v.room_number AS venue_room,
            u.first_name AS organizer_first_name, u.last_name AS organizer_last_name
        FROM events e
        LEFT JOIN venues v ON e.venue_id = v.venue_id
        LEFT JOIN users u ON e.organizer_id = u.user_id
        WHERE e.status = 'upcoming'
    """
    
    params = []
    
    if auth_user_id:
        # User is logged in: show public events OR their own private events
        base_sql += "AND (e.visibility = 'public' OR e.organizer_id = %s)"
        params.append(auth_user_id)
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

@events_bp.route("/", methods=["POST"])
def create_event():
    """
    Create an event. (Schema updated)
    Body JSON: {
        "title": "...", 
        "description": "...",
        "start_time": "ISO_STRING", 
        "end_time": "ISO_STRING",
        "location_type": "venue" | "custom",
        "venue_id": INT (if 'venue'),
        "custom_location_address": "..." (if 'custom'),
        "google_maps_link": "..." (optional),
        "visibility": "public" | "private" (optional, default 'public')
    }
    """
    user_id, role, err, code = verify_token_from_request(required_roles=["organizer", "admin"])
    if err:
        return err, code

    data = request.get_json() or {}
    
    # --- Data Validation ---
    title = data.get("title")
    start_str = data.get("start_time")
    end_str = data.get("end_time")
    
    if not title or not start_str or not end_str:
        return jsonify({"error": "title, start_time, and end_time are required"}), 400

    start_dt = parse_dt(start_str)
    end_dt = parse_dt(end_str)
    
    if not start_dt or not end_dt:
        return jsonify({"error": "Invalid datetime format. Use ISO-8601."}), 400
        
    if start_dt >= end_dt:
        return jsonify({"error": "start_time must be before end_time"}), 400

    # --- Location Handling ---
    location_type = data.get("location_type", "venue")
    venue_id = data.get("venue_id")
    custom_location = data.get("custom_location_address")
    
    if location_type == 'venue' and not venue_id:
        return jsonify({"error": "venue_id is required for location_type 'venue'"}), 400
    if location_type == 'custom' and not custom_location:
        return jsonify({"error": "custom_location_address is required for location_type 'custom'"}), 400

    # --- Optional Fields ---
    description = data.get("description")
    google_maps_link = data.get("google_maps_link")
    visibility = data.get("visibility", "public")
    if visibility not in ['public', 'private']:
        visibility = 'public'

    # --- Conflict Check (Simple) ---
    if location_type == 'venue':
        conflict_sql = """
            SELECT event_id FROM events
            WHERE venue_id = %s
            AND status = 'upcoming'
            AND (start_time, end_time) OVERLAPS (%s, %s);
        """
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(conflict_sql, (venue_id, start_dt, end_dt))
                    conflict = cur.fetchone()
                    if conflict:
                        return jsonify({"error": "Scheduling conflict detected at this venue"}), 409
        except Exception as e:
            print(f"Database error during conflict check: {e}")
            return jsonify({"error": "Failed to check for conflicts"}), 500

    # --- Insert Event ---
    sql = """
        INSERT INTO events (
            title, description, start_time, end_time, 
            location_type, venue_id, custom_location_address, google_maps_link,
            visibility, organizer_id, created_by, status
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, 'upcoming'
        )
        RETURNING event_id;
    """
    
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    title, description, start_dt, end_dt,
                    location_type, 
                    venue_id if location_type == 'venue' else None,
                    custom_location if location_type == 'custom' else None,
                    google_maps_link,
                    visibility, user_id, user_id
                ))
                new_event = cur.fetchone()
                conn.commit()
                event_id = new_event["event_id"]
    except Exception as e:
        print(f"Database error creating event: {e}")
        return jsonify({"error": "Failed to create event"}), 500

    return jsonify({"event_id": event_id}), 201

# --- /<int:event_id> PUT and DELETE (Omitted for brevity, unchanged) ---
# --- /<int:event_id>/rsvp POST (Omitted for brevity, unchanged) ---

