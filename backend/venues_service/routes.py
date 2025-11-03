"""
Venues service routes: create and list venues.
Venues can be created by organizers/admins and listed by anyone.
"""

from flask import Blueprint, request, jsonify
from backend.database.db_connection import get_db
from backend.auth_service.utils import verify_token_from_request
from dotenv import load_dotenv

load_dotenv()

venues_bp = Blueprint("venues", __name__)

@venues_bp.route("/", methods=["GET"])
def list_venues():
    """
    Return all venues (simple list).
    This is a public endpoint, as all users need to see venue options.
    """
    sql = "SELECT venue_id, name, building, room_number, google_maps_link FROM venues ORDER BY name;"
    
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"Database error listing venues: {e}")
        return jsonify({"error": "Failed to retrieve venues"}), 500
        
    return jsonify(rows), 200

@venues_bp.route("/", methods=["POST"])
def create_venue():
    """
    Create a new venue.
    Only organizers and admins can create new venues.
    Body JSON: { 
        "name": "...", 
        "building": "..." (optional), 
        "room_number": "..." (optional), 
        "google_maps_link": "..." (optional)
    }
    """
    user_id, role, err, code = verify_token_from_request(required_roles=["organizer", "admin"])
    if err:
        return err, code

    data = request.get_json() or {}
    name = data.get("name")
    
    if not name:
        return jsonify({"error": "Venue 'name' is required"}), 400

    sql = """
        INSERT INTO venues (name, building, room_number, google_maps_link)
        VALUES (%s, %s, %s, %s)
        RETURNING venue_id;
    """
    
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    name,
                    data.get("building"),
                    data.get("room_number"),
                    data.get("google_maps_link")
                ))
                new_venue = cur.fetchone()
                conn.commit()
                venue_id = new_venue["venue_id"]
    except Exception as e:
        print(f"Database error creating venue: {e}")
        return jsonify({"error": "Failed to create venue"}), 500

    return jsonify({"venue_id": venue_id, "name": name}), 201

