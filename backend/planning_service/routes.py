"""
Planning service routes: Manage tasks, Kanban board, and planning calendar.
Supports organizers in managing event logistics.
"""

import datetime
from typing import Tuple, Dict, Any, Optional

from flask import Blueprint, request, jsonify, Response
from backend.database.db_connection import get_db
from backend.auth_service.utils import verify_token_from_request

planning_bp = Blueprint("planning", __name__)

def parse_dt(val: Optional[str]) -> Optional[datetime.datetime]:
    """
    Helper to parse ISO datetime strings.
    """
    if not val: return None
    try:
        if val.endswith('Z'): val = val[:-1] + '+00:00'
        return datetime.datetime.fromisoformat(val)
    except Exception: return None

@planning_bp.route("/tasks", methods=["GET"])
def list_tasks() -> Tuple[Response, int]:
    """
    Get all tasks ordered by position.
    
    Filters:
    - ?event_id=<id> : Filter by specific event.
    - ?event_id=global : Filter for tasks not linked to any event.
    
    Permissions:
    - Admin or Organizer only.
    
    Returns:
        200: List of task objects with assignee and event details.
        403: Forbidden.
        500: Database error.
    """
    user_id, role, err, code = verify_token_from_request()
    if err: return err, code

    if role not in ['admin', 'organizer']:
        return jsonify({"error": "Permission denied"}), 403

    event_filter = request.args.get('event_id')
    
    sql = """
        SELECT 
            t.task_id, t.event_id, t.title, t.description, 
            t.status, t.priority, t.due_date, t.assigned_to, t.position,
            u.first_name as assignee_name, u.last_name as assignee_last, u.email as assignee_email,
            e.title as event_title
        FROM planning_tasks t
        LEFT JOIN users u ON t.assigned_to = u.user_id
        LEFT JOIN events e ON t.event_id = e.event_id
    """
    
    params = []
    conditions = []

    if event_filter:
        if event_filter == 'global':
            conditions.append("t.event_id IS NULL")
        else:
            conditions.append("t.event_id = %s")
            params.append(event_filter)
    
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    
    # Order by position ascending
    sql += " ORDER BY t.position ASC, t.created_at DESC;"

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                tasks = [dict(row) for row in cur.fetchall()]
                
                for t in tasks:
                    if t['due_date']:
                        t['due_date'] = t['due_date'].isoformat()
                        
        return jsonify(tasks), 200
    except Exception as e:
        print(f"Error listing tasks: {e}")
        return jsonify({"error": "Failed to fetch tasks"}), 500

@planning_bp.route("/tasks", methods=["POST"])
def create_task() -> Tuple[Response, int]:
    """
    Create a new planning task.
    
    Auto-assigns a position at the bottom of the list (max(pos) + 1000).
    
    Returns:
        201: { "task_id": int, "status": "created" }
        400: Validation error.
        403: Forbidden.
    """
    user_id, role, err, code = verify_token_from_request()
    if err: return err, code

    if role not in ['admin', 'organizer']:
        return jsonify({"error": "Permission denied"}), 403

    data: Dict[str, Any] = request.get_json() or {}
    
    if not data.get('title'):
        return jsonify({"error": "Title is required"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Get current max position to append to bottom
                cur.execute("SELECT COALESCE(MAX(position), 0) FROM planning_tasks")
                result = cur.fetchone()
                max_pos = result[0] if result else 0
                new_pos = max_pos + 1000.0

                sql = """
                    INSERT INTO planning_tasks 
                    (event_id, title, description, status, priority, due_date, assigned_to, created_by, position)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING task_id;
                """
                cur.execute(sql, (
                    data.get('event_id'),
                    data['title'],
                    data.get('description'),
                    data.get('status', 'todo'),
                    data.get('priority', 'medium'),
                    parse_dt(data.get('due_date')),
                    data.get('assigned_to'),
                    user_id,
                    new_pos
                ))
                conn.commit()
                new_id = cur.fetchone()['task_id']
                
        return jsonify({"task_id": new_id, "status": "created"}), 201
    except Exception as e:
        print(f"Error creating task: {e}")
        return jsonify({"error": "Failed to create task"}), 500

@planning_bp.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id: int) -> Tuple[Response, int]:
    """
    Update an existing task.
    
    Allowed fields:
        title, description, status, priority, due_date, 
        assigned_to, event_id, position
    
    Returns:
        200: Success status.
        400: No valid fields.
        403: Forbidden.
    """
    user_id, role, err, code = verify_token_from_request()
    if err: return err, code

    if role not in ['admin', 'organizer']:
        return jsonify({"error": "Permission denied"}), 403

    data: Dict[str, Any] = request.get_json() or {}
    
    fields = []
    values = []
    allowed = ['title', 'description', 'status', 'priority', 'due_date', 'assigned_to', 'event_id', 'position']

    for key in allowed:
        if key in data:
            fields.append(f"{key} = %s")
            if key == 'due_date':
                values.append(parse_dt(data[key]))
            else:
                values.append(data[key])
    
    if not fields:
        return jsonify({"error": "No valid fields to update"}), 400
        
    values.append(task_id)
    
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                sql = f"UPDATE planning_tasks SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE task_id = %s"
                cur.execute(sql, values)
                conn.commit()
        return jsonify({"status": "updated"}), 200
    except Exception as e:
        print(f"Error updating task: {e}")
        return jsonify({"error": "Failed to update task"}), 500

@planning_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id: int) -> Tuple[Response, int]:
    """
    Delete a task.
    
    Returns:
        200: Success status.
        403: Forbidden.
    """
    user_id, role, err, code = verify_token_from_request()
    if err: return err, code

    if role not in ['admin', 'organizer']:
        return jsonify({"error": "Permission denied"}), 403

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM planning_tasks WHERE task_id = %s", (task_id,))
                conn.commit()
        return jsonify({"status": "deleted"}), 200
    except Exception as e:
        print(f"Error deleting task: {e}")
        return jsonify({"error": "Failed to delete task"}), 500