"""
routes/analysis.py - Video and audio analysis API endpoints
"""

import logging
import os
import threading
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from database.db import execute_db, query_db
from services.video_analysis import analyze_video
from services.audio_analysis import analyze_audio

analysis_bp = Blueprint("analysis", __name__, url_prefix="/api/analysis")
logger = logging.getLogger(__name__)

# Store processing progress in memory (per-session)
_progress: dict = {}


def _allowed(filename: str, extensions: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions


def _save_upload(file, folder: str, prefix: str) -> str:
    filename = secure_filename(file.filename)
    target = Path(folder) / f"{prefix}_{filename}"
    file.save(str(target))
    return str(target)


# ─── Video Analysis ────────────────────────────────────────────────────────────

@analysis_bp.route("/video/upload/<int:session_id>", methods=["POST"])
def upload_video(session_id):
    """Upload a video file and start background analysis."""
    session = query_db(
        "SELECT id FROM classroom_sessions WHERE id=?", (session_id,), one=True
    )
    if not session:
        return jsonify({"error": "Session not found."}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file part in request."}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "No file selected."}), 400

    allowed_ext = current_app.config.get(
        "ALLOWED_VIDEO_EXTENSIONS", {"mp4", "avi", "mov", "mkv", "webm"}
    )
    if not _allowed(f.filename, allowed_ext):
        return jsonify({"error": f"Unsupported file type. Allowed: {allowed_ext}"}), 400

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    video_path = _save_upload(f, upload_folder, f"session{session_id}")

    # Update session record
    execute_db(
        "UPDATE classroom_sessions SET video_path=?, updated_at=datetime('now') WHERE id=?",
        (video_path, session_id)
    )

    # Create pending summary record
    existing = query_db(
        "SELECT id FROM activity_summaries WHERE session_id=? AND analysis_type IN ('video','combined')",
        (session_id,), one=True
    )
    if existing:
        execute_db(
            "UPDATE activity_summaries SET processing_status='pending', processing_error=NULL WHERE id=?",
            (existing["id"],)
        )
        summary_id = existing["id"]
    else:
        summary_id = execute_db(
            """INSERT INTO activity_summaries(session_id, analysis_type, processing_status)
               VALUES(?, 'video', 'pending')""",
            (session_id,)
        )

    _progress[session_id] = 0

    # Background processing thread
    sample_rate = int(current_app.config.get("VIDEO_FRAME_SAMPLE_RATE", 5))

    def run():
        def cb(pct):
            _progress[session_id] = pct

        result = analyze_video(video_path, sample_rate, cb)

        import json
        if result.get("status") == "done":
            execute_db(
                """UPDATE activity_summaries
                   SET person_count_avg=?, movement_score=?, activity_timeline=?,
                       processing_status='done', processed_at=datetime('now'),
                       processing_error=NULL
                   WHERE id=?""",
                (result.get("person_count_avg"), result.get("movement_score"),
                 json.dumps(result.get("activity_timeline", [])), summary_id)
            )
        else:
            execute_db(
                """UPDATE activity_summaries
                   SET processing_status='failed', processing_error=?
                   WHERE id=?""",
                (result.get("error", "Unknown error"), summary_id)
            )
        _progress.pop(session_id, None)

    t = threading.Thread(target=run, daemon=True)
    t.start()

    return jsonify({
        "message": "Video uploaded. Processing started in background.",
        "summary_id": summary_id,
        "video_path": os.path.basename(video_path),
    }), 202


@analysis_bp.route("/video/progress/<int:session_id>", methods=["GET"])
def video_progress(session_id):
    pct = _progress.get(session_id)
    if pct is None:
        summary = query_db(
            "SELECT processing_status FROM activity_summaries WHERE session_id=?",
            (session_id,), one=True
        )
        status = summary["processing_status"] if summary else "no_data"
        return jsonify({"progress": 100 if status == "done" else 0, "status": status})
    return jsonify({"progress": pct, "status": "processing"})


@analysis_bp.route("/video/result/<int:session_id>", methods=["GET"])
def video_result(session_id):
    import json
    row = query_db(
        "SELECT * FROM activity_summaries WHERE session_id=? AND analysis_type='video'",
        (session_id,), one=True
    )
    if not row:
        return jsonify({"error": "No video analysis found for this session."}), 404
    data = dict(row)
    try:
        data["activity_timeline"] = json.loads(data.get("activity_timeline") or "[]")
    except Exception:
        data["activity_timeline"] = []
    return jsonify(data)


# ─── Audio Analysis ────────────────────────────────────────────────────────────

@analysis_bp.route("/audio/upload/<int:session_id>", methods=["POST"])
def upload_audio(session_id):
    """Upload an audio file and run local analysis."""
    session = query_db(
        "SELECT id FROM classroom_sessions WHERE id=?", (session_id,), one=True
    )
    if not session:
        return jsonify({"error": "Session not found."}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file part in request."}), 400

    f = request.files["file"]
    allowed_ext = current_app.config.get(
        "ALLOWED_AUDIO_EXTENSIONS", {"wav", "mp3", "ogg", "flac", "m4a"}
    )
    if not _allowed(f.filename, allowed_ext):
        return jsonify({"error": f"Unsupported audio format. Allowed: {allowed_ext}"}), 400

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    audio_path = _save_upload(f, upload_folder, f"audio_session{session_id}")

    execute_db(
        "UPDATE classroom_sessions SET audio_path=?, updated_at=datetime('now') WHERE id=?",
        (audio_path, session_id)
    )

    # Run analysis synchronously (audio is usually much smaller than video)
    import json
    from flask import current_app as cap
    chunk_ms = int(cap.config.get("AUDIO_CHUNK_DURATION_SEC", 5)) * 1000
    result = analyze_audio(audio_path, chunk_ms=chunk_ms)

    existing = query_db(
        "SELECT id FROM activity_summaries WHERE session_id=? AND analysis_type='audio'",
        (session_id,), one=True
    )
    if result["status"] == "done":
        if existing:
            execute_db(
                """UPDATE activity_summaries
                   SET audio_activity_pct=?, active_periods=?, quiet_periods=?,
                       activity_timeline=?, processing_status='done',
                       processed_at=datetime('now'), processing_error=NULL
                   WHERE id=?""",
                (result["audio_activity_pct"], result["active_periods"],
                 result["quiet_periods"], json.dumps(result["activity_timeline"]),
                 existing["id"])
            )
        else:
            execute_db(
                """INSERT INTO activity_summaries
                   (session_id, analysis_type, audio_activity_pct, active_periods,
                    quiet_periods, activity_timeline, processing_status, processed_at)
                   VALUES(?, 'audio', ?, ?, ?, ?, 'done', datetime('now'))""",
                (session_id, result["audio_activity_pct"], result["active_periods"],
                 result["quiet_periods"], json.dumps(result["activity_timeline"]))
            )

    return jsonify(result), 200 if result["status"] == "done" else 500


@analysis_bp.route("/audio/result/<int:session_id>", methods=["GET"])
def audio_result(session_id):
    import json
    row = query_db(
        "SELECT * FROM activity_summaries WHERE session_id=? AND analysis_type='audio'",
        (session_id,), one=True
    )
    if not row:
        return jsonify({"error": "No audio analysis found for this session."}), 404
    data = dict(row)
    try:
        data["activity_timeline"] = json.loads(data.get("activity_timeline") or "[]")
    except Exception:
        data["activity_timeline"] = []
    return jsonify(data)
