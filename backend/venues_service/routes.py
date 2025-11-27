"""
Venues service route handlers.
Manages on-campus locations.
"""

from flask import Blueprint, request, jsonify
from backend.database.db_connection import get_db
from backend.auth_service.utils import verify_token_from_request

venues_bp = Blueprint("venues", __name__)

@venues_bp.route("/", methods=["GET"])
def list_venues():
    """
    Get all venues. Public access allowed (anyone can see venues).
    """
    sql = "SELECT * FROM venues ORDER BY name;"
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                venues = [dict(row) for row in cur.fetchall()]
                return jsonify(venues), 200
    except Exception as e:
        print(f"Error listing venues: {e}")
        return jsonify({"error": "Failed to list venues"}), 500


@venues_bp.route("/", methods=["POST"])
def create_venue():
    """
    Admin-only: Create a new venue.
    """
    _, _, err, code = verify_token_from_request(required_roles=["admin"])
    if err:
        return err, code

    data = request.get_json() or {}
    name = data.get("name")
    building = data.get("building")
    
    if not name or not building:
        return jsonify({"error": "Name and Building are required"}), 400

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
                    building, 
                    data.get("room_number"), 
                    data.get("google_maps_link")
                ))
                venue = cur.fetchone()
                conn.commit()
                return jsonify(venue), 201
    except Exception as e:
        print(f"Error creating venue: {e}")
        return jsonify({"error": "Failed to create venue"}), 500


@venues_bp.route("/<int:venue_id>", methods=["PUT"])
def update_venue(venue_id):
    """
    Admin-only: Update a venue.
    """
    _, _, err, code = verify_token_from_request(required_roles=["admin"])
    if err:
        return err, code

    data = request.get_json() or {}
    
    # Simple dynamic update query builder
    allowed_fields = ["name", "building", "room_number", "google_maps_link"]
    fields = []
    values = []
    
    for key in allowed_fields:
        if key in data:
            fields.append(f"{key} = %s")
            values.append(data[key])
            
    if not fields:
        return jsonify({"error": "No valid fields to update"}), 400
        
    values.append(venue_id)
    sql = f"UPDATE venues SET {', '.join(fields)} WHERE venue_id = %s RETURNING *;"

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, values)
                updated = cur.fetchone()
                if not updated:
                    return jsonify({"error": "Venue not found"}), 404
                conn.commit()
                return jsonify(dict(updated)), 200
    except Exception as e:
        print(f"Error updating venue: {e}")
        return jsonify({"error": "Failed to update venue"}), 500


@venues_bp.route("/<int:venue_id>", methods=["DELETE"])
def delete_venue(venue_id):
    """
    Admin-only: Delete a venue.
    """
    _, _, err, code = verify_token_from_request(required_roles=["admin"])
    if err:
        return err, code

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Check for usage (optional, but good practice)
                # For now, relying on DB constraints (ON DELETE SET NULL in events table)
                cur.execute("DELETE FROM venues WHERE venue_id = %s;", (venue_id,))
                if cur.rowcount == 0:
                     return jsonify({"error": "Venue not found"}), 404
                conn.commit()
                return jsonify({"status": "deleted"}), 200
    except Exception as e:
        print(f"Error deleting venue: {e}")
        return jsonify({"error": "Failed to delete venue"}), 500