"""
database/db.py - Database Connection Manager
Provides a thread-safe SQLite connection using Flask's application context.
"""

import sqlite3
import logging
from pathlib import Path

import flask
from flask import g

logger = logging.getLogger(__name__)


def get_db():
    """Return the database connection for the current request context."""
    if "db" not in g:
        db_path = flask.current_app.config["DATABASE"]
        try:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row          # Rows behave like dicts
        g.db.execute("PRAGMA foreign_keys = ON")
        try:
            g.db.execute("PRAGMA journal_mode = WAL")
        except sqlite3.OperationalError:
            g.db.execute("PRAGMA journal_mode = DELETE")
    return g.db


def close_db(e=None):
    """Close the database connection at the end of a request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Create all tables and optionally load demo data."""
    import shutil
    from database.schema import SCHEMA_SQL, DEMO_DATA_SQL

    db_path = Path(app.config["DATABASE"])
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    # In serverless environments, copy pre-seeded database if available
    repo_db = Path(__file__).resolve().parent / "attendance.db"
    if str(db_path).startswith("/tmp") and repo_db.exists() and not db_path.exists():
        try:
            shutil.copy2(repo_db, db_path)
            logger.info("Copied initial database from %s to %s", repo_db, db_path)
            return
        except Exception as e:
            logger.warning("Could not copy initial db: %s", e)

    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_SQL)
    conn.commit()

    if app.config.get("LOAD_DEMO_DATA"):
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM students")
        if cur.fetchone()[0] == 0:
            conn.executescript(DEMO_DATA_SQL)
            conn.commit()
            logger.info("Demo data loaded.")

    conn.close()
    logger.info("Database initialized at %s", db_path)


def query_db(query, args=(), one=False):
    """Helper: run a SELECT and return Row objects."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv


def execute_db(query, args=()):
    """Helper: run an INSERT / UPDATE / DELETE and commit."""
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    return cur.lastrowid
