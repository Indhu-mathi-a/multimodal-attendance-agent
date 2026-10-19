"""
sample_data/load_demo.py
Run this script to load demo students, sessions, and attendance data
into an already-initialised database.

Usage:
    python sample_data/load_demo.py
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database.schema import DEMO_DATA_SQL
import sqlite3

def load():
    app = create_app("development")
    db_path = app.config["DATABASE"]
    print(f"Loading demo data into: {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(DEMO_DATA_SQL)
        conn.commit()
        print("✓ Demo data loaded successfully.")
        print("  10 students, 5 sessions, attendance records, and recommendations.")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    load()
