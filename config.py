"""
config.py - Application Configuration
Centralizes all settings so they are easy to change in one place.
"""

import os
from pathlib import Path

# ─── Base Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))

if IS_VERCEL:
    DATABASE_PATH = Path("/tmp") / "attendance.db"
    UPLOAD_FOLDER = Path("/tmp") / "uploads"
    REPORTS_FOLDER = Path("/tmp") / "reports"
else:
    DATABASE_PATH = BASE_DIR / "database" / "attendance.db"
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    REPORTS_FOLDER = BASE_DIR / "reports"

# ─── Flask Settings ────────────────────────────────────────────────────────────
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DATABASE = str(DATABASE_PATH)
    UPLOAD_FOLDER = str(UPLOAD_FOLDER)
    REPORTS_FOLDER = str(REPORTS_FOLDER)
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024   # 500 MB upload limit

    # Allowed file extensions
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}
    ALLOWED_AUDIO_EXTENSIONS = {"wav", "mp3", "ogg", "flac", "m4a"}
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}

    # Video processing
    VIDEO_FRAME_SAMPLE_RATE = 5          # Process every Nth frame
    VIDEO_PERSON_DETECTION_CONFIDENCE = 0.5

    # Attendance thresholds
    LATE_THRESHOLD_MINUTES = 15          # Minutes after start = "Late"
    ATTENDANCE_PERCENTAGE_PASS = 75      # % required to be marked present

    # Audio analysis
    AUDIO_SILENCE_THRESHOLD = 0.02       # RMS below this = silence
    AUDIO_CHUNK_DURATION_SEC = 5         # Chunk length for analysis

    # Gemini AI (optional)
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    USE_GEMINI = bool(os.environ.get("USE_GEMINI", False))

    # Demo data (default to true on Vercel for instant demo preview)
    LOAD_DEMO_DATA = os.environ.get("LOAD_DEMO_DATA", "true" if IS_VERCEL else "false").lower() == "true"

    # Data retention (days). 0 = keep forever
    TEMP_FILE_RETENTION_DAYS = 7


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    DATABASE = str(BASE_DIR / "database" / "test_attendance.db")


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
