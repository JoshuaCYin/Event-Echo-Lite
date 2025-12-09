"""
Events service routes: create, read, update, delete events, and RSVP.
Handles event lifecycle management and participation.
"""

import os
from datetime import datetime
from typing import Tuple, Dict, Any, Optional

from flask import Blueprint, request, jsonify, Response
from dotenv import load_dotenv

from backend.database.db_connection import get_db
from backend.auth_service.utils import verify_token_from_request, verify_token

load_dotenv()

events_bp = Blueprint("events", __name__)

# --- CONSTANTS FOR VALIDATION ---
TITLE_MAX_LENGTH = 200
VALID_VISIBILITY = ['public', 'private']
VALID_LOCATION_TYPES = ['venue', 'custom']
VALID_STATUSES = ['upcoming', 'cancelled', 'completed'] 

def parse_dt(val: Optional[str]) -> Optional[datetime]:
    """
    Safely parse an ISO-8601 or datetime-local string to a datetime object.
    
    Args:
        val (str): The date string to parse.
    
    Returns:
        datetime: The parsed datetime, or None if invalid.
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
def list_events() -> Tuple[Response, int]:
    """
    Return all events based on user authentication.
    
    Query Logic:
    - If logged in: Returns public events + user's private events.
    - If anonymous: Returns only public events.
    - Includes aggregate data: attendee_count, avg_rating, review_count.
    
    Returns:
        200: List of event objects.
        500: Database error.
    """
    auth_user_id = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        auth_user_id = verify_token(token)

    # Complex Query Explanation:
    # 1. Joins events with venues and users (organizers).
    # 2. Left join on rsvps to check if the current user has RSVP'd.
    # 3. Subqueries calculate attendee counts and review stats per event.
    base_sql = """
        SELECT 
            e.event_id, e.title, e.description, 
            e.start_time AT TIME ZONE 'UTC' as start_time, 
            e.end_time AT TIME ZONE 'UTC' as end_time,
            e.location_type, e.custom_location_address, e.google_maps_link,
            e.status, e.visibility, e.organizer_id, e.created_by,
            v.name AS venue_name, v.building AS venue_building, v.room_number AS venue_room,
            u.first_name AS organizer_first_name, u.last_name AS organizer_last_name,
            r.rsvp_status AS my_rsvp_status,
            e.venue_id,
            (SELECT COUNT(*) FROM rsvps WHERE rsvps.event_id = e.event_id AND rsvps.rsvp_status = 'going') as attendee_count,
            
            (SELECT AVG(rating) FROM event_reviews WHERE event_reviews.event_id = e.event_id) as avg_rating,
            (SELECT COUNT(*) FROM event_reviews WHERE event_reviews.event_id = e.event_id) as review_count

        FROM events e
        LEFT JOIN venues v ON e.venue_id = v.venue_id
        LEFT JOIN users u ON e.organizer_id = u.user_id
        LEFT JOIN rsvps r ON e.event_id = r.event_id AND r.user_id = %s
        WHERE 1=1
    """
    
    params = [auth_user_id] 
    
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
                
                # Explicitly ensure ISO format strings for JSON serialization
                for row in rows:
                    if row.get('start_time'):
                        row['start_time'] = row['start_time'].isoformat()
                    if row.get('end_time'):
                        row['end_time'] = row['end_time'].isoformat()
                    # Convert decimal rating to float
                    if row.get('avg_rating'):
                        row['avg_rating'] = float(row['avg_rating'])

    except Exception as e:
        print(f"Database error listing events: {e}")
        return jsonify({"error": "Failed to retrieve events"}), 500
        
    return jsonify(rows), 200


@events_bp.route("/<int:event_id>", methods=["GET"])
def get_event(event_id: int) -> Tuple[Response, int]:
    """
    Get a single event by ID.

    Features:
    - Checks visibility permissions (public vs private).
    - Returns detailed info including venue and review stats.

    Returns:
        200: Event object.
        403: Permission denied (private event, not owner).
        404: Event not found.
    """
    auth_user_id = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        auth_user_id = verify_token(token)

    sql = """
        SELECT 
            e.event_id, e.title, e.description, 
            e.start_time AT TIME ZONE 'UTC' as start_time,
            e.end_time AT TIME ZONE 'UTC' as end_time,
            e.location_type, e.custom_location_address, e.google_maps_link,
            e.status, e.visibility, e.organizer_id, e.created_by, e.venue_id,
            v.name AS venue_name,
            (SELECT COUNT(*) FROM rsvps WHERE rsvps.event_id = e.event_id AND rsvps.rsvp_status = 'going') as attendee_count,
            
            (SELECT AVG(rating) FROM event_reviews WHERE event_reviews.event_id = e.event_id) as avg_rating,
            (SELECT COUNT(*) FROM event_reviews WHERE event_reviews.event_id = e.event_id) as review_count

        FROM events e
        LEFT JOIN venues v ON e.venue_id = v.venue_id
        WHERE e.event_id = %s
    """
    
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (event_id,))
                event = cur.fetchone()
                
                if not event:
                    return jsonify({"error": "Event not found"}), 404

                # Privacy Check
                is_public = event['visibility'] == 'public'
                is_owner = auth_user_id and (event['organizer_id'] == auth_user_id or event['created_by'] == auth_user_id)
                
                if not is_public and not is_owner:
                    return jsonify({"error": "Permission denied"}), 403

                # Convert to dict and ensure datetime ISO format
                event_dict = dict(event)
                if event_dict.get('start_time'):
                    event_dict['start_time'] = event_dict['start_time'].isoformat()
                if event_dict.get('end_time'):
                    event_dict['end_time'] = event_dict['end_time'].isoformat()
                
                if event_dict.get('avg_rating'):
                    event_dict['avg_rating'] = float(event_dict['avg_rating'])

                return jsonify(event_dict), 200
    except Exception as e:
        print(f"Database error getting event: {e}")
        return jsonify({"error": "Failed to retrieve event"}), 500

@events_bp.route("/", methods=["POST"])
def create_event() -> Tuple[Response, int]:
    """
    Create an event.

    Validations:
    - Time consistency (start < end).
    - Location logic (venue vs custom).
    - Venue availability (conflict check).
    - Permissions (public events restricted to organizers/admins).
    
    Returns:
        201: { "event_id": int }
        400: Validation error.
        403: Role permission error.
        409: Venue conflict.
        500: Server error.
    """
    user_id, role, err, code = verify_token_from_request()
    if err:
        return err, code

    data: Dict[str, Any] = request.get_json() or {}
    
    title = data.get("title")
    start_str = data.get("start_time")
    end_str = data.get("end_time")
    
    # --- START VALIDATION ---
    if not title or not start_str or not end_str:
        return jsonify({"error": "title, start_time, and end_time are required"}), 400

    if len(title) > TITLE_MAX_LENGTH:
        return jsonify({"error": f"Title must be {TITLE_MAX_LENGTH} characters or less."}), 400
    # --- END VALIDATION ---

    start_dt = parse_dt(start_str)
    end_dt = parse_dt(end_str)
    
    if not start_dt or not end_dt:
        return jsonify({"error": "Invalid datetime format. Use ISO-8601."}), 400
        
    if start_dt >= end_dt:
        return jsonify({"error": "start_time must be before end_time"}), 400

    location_type = data.get("location_type", "custom")
    venue_id = data.get("venue_id")
    custom_location = data.get("custom_location_address")
    
    # --- START VALIDATION ---
    if location_type not in VALID_LOCATION_TYPES:
         return jsonify({"error": f"location_type must be one of: {', '.join(VALID_LOCATION_TYPES)}"}), 400
    
    if location_type == 'venue' and not venue_id:
        return jsonify({"error": "venue_id is required for location_type 'venue'"}), 400
    if location_type == 'custom' and not custom_location:
        return jsonify({"error": "custom_location_address is required for location_type 'custom'"}), 400
    # --- END VALIDATION ---

    description = data.get("description")
    google_maps_link = data.get("google_maps_link")
    visibility = data.get("visibility", "public")
    
    if visibility not in VALID_VISIBILITY:
        visibility = 'public'

    if visibility == 'public' and role not in ['organizer', 'admin']:
        return jsonify({
            "error": "Permission denied. Only organizers and admins can create public events."
        }), 403

    # Check for scheduling conflicts at the venue
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
def update_event(event_id: int) -> Tuple[Response, int]:
    """
    Update an event.

    Permission:
    - Admin or Organizer
    - OR the creator of the event

    Returns:
        200: Status updated.
        400: Validation error.
        403: Forbidden.
    """
    user_id, role, err, code = verify_token_from_request()
    if err:
        return err, code

    data: Dict[str, Any] = request.get_json() or {}
    if not data:
        return jsonify({"error": "No update data provided"}), 400
        
    conn = get_db()
    try:
        # --- FETCH CURRENT EVENT STATE FIRST FOR VALIDATION ---
        with conn.cursor() as cur:
            # Fetch all fields needed for validation
            cur.execute(
                """
                SELECT organizer_id, created_by, start_time, end_time, 
                       location_type, venue_id, custom_location_address, visibility
                FROM events 
                WHERE event_id = %s;
                """, 
                (event_id,)
            )
            ev = cur.fetchone()
            if not ev:
                conn.close()
                return jsonify({"error": "Event not found"}), 404

            # --- PERMISSION CHECKS ---
            if role not in ['admin', 'organizer'] and ev["created_by"] != user_id:
                conn.close()
                return jsonify({"error": "Permission denied"}), 403
            
            if 'visibility' in data and data['visibility'] == 'public':
                if role not in ['admin', 'organizer']:
                    conn.close()
                    return jsonify({"error": "Only organizers/admins can make events public"}), 403

        # --- VALIDATION BLOCK ---
        
        if "title" in data:
            title = data.get("title")
            if not title:
                return jsonify({"error": "Title cannot be empty"}), 400
            if len(title) > TITLE_MAX_LENGTH:
                return jsonify({"error": f"Title must be {TITLE_MAX_LENGTH} characters or less."}), 400

        # --- DATETIME VALIDATION ---
        start_dt = parse_dt(data.get("start_time")) if "start_time" in data else None
        end_dt = parse_dt(data.get("end_time")) if "end_time" in data else None

        if "start_time" in data and not start_dt:
            return jsonify({"error": "Invalid start_time format. Use ISO-8601."}), 400
        if "end_time" in data and not end_dt:
            return jsonify({"error": "Invalid end_time format. Use ISO-8601."}), 400

        # Check final start/end times
        final_start = start_dt or ev['start_time']
        final_end = end_dt or ev['end_time']

        if final_start >= final_end:
            return jsonify({"error": "start_time must be before end_time"}), 400
        
        # --- ENUM VALIDATIONS ---
        if "visibility" in data and data.get("visibility") not in VALID_VISIBILITY:
             return jsonify({"error": f"visibility must be one of: {', '.join(VALID_VISIBILITY)}"}), 400

        if "status" in data and data.get("status") not in VALID_STATUSES:
             return jsonify({"error": f"status must be one of: {', '.join(VALID_STATUSES)}"}), 400

        if "location_type" in data and data.get("location_type") not in VALID_LOCATION_TYPES:
             return jsonify({"error": f"location_type must be one of: {', '.join(VALID_LOCATION_TYPES)}"}), 400
             
        # --- LOCATION LOGIC VALIDATION ---
        # Determine the *final* state of the event
        final_loc_type = data.get("location_type", ev['location_type'])
        final_venue_id = data.get("venue_id", ev['venue_id'])
        final_custom_loc = data.get("custom_location_address", ev['custom_location_address'])

        # Auto-set logic
        if "venue_id" in data and "location_type" not in data:
            final_loc_type = 'venue'
        if "custom_location_address" in data and "location_type" not in data:
            final_loc_type = 'custom'

        if final_loc_type == 'venue' and not final_venue_id:
            return jsonify({"error": "venue_id is required for location_type 'venue'"}), 400
        
        if final_loc_type == 'custom' and not final_custom_loc:
            return jsonify({"error": "custom_location_address is required for location_type 'custom'"}), 400

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
        
        # Auto-update location_type if needed
        if "venue_id" in data and "location_type" not in data:
             fields.append("location_type = 'venue'")
        elif "custom_location_address" in data and "location_type" not in data:
             fields.append("location_type = 'custom'")

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
        # Specific PG error catching could go here
        if "value too long for type character varying" in str(e):
             return jsonify({"error": "A value provided was too long for the database."}), 400
        return jsonify({"error": "Failed to update event"}), 500
    finally:
        if conn:
            conn.close()

    return jsonify({"status": "updated"}), 200


@events_bp.route("/<int:event_id>", methods=["DELETE"])
def delete_event(event_id: int) -> Tuple[Response, int]:
    """
    Delete an event if the caller is the organizer, admin, or creator.
    """
    user_id, role, err, code = verify_token_from_request()
    if err:
        return err, code

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT organizer_id, created_by FROM events WHERE event_id = %s;", (event_id,))
                ev = cur.fetchone()
                if not ev:
                    return jsonify({"error": "Event not found"}), 404

                if role not in ['admin', 'organizer'] and ev["created_by"] != user_id:
                    return jsonify({"error": "Permission denied"}), 403

                cur.execute("DELETE FROM events WHERE event_id = %s;", (event_id,))
                conn.commit()
                
                if cur.rowcount == 0:
                    return jsonify({"error": "Event not found or already deleted"}), 404
                    
    except Exception as e:
        print(f"Database error deleting event {event_id}: {e}")
        return jsonify({"error": "Failed to delete event"}), 500

    return jsonify({"status": "deleted"}), 200


@events_bp.route("/<int:event_id>/rsvp", methods=["POST"])
def rsvp(event_id: int) -> Tuple[Response, int]:
    """
    RSVP to an event.
    
    Status can be 'going', 'maybe', or 'canceled' (upsert logic).
    If status is missing, it removes the RSVP.
    """
    user_id, _, err, code = verify_token_from_request()
    if err:
        return err, code

    data: Dict[str, Any] = request.get_json() or {}
    status = data.get("status")
    
    sql = ""
    params = []

    if status:
        if status not in ["going", "maybe", "canceled"]:
            return jsonify({"error": "Invalid status"}), 400
        
        # Upsert: Insert or Update
        sql = """
            INSERT INTO rsvps (user_id, event_id, rsvp_status) 
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, event_id) 
            DO UPDATE SET rsvp_status = EXCLUDED.rsvp_status;
        """
        params = (user_id, event_id, status)
    else:
        # If no status, treat as removal
        sql = "DELETE FROM rsvps WHERE user_id = %s AND event_id = %s;"
        params = (user_id, event_id)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                conn.commit()
    except Exception as e:
        print(f"Database error RSVPing: {e}")
        return jsonify({"error": "Failed to RSVP"}), 500

    return jsonify({"status": status or "cleared"}), 200


@events_bp.route("/<int:event_id>/rsvps", methods=["GET"])
def get_rsvps(event_id: int) -> Tuple[Response, int]:
    """
    Get the list of attendees for an event.
    Restricted to Organizers and Admins (or the event creator).
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
                cur.execute("SELECT organizer_id, created_by FROM events WHERE event_id = %s;", (event_id,))
                event = cur.fetchone()
                
                if not event:
                    return jsonify({"error": "Event not found"}), 404
                
                is_creator = (event["organizer_id"] == user_id) or (event["created_by"] == user_id)
                if role not in ['admin', 'organizer'] and not is_creator:
                    return jsonify({"error": "Permission denied"}), 403

                cur.execute(sql, (event_id,))
                attendees = [dict(row) for row in cur.fetchall()]
                
    except Exception as e:
        print(f"Database error getting RSVPs: {e}")
        return jsonify({"error": "Failed to retrieve attendee list"}), 500

    return jsonify(attendees), 200


@events_bp.route("/users/<int:user_id>/profile", methods=["GET"])
def get_user_profile(user_id: int) -> Tuple[Response, int]:
    """
    Get public-facing profile info for a user.
    """
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
    
# --- REVIEWS ENDPOINTS ---

@events_bp.route("/<int:event_id>/reviews", methods=["GET"])
def get_event_reviews(event_id: int) -> Tuple[Response, int]:
    """
    Get all reviews for a specific event.
    """
    
    sql = """
        SELECT 
            r.review_id, r.user_id, r.rating, r.review_text, r.created_at,
            u.first_name, u.last_name
        FROM event_reviews r
        JOIN users u ON r.user_id = u.user_id
        WHERE r.event_id = %s
        ORDER BY r.created_at DESC;
    """
    
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (event_id,))
                reviews = [dict(row) for row in cur.fetchall()]
                
                # Ensure ISO format for datetimes
                for review in reviews:
                    if review.get('created_at'):
                        review['created_at'] = review['created_at'].isoformat()
                        
                return jsonify(reviews), 200
    except Exception as e:
        print(f"Database error getting reviews: {e}")
        return jsonify({"error": "Failed to retrieve reviews"}), 500


@events_bp.route("/<int:event_id>/review", methods=["POST"])
def post_event_review(event_id: int) -> Tuple[Response, int]:
    """
    Create or update a review for an event.
    Upserts (ON CONFLICT DO UPDATE).
    """
    user_id, _, err, code = verify_token_from_request()
    if err:
        return err, code

    data: Dict[str, Any] = request.get_json() or {}
    rating = data.get("rating")
    review_text = data.get("review_text")

    if not rating or not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({"error": "A rating between 1 and 5 is required"}), 400

    sql = """
        INSERT INTO event_reviews (event_id, user_id, rating, review_text)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, event_id)
        DO UPDATE SET
            rating = EXCLUDED.rating,
            review_text = EXCLUDED.review_text,
            created_at = CURRENT_TIMESTAMP
        RETURNING *;
    """
    
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (event_id, user_id, rating, review_text))
                new_review = dict(cur.fetchone())
                conn.commit()
                
                if new_review.get('created_at'):
                    new_review['created_at'] = new_review['created_at'].isoformat()

                return jsonify(new_review), 201
    except Exception as e:
        print(f"Database error posting review: {e}")
        return jsonify({"error": "Failed to post review"}), 500