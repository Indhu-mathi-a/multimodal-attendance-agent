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
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row          # Rows behave like dicts
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")
    return g.db


def close_db(e=None):
    """Close the database connection at the end of a request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Create all tables and optionally load demo data."""
    from database.schema import SCHEMA_SQL, DEMO_DATA_SQL

    db_path = app.config["DATABASE"]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()

    if app.config.get("LOAD_DEMO_DATA"):
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
