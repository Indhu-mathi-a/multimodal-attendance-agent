"""
routes/engagement.py - Engagement analytics and participation event API
"""

import logging
from flask import Blueprint, jsonify, request
from database.db import query_db
from services import engagement_service as svc
from services import recommendation_service as rec_svc

engagement_bp = Blueprint("engagement", __name__, url_prefix="/api/engagement")
logger = logging.getLogger(__name__)


@engagement_bp.route("/score/<int:session_id>", methods=["GET"])
def get_score(session_id):
    """Compute and return the Activity & Participation Indicator for a session."""
    score_data = svc.compute_session_score(session_id)
    return jsonify(score_data)


@engagement_bp.route("/trend", methods=["GET"])
def get_trend():
    """Return composite scores for a list of sessions for trend charts."""
    ids_param = request.args.get("session_ids", "")
    try:
        session_ids = [int(x) for x in ids_param.split(",") if x.strip()]
    except ValueError:
        return jsonify({"error": "session_ids must be comma-separated integers."}), 400

    if not session_ids:
        # Default: last 10 completed sessions
        rows = query_db(
            "SELECT id FROM classroom_sessions WHERE status='completed' "
            "ORDER BY session_date DESC LIMIT 10"
        )
        session_ids = [r["id"] for r in rows]

    trend = svc.get_multi_session_trend(session_ids)
    return jsonify(trend)


@engagement_bp.route("/participation", methods=["POST"])
def log_participation():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    student_id = data.get("student_id")
    event_type = (data.get("event_type") or "other").strip()
    notes = data.get("notes", "")

    if not session_id:
        return jsonify({"error": "session_id is required."}), 400

    try:
        rid = svc.log_participation_event(
            int(session_id), int(student_id) if student_id else None,
            event_type, notes
        )
        return jsonify({"id": rid, "event_type": event_type}), 201
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.exception("Participation log error")
        return jsonify({"error": str(e)}), 500


@engagement_bp.route("/participation/<int:session_id>", methods=["GET"])
def get_participation(session_id):
    rows = query_db(
        """SELECT pe.id, pe.event_type, pe.event_time, pe.notes,
                  s.name AS student_name, s.student_id AS student_code
           FROM participation_events pe
           LEFT JOIN students s ON s.id = pe.student_id
           WHERE pe.session_id = ?
           ORDER BY pe.event_time DESC""",
        (session_id,)
    )
    return jsonify([dict(r) for r in rows])


@engagement_bp.route("/recommendations/<int:session_id>", methods=["GET"])
def get_recommendations(session_id):
    """Retrieve saved recommendations, optionally regenerate them."""
    refresh = request.args.get("refresh", "false").lower() == "true"

    if refresh:
        score_data = svc.compute_session_score(session_id)
        session_info = query_db(
            "SELECT start_time, end_time FROM classroom_sessions WHERE id=?",
            (session_id,), one=True
        )
        duration_min = 0
        if session_info and session_info["start_time"] and session_info["end_time"]:
            try:
                from datetime import datetime
                s = datetime.strptime(session_info["start_time"], "%H:%M")
                e = datetime.strptime(session_info["end_time"], "%H:%M")
                duration_min = int((e - s).total_seconds() // 60)
            except Exception:
                pass
        recs = rec_svc.generate_recommendations(session_id, score_data, duration_min)
    else:
        recs = rec_svc.get_recommendations(session_id)

    return jsonify(recs)


@engagement_bp.route("/recommendations/dismiss/<int:rec_id>", methods=["PATCH"])
def dismiss_recommendation(rec_id):
    rec_svc.dismiss_recommendation(rec_id)
    return jsonify({"message": "Recommendation dismissed."})
