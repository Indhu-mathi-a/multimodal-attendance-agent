"""
tests/test_app.py
Automated tests for the Multimodal Attendance & Engagement Agent.
Run with:  python -m pytest tests/ -v
"""

import json
import os
import sys
import tempfile
import pytest

# Make sure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    """Create a testing application instance with a temp database."""
    os.environ["FLASK_ENV"] = "testing"
    application = create_app("testing")
    application.config["LOAD_DEMO_DATA"] = True

    with application.app_context():
        from database.db import init_db
        init_db(application)

    yield application

    # Clean up test database
    db_path = application.config["DATABASE"]
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# ─── Helper ───────────────────────────────────────────────────────────────────

def jpost(client, url, payload):
    return client.post(url, json=payload, content_type="application/json")


def jput(client, url, payload):
    return client.put(url, json=payload, content_type="application/json")


# ─── Health ───────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/api/settings/health")
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "ok"

    def test_home_page(self, client):
        r = client.get("/")
        assert r.status_code == 200


# ─── Student Tests ────────────────────────────────────────────────────────────

class TestStudents:
    def test_list_students_empty_initially(self, client):
        r = client.get("/api/students")
        assert r.status_code == 200
        assert isinstance(r.get_json(), list)

    def test_create_student(self, client):
        r = jpost(client, "/api/students", {
            "student_id": "TEST001",
            "name": "Test Student",
            "department": "Testing",
            "email": "test@test.com",
        })
        assert r.status_code == 201
        data = r.get_json()
        assert data["student_id"] == "TEST001"
        assert data["name"] == "Test Student"

    def test_create_student_missing_fields(self, client):
        r = jpost(client, "/api/students", {"name": "No ID"})
        assert r.status_code == 400

    def test_create_duplicate_student(self, client):
        jpost(client, "/api/students", {
            "student_id": "DUP001", "name": "Dup A", "department": "X"
        })
        r = jpost(client, "/api/students", {
            "student_id": "DUP001", "name": "Dup B", "department": "X"
        })
        assert r.status_code == 409

    def test_get_student(self, client):
        # Create then fetch
        cr = jpost(client, "/api/students", {
            "student_id": "FETCH001", "name": "Fetch Me", "department": "A"
        })
        sid = cr.get_json()["id"]
        r = client.get(f"/api/students/{sid}")
        assert r.status_code == 200
        assert r.get_json()["name"] == "Fetch Me"

    def test_update_student(self, client):
        cr = jpost(client, "/api/students", {
            "student_id": "UPD001", "name": "Old Name", "department": "A"
        })
        sid = cr.get_json()["id"]
        r = jput(client, f"/api/students/{sid}", {
            "student_id": "UPD001", "name": "New Name", "department": "B"
        })
        assert r.status_code == 200
        assert r.get_json()["name"] == "New Name"

    def test_delete_student(self, client):
        cr = jpost(client, "/api/students", {
            "student_id": "DEL001", "name": "Delete Me", "department": "A"
        })
        sid = cr.get_json()["id"]
        r = client.delete(f"/api/students/{sid}")
        assert r.status_code == 200

    def test_get_nonexistent_student(self, client):
        r = client.get("/api/students/99999")
        assert r.status_code == 404

    def test_export_csv(self, client):
        r = client.get("/api/students/export/csv")
        assert r.status_code == 200
        assert "text/csv" in r.content_type


# ─── Session Tests ────────────────────────────────────────────────────────────

SESSION_PAYLOAD = {
    "session_name": "Test Session",
    "subject": "Test Subject",
    "department": "Testing",
    "session_date": "2025-01-15",
    "start_time": "09:00",
    "end_time": "10:30",
    "notes": "Automated test",
}


class TestSessions:
    def test_create_session(self, client):
        r = jpost(client, "/api/sessions", SESSION_PAYLOAD)
        assert r.status_code == 201
        data = r.get_json()
        assert data["session_name"] == "Test Session"
        assert data["status"] == "scheduled"

    def test_create_session_missing_name(self, client):
        bad = {**SESSION_PAYLOAD, "session_name": ""}
        r = jpost(client, "/api/sessions", bad)
        assert r.status_code == 400

    def test_list_sessions(self, client):
        r = client.get("/api/sessions")
        assert r.status_code == 200
        assert isinstance(r.get_json(), list)

    def test_update_status(self, client):
        cr = jpost(client, "/api/sessions", SESSION_PAYLOAD)
        sid = cr.get_json()["id"]
        r = client.patch(f"/api/sessions/{sid}/status",
                         json={"status": "active"},
                         content_type="application/json")
        assert r.status_code == 200
        assert r.get_json()["status"] == "active"

    def test_delete_session(self, client):
        cr = jpost(client, "/api/sessions", SESSION_PAYLOAD)
        sid = cr.get_json()["id"]
        r = client.delete(f"/api/sessions/{sid}")
        assert r.status_code == 200


# ─── Attendance Tests ─────────────────────────────────────────────────────────

class TestAttendance:
    def _setup(self, client):
        """Create a session and a student, return their IDs."""
        sr = jpost(client, "/api/students", {
            "student_id": f"ATT{id(self)}", "name": "Att Student", "department": "A"
        })
        student_id = sr.get_json()["id"]

        pr = jpost(client, "/api/sessions", SESSION_PAYLOAD)
        session_id = pr.get_json()["id"]
        return session_id, student_id

    def test_checkin(self, client):
        s_id, st_id = self._setup(client)
        r = jpost(client, "/api/attendance/checkin", {
            "session_id": s_id, "student_db_id": st_id, "source": "manual"
        })
        assert r.status_code == 200
        assert r.get_json()["status"] in ("present", "late")

    def test_duplicate_checkin_prevented(self, client):
        s_id, st_id = self._setup(client)
        jpost(client, "/api/attendance/checkin",
              {"session_id": s_id, "student_db_id": st_id})
        r = jpost(client, "/api/attendance/checkin",
                  {"session_id": s_id, "student_db_id": st_id})
        assert r.status_code == 409

    def test_mark_absent(self, client):
        s_id, st_id = self._setup(client)
        r = jpost(client, "/api/attendance/absent",
                  {"session_id": s_id, "student_db_id": st_id})
        assert r.status_code == 200
        assert r.get_json()["status"] == "absent"

    def test_qr_checkin(self, client):
        sr = jpost(client, "/api/students", {
            "student_id": "QRSTU001", "name": "QR Student", "department": "A"
        })
        pr = jpost(client, "/api/sessions", SESSION_PAYLOAD)
        s_id = pr.get_json()["id"]
        r = jpost(client, "/api/attendance/checkin/qr",
                  {"session_id": s_id, "student_code": "QRSTU001"})
        assert r.status_code == 200

    def test_qr_checkin_invalid_code(self, client):
        pr = jpost(client, "/api/sessions", SESSION_PAYLOAD)
        s_id = pr.get_json()["id"]
        r = jpost(client, "/api/attendance/checkin/qr",
                  {"session_id": s_id, "student_code": "DOESNOTEXIST"})
        assert r.status_code == 404

    def test_attendance_summary(self, client):
        s_id, st_id = self._setup(client)
        jpost(client, "/api/attendance/checkin",
              {"session_id": s_id, "student_db_id": st_id})
        r = client.get(f"/api/attendance/summary/session/{s_id}")
        assert r.status_code == 200
        data = r.get_json()
        assert "attendance_pct" in data

    def test_attendance_pct_calculation(self, client):
        """Create 4 students, mark 3 present → expect 75%."""
        students = []
        for i in range(4):
            sr = jpost(client, "/api/students", {
                "student_id": f"PCT{i}{id(self)}", "name": f"Student {i}", "department": "A"
            })
            students.append(sr.get_json()["id"])

        pr = jpost(client, "/api/sessions", SESSION_PAYLOAD)
        s_id = pr.get_json()["id"]

        # Init all as absent
        jpost(client, "/api/attendance/bulk-init",
              {"session_id": s_id, "student_ids": students})

        # Mark 3 present
        for st_id in students[:3]:
            jpost(client, "/api/attendance/checkin",
                  {"session_id": s_id, "student_db_id": st_id})

        r = client.get(f"/api/attendance/summary/session/{s_id}")
        assert r.status_code == 200
        data = r.get_json()
        assert data["attendance_pct"] == 75.0

    def test_correct_attendance(self, client):
        s_id, st_id = self._setup(client)
        # Mark absent first
        ar = jpost(client, "/api/attendance/absent",
                   {"session_id": s_id, "student_db_id": st_id})
        rec_id = ar.get_json()["id"]
        r = client.patch(f"/api/attendance/correct/{rec_id}",
                         json={"status": "present", "corrected_by": "educator"},
                         content_type="application/json")
        assert r.status_code == 200
        assert r.get_json()["status"] == "present"


# ─── Engagement Tests ─────────────────────────────────────────────────────────

class TestEngagement:
    def test_score_no_data(self, client):
        pr = jpost(client, "/api/sessions", SESSION_PAYLOAD)
        s_id = pr.get_json()["id"]
        r = client.get(f"/api/engagement/score/{s_id}")
        assert r.status_code == 200
        data = r.get_json()
        assert data["composite_score"] is None   # No data yet = no score
        assert "disclaimer" in data

    def test_log_participation(self, client):
        pr = jpost(client, "/api/sessions", SESSION_PAYLOAD)
        s_id = pr.get_json()["id"]
        r = jpost(client, "/api/engagement/participation", {
            "session_id": s_id, "event_type": "question_asked"
        })
        assert r.status_code == 201

    def test_invalid_event_type(self, client):
        pr = jpost(client, "/api/sessions", SESSION_PAYLOAD)
        s_id = pr.get_json()["id"]
        r = jpost(client, "/api/engagement/participation", {
            "session_id": s_id, "event_type": "invalid_type"
        })
        assert r.status_code == 400


# ─── Recommendation Tests ─────────────────────────────────────────────────────

class TestRecommendations:
    def test_generate_recs_insufficient_data(self, client):
        pr = jpost(client, "/api/sessions", SESSION_PAYLOAD)
        s_id = pr.get_json()["id"]
        r = client.get(f"/api/engagement/recommendations/{s_id}?refresh=true")
        assert r.status_code == 200
        # With no data, no recommendations should be generated
        assert r.get_json() == []

    def test_generate_recs_with_participation(self, client):
        """Log enough participation events to trigger at least one rule."""
        from services.recommendation_service import generate_recommendations

        score_data = {
            "composite_score": 40,
            "movement_score": 35,
            "audio_activity_pct": 25,
            "event_count": 1,
            "data_sufficient": True,
        }
        pr = jpost(client, "/api/sessions", SESSION_PAYLOAD)
        s_id = pr.get_json()["id"]

        import flask
        with client.application.app_context():
            recs = generate_recommendations(s_id, score_data, duration_min=45)

        assert len(recs) > 0
        for r in recs:
            assert "recommendation" in r
            assert "reason" in r
            assert "category" in r


# ─── Report Tests ─────────────────────────────────────────────────────────────

class TestReports:
    def test_attendance_csv(self, client):
        r = client.get("/api/reports/attendance/csv")
        assert r.status_code == 200
        assert "text/csv" in r.content_type

    def test_student_summary_csv(self, client):
        r = client.get("/api/reports/students/csv")
        assert r.status_code == 200

    def test_activity_csv(self, client):
        r = client.get("/api/reports/activity/csv")
        assert r.status_code == 200

    def test_dashboard_stats(self, client):
        r = client.get("/api/reports/dashboard/stats")
        assert r.status_code == 200
        data = r.get_json()
        assert "total_students" in data
        assert "total_sessions" in data

    def test_html_report_nonexistent_session(self, client):
        r = client.get("/api/reports/attendance/html/99999")
        assert r.status_code == 200   # Returns HTML with "Session not found"

    def test_invalid_file_upload(self, client):
        """Uploading a non-video file should return 400."""
        pr = jpost(client, "/api/sessions", SESSION_PAYLOAD)
        s_id = pr.get_json()["id"]
        data = {"file": (b"fake content", "test.txt", "text/plain")}
        import io
        r = client.post(
            f"/api/analysis/video/upload/{s_id}",
            data={"file": (io.BytesIO(b"fake"), "bad.txt")},
            content_type="multipart/form-data"
        )
        assert r.status_code == 400


# ─── Settings Tests ───────────────────────────────────────────────────────────

class TestSettings:
    def test_get_settings(self, client):
        r = client.get("/api/settings")
        assert r.status_code == 200
        data = r.get_json()
        assert "consent_obtained" in data

    def test_update_setting(self, client):
        r = jpost(client, "/api/settings", {"institution_name": "Test University"})
        assert r.status_code == 200

    def test_get_single_setting(self, client):
        r = client.get("/api/settings/institution_name")
        assert r.status_code == 200
