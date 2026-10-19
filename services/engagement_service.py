"""
services/engagement_service.py
Computes a transparent, configurable Activity and Participation Indicator (API score).

Score components (all normalised to 0-100):
  - movement_score       : from video analysis
  - audio_activity_pct   : from audio analysis
  - participation_score  : derived from educator-logged participation events

The composite score is the simple average of available components.
Missing components are excluded from the average (not replaced with 0).
"""

import json
import logging
from database.db import query_db, execute_db

logger = logging.getLogger(__name__)

# Maximum participation events per session that map to a score of 100
MAX_PARTICIPATION_EVENTS = 20


def compute_session_score(session_id: int) -> dict:
    """
    Compute (or retrieve) the composite Activity and Participation Indicator for a session.
    Returns a dict explaining each component and the final score.
    """
    # Get activity summary
    summary = query_db(
        "SELECT * FROM activity_summaries WHERE session_id=? AND processing_status='done' LIMIT 1",
        (session_id,), one=True
    )

    # Get participation events
    events = query_db(
        "SELECT COUNT(*) AS cnt FROM participation_events WHERE session_id=?",
        (session_id,), one=True
    )
    event_count = events["cnt"] if events else 0
    participation_score = min(event_count / MAX_PARTICIPATION_EVENTS * 100, 100)

    components = {}
    available = []

    if summary:
        if summary["movement_score"] is not None:
            components["movement"] = {
                "label": "Movement Activity",
                "value": round(float(summary["movement_score"]), 1),
                "description": "Aggregate body movement detected from video analysis.",
            }
            available.append(float(summary["movement_score"]))

        if summary["audio_activity_pct"] is not None:
            components["audio"] = {
                "label": "Audio Activity",
                "value": round(float(summary["audio_activity_pct"]), 1),
                "description": "Percentage of session time with detected speech-like audio.",
            }
            available.append(float(summary["audio_activity_pct"]))

    if event_count > 0:
        components["participation"] = {
            "label": "Recorded Participation",
            "value": round(participation_score, 1),
            "description": f"{event_count} participation events logged by educator.",
        }
        available.append(participation_score)

    composite = round(sum(available) / len(available), 1) if available else None

    timeline = []
    if summary and summary["activity_timeline"]:
        try:
            timeline = json.loads(summary["activity_timeline"])
        except Exception:
            pass

    return {
        "session_id": session_id,
        "composite_score": composite,
        "components": components,
        "components_available": len(available),
        "activity_timeline": timeline,
        "event_count": event_count,
        "data_sufficient": len(available) >= 1,
        "disclaimer": (
            "This score is an Activity and Participation Indicator based on aggregate "
            "classroom data. It does not measure individual student attention or academic ability."
        ),
    }


def get_multi_session_trend(session_ids: list) -> list:
    """Return composite scores for multiple sessions for trend charts."""
    result = []
    for sid in session_ids:
        score_data = compute_session_score(sid)
        session_info = query_db(
            "SELECT session_name, session_date, subject FROM classroom_sessions WHERE id=?",
            (sid,), one=True
        )
        if session_info:
            result.append({
                "session_id": sid,
                "session_name": session_info["session_name"],
                "session_date": session_info["session_date"],
                "subject": session_info["subject"],
                "composite_score": score_data["composite_score"],
            })
    return result


def log_participation_event(session_id: int, student_id: int | None,
                            event_type: str, notes: str = "") -> int:
    """Record a single participation event during a live session."""
    valid_types = {
        "question_asked", "answer_given", "discussion", "quiz_response", "other"
    }
    if event_type not in valid_types:
        raise ValueError(f"event_type must be one of {valid_types}")

    rid = execute_db(
        """INSERT INTO participation_events(session_id, student_id, event_type, notes)
           VALUES(?,?,?,?)""",
        (session_id, student_id, event_type, notes)
    )
    return rid
