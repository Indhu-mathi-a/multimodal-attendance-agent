"""
routes/settings.py - Application settings API
"""

from flask import Blueprint, jsonify, request
from database.db import query_db, execute_db

settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")


@settings_bp.route("", methods=["GET"])
def get_all_settings():
    rows = query_db("SELECT key, value FROM application_settings ORDER BY key")
    return jsonify({r["key"]: r["value"] for r in rows})


@settings_bp.route("/<key>", methods=["GET"])
def get_setting(key):
    row = query_db("SELECT value FROM application_settings WHERE key=?", (key,), one=True)
    if not row:
        return jsonify({"error": "Setting not found."}), 404
    return jsonify({"key": key, "value": row["value"]})


@settings_bp.route("", methods=["POST"])
def update_settings():
    data = request.get_json(silent=True) or {}
    for key, value in data.items():
        execute_db(
            """INSERT INTO application_settings(key, value)
               VALUES(?,?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')""",
            (str(key), str(value))
        )
    return jsonify({"message": f"Updated {len(data)} setting(s)."})


@settings_bp.route("/health", methods=["GET"])
def health():
    from database.db import query_db as q
    try:
        result = q("SELECT 1 AS ok", one=True)
        db_ok = result["ok"] == 1
    except Exception:
        db_ok = False
    return jsonify({
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
    }), 200 if db_ok else 503
