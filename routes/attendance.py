"""
routes/attendance.py - Attendance check-in and management API
"""

import logging
from flask import Blueprint, jsonify, request
from database.db import query_db
from services import attendance_service as svc

attendance_bp = Blueprint("attendance", __name__, url_prefix="/api/attendance")
logger = logging.getLogger(__name__)


@attendance_bp.route("/session/<int:session_id>", methods=["GET"])
def get_session_attendance(session_id):
    records = svc.get_all_attendance(session_id)
    summary = svc.get_session_summary(session_id)
    return jsonify({"records": records, "summary": summary})


@attendance_bp.route("/checkin", methods=["POST"])
def check_in():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    student_db_id = data.get("student_db_id")
    source = data.get("source", "manual")
    check_in_time = data.get("check_in_time")
    notes = data.get("notes", "")

    if not session_id or not student_db_id:
        return jsonify({"error": "session_id and student_db_id are required."}), 400

    try:
        result = svc.check_in(
            int(session_id), int(student_db_id), source, check_in_time, notes
        )
        return jsonify(result), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 409
    except Exception as e:
        logger.exception("Check-in error")
        return jsonify({"error": str(e)}), 500


@attendance_bp.route("/absent", methods=["POST"])
def mark_absent():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    student_db_id = data.get("student_db_id")
    if not session_id or not student_db_id:
        return jsonify({"error": "session_id and student_db_id are required."}), 400

    result = svc.mark_absent(int(session_id), int(student_db_id))
    return jsonify(result)


@attendance_bp.route("/correct/<int:record_id>", methods=["PATCH"])
def correct_attendance(record_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "").strip()
    corrected_by = data.get("corrected_by", "educator")
    notes = data.get("notes", "")

    try:
        result = svc.correct_attendance(record_id, new_status, corrected_by, notes)
        return jsonify(result)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.exception("Correction error")
        return jsonify({"error": str(e)}), 500


@attendance_bp.route("/summary/session/<int:session_id>", methods=["GET"])
def session_summary(session_id):
    return jsonify(svc.get_session_summary(session_id))


@attendance_bp.route("/summary/student/<int:student_db_id>", methods=["GET"])
def student_summary(student_db_id):
    return jsonify(svc.get_student_attendance_summary(student_db_id))


@attendance_bp.route("/checkin/qr", methods=["POST"])
def qr_checkin():
    """QR-based check-in: looks up student by student_id string."""
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    student_code = (data.get("student_code") or "").strip()

    if not session_id or not student_code:
        return jsonify({"error": "session_id and student_code are required."}), 400

    row = query_db(
        "SELECT id, name FROM students WHERE student_id=? AND is_active=1",
        (student_code,), one=True
    )
    if not row:
        return jsonify({"error": f"Student '{student_code}' not found."}), 404

    try:
        result = svc.check_in(int(session_id), row["id"], source="qr")
        result["student_name"] = row["name"]
        return jsonify(result)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 409
    except Exception as e:
        logger.exception("QR check-in error")
        return jsonify({"error": str(e)}), 500


@attendance_bp.route("/bulk-init", methods=["POST"])
def bulk_init():
    """Pre-populate attendance records for all students in a session."""
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    student_ids = data.get("student_ids", [])

    if not session_id:
        return jsonify({"error": "session_id is required."}), 400

    if not student_ids:
        # Use all active students
        rows = query_db("SELECT id FROM students WHERE is_active=1")
        student_ids = [r["id"] for r in rows]

    from services.attendance_service import bulk_initialize_attendance
    count = bulk_initialize_attendance(int(session_id), student_ids)
    return jsonify({"initialized": count})
