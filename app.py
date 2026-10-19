"""
app.py - Main Flask Application Entry Point
Multimodal Attendance & Engagement Agent

Run with:
    python app.py
or:
    flask run --debug
"""

import logging
import os
from pathlib import Path

from flask import Flask, render_template, send_from_directory

from config import config
from database.db import close_db, init_db

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(config_name: str = None) -> Flask:
    """Application factory pattern – makes the app testable."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config.get(config_name, config["default"]))

    # Ensure required directories exist
    for folder in [
        app.config["UPLOAD_FOLDER"],
        app.config["REPORTS_FOLDER"],
        Path(app.config["DATABASE"]).parent,
    ]:
        Path(folder).mkdir(parents=True, exist_ok=True)

    # ── Database ──────────────────────────────────────────────────────────────
    with app.app_context():
        init_db(app)

    app.teardown_appcontext(close_db)

    # ── Register API Blueprints ────────────────────────────────────────────────
    from routes.students    import students_bp
    from routes.sessions    import sessions_bp
    from routes.attendance  import attendance_bp
    from routes.analysis    import analysis_bp
    from routes.engagement  import engagement_bp
    from routes.reports     import reports_bp
    from routes.settings    import settings_bp

    for bp in [students_bp, sessions_bp, attendance_bp,
               analysis_bp, engagement_bp, reports_bp, settings_bp]:
        app.register_blueprint(bp)

    # ── Frontend Page Routes ───────────────────────────────────────────────────
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/students")
    def students_page():
        return render_template("students.html")

    @app.route("/sessions")
    def sessions_page():
        return render_template("sessions.html")

    @app.route("/attendance")
    def attendance_page():
        return render_template("attendance.html")

    @app.route("/video-analysis")
    def video_analysis_page():
        return render_template("video_analysis.html")

    @app.route("/audio-analysis")
    def audio_analysis_page():
        return render_template("audio_analysis.html")

    @app.route("/engagement")
    def engagement_page():
        return render_template("engagement.html")

    @app.route("/recommendations")
    def recommendations_page():
        return render_template("recommendations.html")

    @app.route("/reports")
    def reports_page():
        return render_template("reports.html")

    @app.route("/settings")
    def settings_page():
        return render_template("settings.html")

    # ── Error Handlers ────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(413)
    def too_large(e):
        return {"error": "File too large. Maximum size is 500 MB."}, 413

    @app.errorhandler(500)
    def server_error(e):
        logger.exception("Internal server error")
        return {"error": "An internal error occurred."}, 500

    logger.info("App created in '%s' mode.", config_name)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)
