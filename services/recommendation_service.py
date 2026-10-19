"""
services/recommendation_service.py
Offline rule-based teaching recommendation engine.

Rules are transparent: every suggestion includes the observation that triggered it
and the data value that was observed. No ML model is needed.
"""

import json
import logging
from database.db import query_db, execute_db

logger = logging.getLogger(__name__)

# ─── Rule definitions ──────────────────────────────────────────────────────────
# Each rule is a tuple: (category, priority, condition_fn, recommendation, reason_template)
# condition_fn receives the score_data dict and returns True if the rule fires.

RULES = [
    # ── Breaks ──
    (
        "break", 1,
        lambda d: d.get("composite_score") is not None and d["composite_score"] < 50,
        "Schedule a 5-minute break now.",
        "Overall activity score is {composite_score}/100, suggesting low engagement. "
        "A short break often resets attention.",
    ),
    (
        "break", 2,
        lambda d: d.get("session_duration_min", 0) >= 60
                  and d.get("composite_score") is not None,
        "Consider a brief stretch or comfort break.",
        "The session has run for {session_duration_min} minutes. "
        "Regular breaks improve focus for extended sessions.",
    ),

    # ── Interactive activities ──
    (
        "activity", 1,
        lambda d: d.get("movement_score") is not None and d["movement_score"] < 40,
        "Introduce a short collaborative activity (e.g., pair discussion, whiteboard exercise).",
        "Movement activity score is {movement_score}/100. "
        "Low movement can indicate passive listening; interactive tasks re-engage students.",
    ),
    (
        "activity", 2,
        lambda d: d.get("audio_activity_pct") is not None and d["audio_activity_pct"] < 30,
        "Ask the class an open question to stimulate verbal participation.",
        "Audio activity was {audio_activity_pct}% of the session. "
        "Extended silence may indicate students are hesitant to participate.",
    ),

    # ── Quizzes ──
    (
        "quiz", 2,
        lambda d: d.get("event_count", 0) < 3 and d.get("data_sufficient"),
        "Start a 5-question quick revision quiz.",
        "Only {event_count} participation events were recorded this session. "
        "A quiz can surface understanding gaps and boost engagement.",
    ),

    # ── Pacing ──
    (
        "pacing", 3,
        lambda d: d.get("composite_score") is not None and d["composite_score"] >= 75,
        "Maintain the current teaching pace – high activity observed.",
        "Composite activity score is {composite_score}/100. The session appears well-engaged.",
    ),
    (
        "pacing", 2,
        lambda d: d.get("audio_activity_pct") is not None and d["audio_activity_pct"] > 80,
        "Excellent verbal participation! Consider a brief consolidation activity.",
        "Audio activity was {audio_activity_pct}% – very high. "
        "Pausing to consolidate learning can reinforce concepts.",
    ),

    # ── Group discussion ──
    (
        "discussion", 2,
        lambda d: (d.get("composite_score") or 0) < 65
                  and (d.get("event_count", 0)) < 5,
        "Organise a 10-minute group discussion on a key topic.",
        "Both activity score ({composite_score}/100) and participation events ({event_count}) "
        "are moderate. Group discussion can raise both metrics.",
    ),
]


def generate_recommendations(session_id: int, score_data: dict,
                              session_duration_min: int = 0) -> list:
    """
    Evaluate all rules against score_data and persist new recommendations.
    Returns a list of recommendation dicts.
    """
    if not score_data.get("data_sufficient"):
        logger.info("Insufficient data for session %s – skipping recommendations.", session_id)
        # Delete stale recs for this session
        _clear_recommendations(session_id)
        return []

    ctx = {**score_data}
    ctx["session_duration_min"] = session_duration_min

    fired_recs = []
    for category, priority, condition, rec_text, reason_tmpl in RULES:
        try:
            if condition(ctx):
                # Format reason with available values (missing keys → "N/A")
                class SafeDict(dict):
                    def __missing__(self, key):
                        return "N/A"

                reason = reason_tmpl.format_map(SafeDict(ctx))
                fired_recs.append({
                    "category": category,
                    "recommendation": rec_text,
                    "reason": reason,
                    "priority": priority,
                    "supporting_data": json.dumps({
                        k: ctx.get(k) for k in
                        ["composite_score", "movement_score",
                         "audio_activity_pct", "event_count"]
                    }),
                })
        except Exception as e:
            logger.warning("Rule evaluation error: %s", e)

    # Persist to DB (replace previous recs for this session)
    _clear_recommendations(session_id)
    for rec in fired_recs:
        execute_db(
            """INSERT INTO teaching_recommendations
               (session_id, category, recommendation, reason, supporting_data, priority)
               VALUES(?,?,?,?,?,?)""",
            (session_id, rec["category"], rec["recommendation"],
             rec["reason"], rec["supporting_data"], rec["priority"])
        )

    return _get_saved_recommendations(session_id)


def _clear_recommendations(session_id: int):
    execute_db(
        "DELETE FROM teaching_recommendations WHERE session_id=? AND is_dismissed=0",
        (session_id,)
    )


def _get_saved_recommendations(session_id: int) -> list:
    rows = query_db(
        """SELECT * FROM teaching_recommendations
           WHERE session_id=? AND is_dismissed=0
           ORDER BY priority""",
        (session_id,)
    )
    return [dict(r) for r in rows]


def get_recommendations(session_id: int) -> list:
    """Retrieve existing saved recommendations for a session."""
    rows = query_db(
        """SELECT * FROM teaching_recommendations
           WHERE session_id=? AND is_dismissed=0
           ORDER BY priority""",
        (session_id,)
    )
    return [dict(r) for r in rows]


def dismiss_recommendation(rec_id: int) -> bool:
    execute_db(
        "UPDATE teaching_recommendations SET is_dismissed=1 WHERE id=?", (rec_id,)
    )
    return True
