"""
services/attendance_service.py
Handles all attendance business logic: check-in, correction, summaries.
"""

import logging
from datetime import datetime
from database.db import query_db, execute_db, get_db

logger = logging.getLogger(__name__)


def get_all_attendance(session_id: int) -> list:
    """Return all attendance records for a session, joined with student info."""
    rows = query_db(
        """
        SELECT ar.id, ar.session_id, ar.student_id,
               s.student_id AS student_code, s.name, s.department,
               ar.status, ar.check_in_time, ar.source,
               ar.corrected_by, ar.corrected_at, ar.notes, ar.created_at
        FROM   attendance_records ar
        JOIN   students s ON s.id = ar.student_id
        WHERE  ar.session_id = ?
        ORDER  BY s.name
        """,
        (session_id,),
    )
    return [dict(r) for r in rows]


def check_in(session_id: int, student_db_id: int, source: str = "manual",
             check_in_time: str = None, notes: str = "") -> dict:
    """
    Mark a student as present.  Returns the record or raises ValueError.
    Prevents duplicate check-ins.
    """
    # Look up the session to determine 'late' threshold
    session = query_db(
        "SELECT start_time FROM classroom_sessions WHERE id = ?",
        (session_id,), one=True
    )
    if not session:
        raise ValueError(f"Session {session_id} not found.")

    # Check duplicate
    existing = query_db(
        "SELECT id, status FROM attendance_records WHERE session_id=? AND student_id=?",
        (session_id, student_db_id), one=True
    )
    if existing and existing["status"] == "present":
        raise ValueError("Student is already marked present for this session.")

    now_str = check_in_time or datetime.now().isoformat(timespec="seconds")

    # Determine late vs present
    from flask import current_app
    late_mins = int(current_app.config.get("LATE_THRESHOLD_MINUTES", 15))
    status = "present"
    try:
        session_start = datetime.strptime(
            datetime.now().strftime("%Y-%m-%d") + " " + session["start_time"],
            "%Y-%m-%d %H:%M"
        )
        check_dt = datetime.fromisoformat(now_str)
        delta = (check_dt - session_start).total_seconds() / 60
        if delta > late_mins:
            status = "late"
    except Exception:
        pass

    if existing:
        execute_db(
            """UPDATE attendance_records
               SET status=?, check_in_time=?, source=?, notes=?, corrected_at=?
               WHERE id=?""",
            (status, now_str, source, notes, datetime.now().isoformat(), existing["id"])
        )
        rec_id = existing["id"]
    else:
        rec_id = execute_db(
            """INSERT INTO attendance_records
               (session_id, student_id, status, check_in_time, source, notes)
               VALUES (?,?,?,?,?,?)""",
            (session_id, student_db_id, status, now_str, source, notes)
        )

    return {"id": rec_id, "status": status, "check_in_time": now_str}


def mark_absent(session_id: int, student_db_id: int) -> dict:
    """Explicitly mark a student absent (creates record if missing)."""
    existing = query_db(
        "SELECT id FROM attendance_records WHERE session_id=? AND student_id=?",
        (session_id, student_db_id), one=True
    )
    if existing:
        execute_db(
            "UPDATE attendance_records SET status='absent', check_in_time=NULL WHERE id=?",
            (existing["id"],)
        )
        return {"id": existing["id"], "status": "absent"}
    else:
        rid = execute_db(
            """INSERT INTO attendance_records(session_id,student_id,status,source)
               VALUES(?,?,'absent','manual')""",
            (session_id, student_db_id)
        )
        return {"id": rid, "status": "absent"}


def correct_attendance(record_id: int, new_status: str,
                       corrected_by: str = "educator", notes: str = "") -> dict:
    """Allow an educator to override a status."""
    valid = {"present", "absent", "late"}
    if new_status not in valid:
        raise ValueError(f"Status must be one of {valid}")

    check_in_time = None
    if new_status in ("present", "late"):
        check_in_time = datetime.now().isoformat(timespec="seconds")

    execute_db(
        """UPDATE attendance_records
           SET status=?, check_in_time=?, corrected_by=?, corrected_at=?, notes=?
           WHERE id=?""",
        (new_status, check_in_time, corrected_by,
         datetime.now().isoformat(), notes, record_id)
    )
    return {"id": record_id, "status": new_status}


def get_session_summary(session_id: int) -> dict:
    """Return counts and percentage for a session."""
    rows = query_db(
        """SELECT status, COUNT(*) AS cnt
           FROM attendance_records WHERE session_id=?
           GROUP BY status""",
        (session_id,)
    )
    summary = {"present": 0, "absent": 0, "late": 0}
    for r in rows:
        summary[r["status"]] = r["cnt"]

    total = sum(summary.values())
    present_like = summary["present"] + summary["late"]
    pct = round(present_like / total * 100, 1) if total else 0
    return {
        "session_id": session_id,
        "total": total,
        "present": summary["present"],
        "late": summary["late"],
        "absent": summary["absent"],
        "attendance_pct": pct,
    }


def bulk_initialize_attendance(session_id: int, student_ids: list) -> int:
    """Pre-populate all selected students as absent so educator can check them in."""
    db = get_db()
    inserted = 0
    for sid in student_ids:
        try:
            db.execute(
                """INSERT OR IGNORE INTO attendance_records(session_id,student_id,status,source)
                   VALUES(?,?,'absent','manual')""",
                (session_id, sid)
            )
            inserted += 1
        except Exception as e:
            logger.warning("bulk_initialize skip sid=%s: %s", sid, e)
    db.commit()
    return inserted


def get_student_attendance_summary(student_db_id: int) -> dict:
    """Compute overall attendance statistics for one student."""
    rows = query_db(
        """SELECT ar.status, cs.session_name, cs.session_date, cs.subject
           FROM attendance_records ar
           JOIN classroom_sessions cs ON cs.id = ar.session_id
           WHERE ar.student_id = ?
           ORDER BY cs.session_date DESC""",
        (student_db_id,)
    )
    total = len(rows)
    present = sum(1 for r in rows if r["status"] in ("present", "late"))
    pct = round(present / total * 100, 1) if total else 0
    return {
        "total_sessions": total,
        "present": present,
        "absent": total - present,
        "attendance_pct": pct,
        "records": [dict(r) for r in rows],
    }
