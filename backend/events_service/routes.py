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
    - Logged in: Returns all 'public' events AND 'private' events
      created by the authenticated user.
    """
    auth_user_id = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        auth_user_id = verify_token(token)

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
        base_sql += " AND (e.visibility = 'public' OR e.organizer_id = %s)"
        params.append(auth_user_id)
    else:
        # Not logged in: show only public events
        base_sql += " AND e.visibility = 'public'"

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
    Create an event.
    - Any authenticated user can create a 'private' event.
    - Only 'organizer' or 'admin' can create a 'public' event.
    """
    # 1. Verify any authenticated user
    user_id, role, err, code = verify_token_from_request()
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
    location_type = data.get("location_type", "custom") # Default to custom
    venue_id = data.get("venue_id")
    custom_location = data.get("custom_location_address")
    
    if location_type == 'venue' and not venue_id:
        return jsonify({"error": "venue_id is required for location_type 'venue'"}), 400
    if location_type == 'custom' and not custom_location:
        return jsonify({"error": "custom_location_address is required for location_type 'custom'"}), 400

    # --- Optional Fields & Visibility ---
    description = data.get("description")
    google_maps_link = data.get("google_maps_link")
    visibility = data.get("visibility", "public")
    
    if visibility not in ['public', 'private']:
        visibility = 'public'

    # 2. Permission Checks
    if visibility == 'public' and role not in ['organizer', 'admin']:
        return jsonify({
            "error": "Permission denied. Only organizers and admins can create public events."
        }), 403
        # (If an attendee submits 'private', this check passes)

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

@events_bp.route("/<int:event_id>", methods=["PUT"])
def update_event(event_id):
    """
    Update an event if the caller is the organizer or admin.
    Allows partial updates.
    """
    user_id, role, err, code = verify_token_from_request() # Get user first
    if err:
        return err, code

    data = request.get_json() or {}
    if not data:
        return jsonify({"error": "No update data provided"}), 400

    conn = get_db()
    try:
        # First, verify ownership or admin status
        with conn.cursor() as cur:
            cur.execute("SELECT organizer_id, created_by FROM events WHERE event_id = %s;", (event_id,))
            ev = cur.fetchone()
            if not ev:
                conn.close()
                return jsonify({"error": "Event not found"}), 404

            # Allow update if user is Admin, Organizer, or *created* the event
            if role not in ['admin', 'organizer'] and ev["created_by"] != user_id:
                conn.close()
                return jsonify({"error": "Permission denied"}), 403
            
            # Role-based check for visibility
            if 'visibility' in data and data['visibility'] == 'public':
                if role not in ['admin', 'organizer']:
                    conn.close()
                    return jsonify({"error": "Only organizers/admins can make events public"}), 403

        # --- Build partial update query ---
        fields = []
        values = []
        
        allowed_fields = [
            "title", "description", "start_time", "end_time", 
            "location_type", "venue_id", "custom_location_address", 
            "google_maps_link", "visibility", "status"
        ]
        
        for key in allowed_fields:
            if key in data:
                fields.append(f"{key} = %s")
                if key in ("start_time", "end_time"):
                    values.append(parse_dt(data[key]))
                else:
                    values.append(data[key])
        
        if "updated_at" not in fields:
             fields.append("updated_at = CURRENT_TIMESTAMP")

        if fields:
            values.append(event_id)
            sql = f"UPDATE events SET {', '.join(fields)} WHERE event_id = %s;"
            
            with conn.cursor() as cur:
                cur.execute(sql, values)
                conn.commit()
        else:
            return jsonify({"error": "No valid fields to update"}), 400

    except Exception as e:
        conn.rollback()
        print(f"Database error updating event {event_id}: {e}")
        return jsonify({"error": "Failed to update event"}), 500
    finally:
        if conn:
            conn.close()

    return jsonify({"status": "updated"}), 200

@events_bp.route("/<int:event_id>", methods=["DELETE"])
def delete_event(event_id):
    """
    Delete an event if the caller is the organizer, admin, or creator.
    """
    user_id, role, err, code = verify_token_from_request()
    if err:
        return err, code

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify ownership before deleting
                cur.execute("SELECT organizer_id, created_by FROM events WHERE event_id = %s;", (event_id,))
                ev = cur.fetchone()
                if not ev:
                    return jsonify({"error": "Event not found"}), 404

                # Allow delete if user is Admin, Organizer, or created the event
                if role not in ['admin', 'organizer'] and ev["created_by"] != user_id:
                    return jsonify({"error": "Permission denied"}), 403

                # Perform the delete
                cur.execute("DELETE FROM events WHERE event_id = %s;", (event_id,))
                conn.commit()
                
                if cur.rowcount == 0:
                    return jsonify({"error": "Event not found or already deleted"}), 404
                    
    except Exception as e:
        print(f"Database error deleting event {event_id}: {e}")
        return jsonify({"error": "Failed to delete event"}), 500

    return jsonify({"status": "deleted"}), 200

@events_bp.route("/<int:event_id>/rsvp", methods=["POST"])
def rsvp(event_id):
    """
    RSVP to an event. Uses PostgreSQL's "UPSERT" (ON CONFLICT)
    """
    user_id, _, err, code = verify_token_from_request()
    if err:
        return err, code

    data = request.get_json() or {}
    status = data.get("status", "going")
    
    if status not in ["going", "maybe", "canceled"]:
        return jsonify({"error": "Invalid status. Must be 'going', 'maybe', or 'canceled'"}), 400

    sql = """
        INSERT INTO rsvps (user_id, event_id, rsvp_status) 
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, event_id) 
        DO UPDATE SET rsvp_status = EXCLUDED.rsvp_status;
    """

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, event_id, status))
                conn.commit()
    except Exception as e:
        print(f"Database error RSVPing: {e}")
        return jsonify({"error": "Failed to RSVP. The event may not exist."}), 500

    return jsonify({"status": status}), 200
