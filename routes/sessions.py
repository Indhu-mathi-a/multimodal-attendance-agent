"""
routes/sessions.py - Classroom session management API
"""

import logging
from flask import Blueprint, jsonify, request
from database.db import query_db, execute_db
from services.attendance_service import bulk_initialize_attendance

sessions_bp = Blueprint("sessions", __name__, url_prefix="/api/sessions")
logger = logging.getLogger(__name__)


def _validate_session(data: dict) -> tuple[dict, list]:
    errors = []
    cleaned = {}

    cleaned["session_name"] = (data.get("session_name") or "").strip()
    if not cleaned["session_name"]:
        errors.append("session_name is required.")

    cleaned["subject"] = (data.get("subject") or "").strip()
    if not cleaned["subject"]:
        errors.append("subject is required.")

    cleaned["department"] = (data.get("department") or "").strip()
    cleaned["session_date"] = (data.get("session_date") or "").strip()
    if not cleaned["session_date"]:
        errors.append("session_date is required.")

    cleaned["start_time"] = (data.get("start_time") or "").strip()
    cleaned["end_time"] = (data.get("end_time") or "").strip()
    if not cleaned["start_time"] or not cleaned["end_time"]:
        errors.append("start_time and end_time are required.")

    cleaned["notes"] = (data.get("notes") or "").strip()
    return cleaned, errors


@sessions_bp.route("", methods=["GET"])
def list_sessions():
    status_filter = request.args.get("status", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    params = []
    wheres = []
    if status_filter:
        wheres.append("status = ?")
        params.append(status_filter)
    if date_from:
        wheres.append("session_date >= ?")
        params.append(date_from)
    if date_to:
        wheres.append("session_date <= ?")
        params.append(date_to)

    where_str = "WHERE " + " AND ".join(wheres) if wheres else ""
    rows = query_db(
        f"SELECT * FROM classroom_sessions {where_str} ORDER BY session_date DESC, start_time DESC",
        params
    )
    return jsonify([dict(r) for r in rows])


@sessions_bp.route("/<int:session_id>", methods=["GET"])
def get_session(session_id):
    row = query_db(
        "SELECT * FROM classroom_sessions WHERE id=?", (session_id,), one=True
    )
    if not row:
        return jsonify({"error": "Session not found."}), 404
    return jsonify(dict(row))


@sessions_bp.route("", methods=["POST"])
def create_session():
    data = request.get_json(silent=True) or {}
    cleaned, errors = _validate_session(data)
    if errors:
        return jsonify({"error": errors}), 400

    student_ids = data.get("student_ids", [])   # List of student DB IDs

    try:
        new_id = execute_db(
            """INSERT INTO classroom_sessions
               (session_name, subject, department, session_date, start_time, end_time, notes)
               VALUES(?,?,?,?,?,?,?)""",
            (cleaned["session_name"], cleaned["subject"], cleaned["department"],
             cleaned["session_date"], cleaned["start_time"], cleaned["end_time"],
             cleaned["notes"])
        )

        # Pre-populate attendance as absent for enrolled students
        if student_ids:
            bulk_initialize_attendance(new_id, student_ids)

        row = query_db("SELECT * FROM classroom_sessions WHERE id=?", (new_id,), one=True)
        return jsonify(dict(row)), 201
    except Exception as e:
        logger.exception("Create session error")
        return jsonify({"error": str(e)}), 500


@sessions_bp.route("/<int:session_id>", methods=["PUT"])
def update_session(session_id):
    row = query_db("SELECT id FROM classroom_sessions WHERE id=?", (session_id,), one=True)
    if not row:
        return jsonify({"error": "Session not found."}), 404

    data = request.get_json(silent=True) or {}
    cleaned, errors = _validate_session(data)
    if errors:
        return jsonify({"error": errors}), 400

    try:
        execute_db(
            """UPDATE classroom_sessions
               SET session_name=?, subject=?, department=?, session_date=?,
                   start_time=?, end_time=?, notes=?, updated_at=datetime('now')
               WHERE id=?""",
            (cleaned["session_name"], cleaned["subject"], cleaned["department"],
             cleaned["session_date"], cleaned["start_time"], cleaned["end_time"],
             cleaned["notes"], session_id)
        )
        updated = query_db(
            "SELECT * FROM classroom_sessions WHERE id=?", (session_id,), one=True
        )
        return jsonify(dict(updated))
    except Exception as e:
        logger.exception("Update session error")
        return jsonify({"error": str(e)}), 500


@sessions_bp.route("/<int:session_id>/status", methods=["PATCH"])
def update_session_status(session_id):
    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or "").strip()
    valid = {"scheduled", "active", "completed", "cancelled"}
    if new_status not in valid:
        return jsonify({"error": f"status must be one of {valid}"}), 400

    row = query_db("SELECT id FROM classroom_sessions WHERE id=?", (session_id,), one=True)
    if not row:
        return jsonify({"error": "Session not found."}), 404

    execute_db(
        "UPDATE classroom_sessions SET status=?, updated_at=datetime('now') WHERE id=?",
        (new_status, session_id)
    )
    return jsonify({"session_id": session_id, "status": new_status})


@sessions_bp.route("/<int:session_id>", methods=["DELETE"])
def delete_session(session_id):
    row = query_db("SELECT id FROM classroom_sessions WHERE id=?", (session_id,), one=True)
    if not row:
        return jsonify({"error": "Session not found."}), 404

    execute_db("DELETE FROM classroom_sessions WHERE id=?", (session_id,))
    return jsonify({"message": "Session and all related records deleted."})


@sessions_bp.route("/<int:session_id>/students", methods=["GET"])
def get_session_students(session_id):
    """List students enrolled (i.e., having attendance records) in a session."""
    rows = query_db(
        """SELECT s.id, s.student_id, s.name, s.department,
                  ar.status, ar.check_in_time, ar.source, ar.id AS record_id
           FROM attendance_records ar
           JOIN students s ON s.id = ar.student_id
           WHERE ar.session_id = ?
           ORDER BY s.name""",
        (session_id,)
    )
    return jsonify([dict(r) for r in rows])
