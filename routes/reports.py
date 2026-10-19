"""
routes/reports.py - Report generation and export API
"""

import logging
from flask import Blueprint, jsonify, make_response, request
from services import report_service as rpt

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")
logger = logging.getLogger(__name__)


@reports_bp.route("/attendance/csv", methods=["GET"])
def attendance_csv():
    session_id = request.args.get("session_id", type=int)
    date_from = request.args.get("date_from", "").strip() or None
    date_to = request.args.get("date_to", "").strip() or None

    csv_data = rpt.attendance_csv(session_id, date_from, date_to)
    resp = make_response(csv_data)
    resp.headers["Content-Type"] = "text/csv"
    resp.headers["Content-Disposition"] = "attachment; filename=attendance_report.csv"
    return resp


@reports_bp.route("/students/csv", methods=["GET"])
def students_summary_csv():
    date_from = request.args.get("date_from", "").strip() or None
    date_to = request.args.get("date_to", "").strip() or None

    csv_data = rpt.student_summary_csv(date_from, date_to)
    resp = make_response(csv_data)
    resp.headers["Content-Type"] = "text/csv"
    resp.headers["Content-Disposition"] = "attachment; filename=student_summary.csv"
    return resp


@reports_bp.route("/activity/csv", methods=["GET"])
def activity_csv():
    session_id = request.args.get("session_id", type=int)
    csv_data = rpt.activity_csv(session_id)
    resp = make_response(csv_data)
    resp.headers["Content-Type"] = "text/csv"
    resp.headers["Content-Disposition"] = "attachment; filename=activity_report.csv"
    return resp


@reports_bp.route("/recommendations/csv", methods=["GET"])
def recommendations_csv():
    session_id = request.args.get("session_id", type=int)
    csv_data = rpt.recommendations_csv(session_id)
    resp = make_response(csv_data)
    resp.headers["Content-Type"] = "text/csv"
    resp.headers["Content-Disposition"] = "attachment; filename=recommendations.csv"
    return resp


@reports_bp.route("/attendance/html/<int:session_id>", methods=["GET"])
def attendance_html(session_id):
    html = rpt.attendance_html_report(session_id)
    return make_response(html, 200, {"Content-Type": "text/html"})


@reports_bp.route("/dashboard/stats", methods=["GET"])
def dashboard_stats():
    """Aggregate stats for the dashboard."""
    from database.db import query_db

    total_students = query_db(
        "SELECT COUNT(*) AS c FROM students WHERE is_active=1", one=True
    )["c"]
    total_sessions = query_db(
        "SELECT COUNT(*) AS c FROM classroom_sessions", one=True
    )["c"]
    recent_sessions = query_db(
        """SELECT id, session_name, subject, session_date, start_time, end_time, status
           FROM classroom_sessions
           ORDER BY session_date DESC, start_time DESC LIMIT 5"""
    )
    total_present = query_db(
        "SELECT COUNT(*) AS c FROM attendance_records WHERE status IN ('present','late')",
        one=True
    )["c"]
    total_absent = query_db(
        "SELECT COUNT(*) AS c FROM attendance_records WHERE status='absent'",
        one=True
    )["c"]
    total_records = total_present + total_absent
    avg_pct = round(total_present / total_records * 100, 1) if total_records else 0

    avg_score = query_db(
        "SELECT AVG(movement_score) AS avg FROM activity_summaries WHERE processing_status='done'",
        one=True
    )["avg"]

    # Weekly attendance data (last 7 days)
    weekly = query_db(
        """SELECT cs.session_date,
                  SUM(CASE WHEN ar.status IN ('present','late') THEN 1 ELSE 0 END) AS present,
                  SUM(CASE WHEN ar.status = 'absent' THEN 1 ELSE 0 END) AS absent
           FROM classroom_sessions cs
           LEFT JOIN attendance_records ar ON ar.session_id = cs.id
           WHERE cs.session_date >= date('now', '-7 days')
           GROUP BY cs.session_date
           ORDER BY cs.session_date"""
    )

    return jsonify({
        "total_students": total_students,
        "total_sessions": total_sessions,
        "total_present": total_present,
        "total_absent": total_absent,
        "attendance_pct": avg_pct,
        "avg_activity_score": round(float(avg_score), 1) if avg_score else None,
        "recent_sessions": [dict(r) for r in recent_sessions],
        "weekly_data": [dict(r) for r in weekly],
    })
