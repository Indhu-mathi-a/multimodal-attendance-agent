"""
services/report_service.py
Generates CSV and printable HTML reports for attendance, activity, and recommendations.
"""

import csv
import io
import json
import logging
from datetime import datetime
from pathlib import Path

from database.db import query_db

logger = logging.getLogger(__name__)


# ─── CSV Generators ────────────────────────────────────────────────────────────

def attendance_csv(session_id: int = None, date_from: str = None,
                   date_to: str = None) -> str:
    """Generate CSV string for attendance records."""
    params = []
    where_clauses = []

    if session_id:
        where_clauses.append("ar.session_id = ?")
        params.append(session_id)
    if date_from:
        where_clauses.append("cs.session_date >= ?")
        params.append(date_from)
    if date_to:
        where_clauses.append("cs.session_date <= ?")
        params.append(date_to)

    where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    rows = query_db(
        f"""SELECT s.student_id, s.name, s.department,
                   cs.session_name, cs.subject, cs.session_date,
                   cs.start_time, cs.end_time,
                   ar.status, ar.check_in_time, ar.source, ar.corrected_by
            FROM attendance_records ar
            JOIN students s  ON s.id  = ar.student_id
            JOIN classroom_sessions cs ON cs.id = ar.session_id
            {where}
            ORDER BY cs.session_date DESC, s.name""",
        params,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Student ID", "Name", "Department",
        "Session", "Subject", "Date",
        "Start", "End",
        "Status", "Check-in Time", "Source", "Corrected By",
    ])
    for r in rows:
        writer.writerow(list(r))

    return output.getvalue()


def student_summary_csv(date_from: str = None, date_to: str = None) -> str:
    """Generate per-student attendance summary CSV."""
    params = []
    where = ""
    if date_from:
        where += " AND cs.session_date >= ?"
        params.append(date_from)
    if date_to:
        where += " AND cs.session_date <= ?"
        params.append(date_to)

    rows = query_db(
        f"""SELECT s.student_id, s.name, s.department,
                   COUNT(*)                                             AS total,
                   SUM(CASE WHEN ar.status IN ('present','late') THEN 1 ELSE 0 END) AS attended,
                   SUM(CASE WHEN ar.status = 'absent' THEN 1 ELSE 0 END)            AS absent,
                   ROUND(
                       SUM(CASE WHEN ar.status IN ('present','late') THEN 1 ELSE 0 END)
                       * 100.0 / COUNT(*), 1
                   )                                                   AS pct
            FROM students s
            LEFT JOIN attendance_records ar ON ar.student_id = s.id
            LEFT JOIN classroom_sessions  cs ON cs.id = ar.session_id
            WHERE s.is_active = 1 {where}
            GROUP BY s.id
            ORDER BY s.name""",
        params,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Student ID", "Name", "Department",
        "Total Sessions", "Attended", "Absent", "Attendance %",
    ])
    for r in rows:
        writer.writerow(list(r))

    return output.getvalue()


def activity_csv(session_id: int = None) -> str:
    """Generate CSV for activity summaries."""
    params = []
    where = ""
    if session_id:
        where = "WHERE a.session_id = ?"
        params.append(session_id)

    rows = query_db(
        f"""SELECT cs.session_name, cs.subject, cs.session_date,
                   a.analysis_type, a.person_count_avg,
                   a.movement_score, a.audio_activity_pct,
                   a.active_periods, a.quiet_periods,
                   a.processing_status, a.processed_at
            FROM activity_summaries a
            JOIN classroom_sessions cs ON cs.id = a.session_id
            {where}
            ORDER BY cs.session_date DESC""",
        params,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Session", "Subject", "Date", "Analysis Type",
        "Avg Person Count", "Movement Score", "Audio Activity %",
        "Active Periods", "Quiet Periods", "Status", "Processed At",
    ])
    for r in rows:
        writer.writerow(list(r))

    return output.getvalue()


def recommendations_csv(session_id: int = None) -> str:
    """Generate CSV for teaching recommendations."""
    params = []
    where = ""
    if session_id:
        where = "WHERE tr.session_id = ?"
        params.append(session_id)

    rows = query_db(
        f"""SELECT cs.session_name, cs.session_date,
                   tr.category, tr.recommendation, tr.reason,
                   tr.priority, tr.created_at
            FROM teaching_recommendations tr
            JOIN classroom_sessions cs ON cs.id = tr.session_id
            {where}
            ORDER BY cs.session_date DESC, tr.priority""",
        params,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Session", "Date", "Category",
        "Recommendation", "Reason", "Priority", "Generated At",
    ])
    for r in rows:
        writer.writerow(list(r))

    return output.getvalue()


# ─── HTML Report ───────────────────────────────────────────────────────────────

def attendance_html_report(session_id: int) -> str:
    """Generate a printable HTML attendance report for one session."""
    session = query_db(
        "SELECT * FROM classroom_sessions WHERE id=?", (session_id,), one=True
    )
    if not session:
        return "<p>Session not found.</p>"

    rows = query_db(
        """SELECT s.student_id, s.name, s.department,
                  ar.status, ar.check_in_time, ar.source
           FROM attendance_records ar
           JOIN students s ON s.id = ar.student_id
           WHERE ar.session_id=?
           ORDER BY s.name""",
        (session_id,)
    )

    total = len(rows)
    present = sum(1 for r in rows if r["status"] in ("present", "late"))
    pct = round(present / total * 100, 1) if total else 0

    rows_html = ""
    for i, r in enumerate(rows, 1):
        badge = {
            "present": "success", "late": "warning", "absent": "danger"
        }.get(r["status"], "secondary")
        rows_html += f"""<tr>
          <td>{i}</td><td>{r['student_id']}</td><td>{r['name']}</td>
          <td>{r['department']}</td>
          <td><span class="badge bg-{badge}">{r['status'].title()}</span></td>
          <td>{r['check_in_time'] or '–'}</td>
          <td>{r['source']}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Attendance Report – {session['session_name']}</title>
  <link rel="stylesheet"
    href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
  <style>
    body {{ font-family: Arial, sans-serif; padding: 20px; }}
    h1   {{ color: #1a3a5c; }}
    @media print {{ .no-print {{ display:none; }} }}
  </style>
</head>
<body>
  <div class="container">
    <div class="d-flex justify-content-between align-items-start mb-3">
      <div>
        <h1>Attendance Report</h1>
        <h4 class="text-muted">{session['session_name']} – {session['subject']}</h4>
      </div>
      <button class="btn btn-primary no-print" onclick="window.print()">🖨 Print</button>
    </div>
    <div class="row mb-3">
      <div class="col-md-3"><strong>Date:</strong> {session['session_date']}</div>
      <div class="col-md-3"><strong>Time:</strong> {session['start_time']} – {session['end_time']}</div>
      <div class="col-md-3"><strong>Department:</strong> {session['department']}</div>
      <div class="col-md-3"><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    </div>
    <div class="row mb-3">
      <div class="col-auto">
        <span class="badge bg-primary fs-6">Total: {total}</span>&nbsp;
        <span class="badge bg-success fs-6">Present/Late: {present}</span>&nbsp;
        <span class="badge bg-danger fs-6">Absent: {total - present}</span>&nbsp;
        <span class="badge bg-info fs-6">Attendance: {pct}%</span>
      </div>
    </div>
    <table class="table table-bordered table-striped">
      <thead class="table-dark">
        <tr><th>#</th><th>ID</th><th>Name</th><th>Department</th>
            <th>Status</th><th>Check-in Time</th><th>Source</th></tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    <p class="text-muted small mt-4">
      This report was generated by the Multimodal Attendance &amp; Engagement Agent.
      Attendance source is shown for transparency.
    </p>
  </div>
</body>
</html>"""
