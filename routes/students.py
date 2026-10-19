"""
routes/students.py - Student management API
CRUD + CSV import/export
"""

import csv
import io
import logging
from flask import Blueprint, jsonify, request, make_response
from database.db import query_db, execute_db, get_db

students_bp = Blueprint("students", __name__, url_prefix="/api/students")
logger = logging.getLogger(__name__)


def _validate_student(data: dict, require_all=True) -> tuple[dict, list]:
    """Return (cleaned_data, errors)."""
    errors = []
    cleaned = {}

    sid = (data.get("student_id") or "").strip()
    if require_all and not sid:
        errors.append("student_id is required.")
    cleaned["student_id"] = sid

    name = (data.get("name") or "").strip()
    if require_all and not name:
        errors.append("name is required.")
    cleaned["name"] = name

    cleaned["department"] = (data.get("department") or "").strip()
    cleaned["email"] = (data.get("email") or "").strip()
    cleaned["phone"] = (data.get("phone") or "").strip()
    cleaned["notes"] = (data.get("notes") or "").strip()

    return cleaned, errors


@students_bp.route("", methods=["GET"])
def list_students():
    q = request.args.get("q", "").strip()
    dept = request.args.get("department", "").strip()
    active_only = request.args.get("active", "true").lower() == "true"

    params = []
    wheres = []

    if active_only:
        wheres.append("is_active = 1")
    if q:
        wheres.append("(name LIKE ? OR student_id LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    if dept:
        wheres.append("department = ?")
        params.append(dept)

    where_str = "WHERE " + " AND ".join(wheres) if wheres else ""
    rows = query_db(
        f"SELECT * FROM students {where_str} ORDER BY name", params
    )
    return jsonify([dict(r) for r in rows])


@students_bp.route("/<int:student_id>", methods=["GET"])
def get_student(student_id):
    row = query_db("SELECT * FROM students WHERE id=?", (student_id,), one=True)
    if not row:
        return jsonify({"error": "Student not found."}), 404
    return jsonify(dict(row))


@students_bp.route("", methods=["POST"])
def create_student():
    data = request.get_json(silent=True) or {}
    cleaned, errors = _validate_student(data)
    if errors:
        return jsonify({"error": errors}), 400

    # Check duplicate student_id
    existing = query_db(
        "SELECT id FROM students WHERE student_id=?", (cleaned["student_id"],), one=True
    )
    if existing:
        return jsonify({"error": "A student with this ID already exists."}), 409

    try:
        new_id = execute_db(
            """INSERT INTO students(student_id, name, department, email, phone, notes)
               VALUES(?,?,?,?,?,?)""",
            (cleaned["student_id"], cleaned["name"], cleaned["department"],
             cleaned["email"], cleaned["phone"], cleaned["notes"]),
        )
        row = query_db("SELECT * FROM students WHERE id=?", (new_id,), one=True)
        return jsonify(dict(row)), 201
    except Exception as e:
        logger.exception("Create student error")
        return jsonify({"error": str(e)}), 500


@students_bp.route("/<int:student_id>", methods=["PUT"])
def update_student(student_id):
    row = query_db("SELECT id FROM students WHERE id=?", (student_id,), one=True)
    if not row:
        return jsonify({"error": "Student not found."}), 404

    data = request.get_json(silent=True) or {}
    cleaned, errors = _validate_student(data, require_all=False)
    if errors:
        return jsonify({"error": errors}), 400

    try:
        execute_db(
            """UPDATE students
               SET student_id=COALESCE(NULLIF(?,''), student_id),
                   name=COALESCE(NULLIF(?,''), name),
                   department=?, email=?, phone=?, notes=?
               WHERE id=?""",
            (cleaned["student_id"], cleaned["name"], cleaned["department"],
             cleaned["email"], cleaned["phone"], cleaned["notes"], student_id)
        )
        updated = query_db("SELECT * FROM students WHERE id=?", (student_id,), one=True)
        return jsonify(dict(updated))
    except Exception as e:
        logger.exception("Update student error")
        return jsonify({"error": str(e)}), 500


@students_bp.route("/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    row = query_db("SELECT id FROM students WHERE id=?", (student_id,), one=True)
    if not row:
        return jsonify({"error": "Student not found."}), 404

    execute_db("UPDATE students SET is_active=0 WHERE id=?", (student_id,))
    return jsonify({"message": "Student deactivated."})


@students_bp.route("/departments", methods=["GET"])
def list_departments():
    rows = query_db(
        "SELECT DISTINCT department FROM students WHERE is_active=1 ORDER BY department"
    )
    return jsonify([r["department"] for r in rows if r["department"]])


@students_bp.route("/export/csv", methods=["GET"])
def export_csv():
    rows = query_db(
        "SELECT student_id, name, department, email, phone, enrolled_at, notes "
        "FROM students WHERE is_active=1 ORDER BY name"
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID", "Name", "Department", "Email", "Phone",
                     "Enrolled At", "Notes"])
    for r in rows:
        writer.writerow(list(r))

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = "attachment; filename=students.csv"
    return response


@students_bp.route("/import/csv", methods=["POST"])
def import_csv():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400
    f = request.files["file"]
    if not f.filename.endswith(".csv"):
        return jsonify({"error": "Only CSV files are accepted."}), 400

    reader = csv.DictReader(io.StringIO(f.read().decode("utf-8-sig")))
    imported = skipped = errors_list = 0
    error_msgs = []
    db = get_db()

    for row in reader:
        sid = row.get("Student ID", "").strip()
        name = row.get("Name", "").strip()
        dept = row.get("Department", "").strip()
        email = row.get("Email", "").strip()

        if not sid or not name:
            skipped += 1
            continue
        try:
            db.execute(
                """INSERT OR IGNORE INTO students(student_id, name, department, email)
                   VALUES(?,?,?,?)""",
                (sid, name, dept, email)
            )
            imported += 1
        except Exception as e:
            error_msgs.append(str(e))
            errors_list += 1

    db.commit()
    return jsonify({
        "imported": imported, "skipped": skipped, "errors": errors_list,
        "error_messages": error_msgs[:5]
    })
