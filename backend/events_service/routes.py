"""
Events service routes: create, read, update, delete events, and RSVP.
Assumes token auth (same JWT secret) and user id is the subject.
"""

from flask import Blueprint, request, jsonify
from backend.database.db_connection import get_db
import os
import jwt
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET", "change_me")

events_bp = Blueprint("events", __name__)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except Exception:
        return None

def parse_dt(val):
    # expects ISO-8601 or "YYYY-MM-DD HH:MM:SS"
    try:
        return datetime.fromisoformat(val)
    except Exception:
        return None

@events_bp.route("/", methods=["GET"])
def list_events():
    """
    Return all events (simple list).
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM events ORDER BY start_time")
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return jsonify(rows), 200

@events_bp.route("/", methods=["POST"])
def create_event():
    """
    Create an event.
    Header: Authorization: Bearer <token>
    Body JSON: title, description, start_time, end_time, location
    start_time/end_time should be ISO strings.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing token"}), 401
    user_id = verify_token(auth.split(" ",1)[1])
    if not user_id:
        return jsonify({"error": "invalid token"}), 401

    data = request.get_json() or {}
    title = data.get("title") or ""
    start = data.get("start_time")
    end = data.get("end_time")
    if not title or not start or not end:
        return jsonify({"error": "title, start_time, end_time required"}), 400

    start_dt = parse_dt(start)
    end_dt = parse_dt(end)
    if not start_dt or not end_dt or start_dt >= end_dt:
        return jsonify({"error": "invalid start/end times"}), 400

    # simple conflict check: same location overlapping
    location = data.get("location")
    conn = get_db()
    try:
        cur = conn.cursor()
        if location:
            cur.execute("""
                SELECT id FROM events
                WHERE location = ?
                AND NOT (end_time <= ? OR start_time >= ?)
            """, (location, start, end))
            conflict = cur.fetchone()
            if conflict:
                return jsonify({"warning": "scheduling conflict detected"}), 409

        cur.execute(
            "INSERT INTO events (title, description, start_time, end_time, location, organizer_id) VALUES (?, ?, ?, ?, ?, ?)",
            (title, data.get("description"), start, end, location, user_id)
        )
        conn.commit()
        event_id = cur.lastrowid
    finally:
        conn.close()

    return jsonify({"id": event_id}), 201

@events_bp.route("/<int:event_id>", methods=["PUT"])
def update_event(event_id):
    """
    Update an event if the caller is the organizer.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing token"}), 401
    user_id = verify_token(auth.split(" ",1)[1])
    if not user_id:
        return jsonify({"error": "invalid token"}), 401

    data = request.get_json() or {}
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT organizer_id FROM events WHERE id = ?", (event_id,))
        ev = cur.fetchone()
        if not ev:
            return jsonify({"error": "not found"}), 404
        if ev["organizer_id"] != user_id:
            return jsonify({"error": "forbidden"}), 403

        # allow partial updates
        fields = []
        values = []
        for key in ("title", "description", "start_time", "end_time", "location"):
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(event_id)
            cur.execute(f"UPDATE events SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()
    finally:
        conn.close()

    return jsonify({"status": "updated"}), 200

@events_bp.route("/<int:event_id>", methods=["DELETE"])
def delete_event(event_id):
    """
    Delete an event if the caller is the organizer.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing token"}), 401
    user_id = verify_token(auth.split(" ",1)[1])
    if not user_id:
        return jsonify({"error": "invalid token"}), 401

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT organizer_id FROM events WHERE id = ?", (event_id,))
        ev = cur.fetchone()
        if not ev:
            return jsonify({"error": "not found"}), 404
        if ev["organizer_id"] != user_id:
            return jsonify({"error": "forbidden"}), 403

        cur.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
    finally:
        conn.close()

    return jsonify({"status": "deleted"}), 200

@events_bp.route("/<int:event_id>/rsvp", methods=["POST"])
def rsvp(event_id):
    """
    RSVP to an event.
    Header: Authorization: Bearer <token>
    Body: { "status": "going"|"canceled"|"maybe" }  (optional; default 'going')
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing token"}), 401
    user_id = verify_token(auth.split(" ",1)[1])
    if not user_id:
        return jsonify({"error": "invalid token"}), 401

    status = (request.get_json() or {}).get("status", "going")
    conn = get_db()
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO rsvps (user_id, event_id, status) VALUES (?, ?, ?)",
                (user_id, event_id, status)
            )
        except Exception:
            # update if exists
            cur.execute(
                "UPDATE rsvps SET status = ? WHERE user_id = ? AND event_id = ?",
                (status, user_id, event_id)
            )
        conn.commit()
    finally:
        conn.close()

    return jsonify({"status": status}), 200
