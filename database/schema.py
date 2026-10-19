"""
database/schema.py - SQLite Schema Definitions
Creates all tables with proper foreign keys, indexes, and constraints.
"""

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

-- Students table
CREATE TABLE IF NOT EXISTS students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  TEXT    NOT NULL UNIQUE,
    name        TEXT    NOT NULL,
    department  TEXT    NOT NULL DEFAULT '',
    email       TEXT    DEFAULT '',
    phone       TEXT    DEFAULT '',
    enrolled_at TEXT    NOT NULL DEFAULT (datetime('now')),
    is_active   INTEGER NOT NULL DEFAULT 1,
    notes       TEXT    DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_students_student_id ON students(student_id);
CREATE INDEX IF NOT EXISTS idx_students_department  ON students(department);

-- Classroom sessions table
CREATE TABLE IF NOT EXISTS classroom_sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_name TEXT    NOT NULL,
    subject      TEXT    NOT NULL,
    department   TEXT    NOT NULL DEFAULT '',
    session_date TEXT    NOT NULL,
    start_time   TEXT    NOT NULL,
    end_time     TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'scheduled',   -- scheduled | active | completed | cancelled
    video_path   TEXT    DEFAULT NULL,
    audio_path   TEXT    DEFAULT NULL,
    notes        TEXT    DEFAULT '',
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sessions_date       ON classroom_sessions(session_date);
CREATE INDEX IF NOT EXISTS idx_sessions_department ON classroom_sessions(department);

-- Attendance records table
CREATE TABLE IF NOT EXISTS attendance_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    student_id      INTEGER NOT NULL REFERENCES students(id)            ON DELETE CASCADE,
    status          TEXT    NOT NULL DEFAULT 'absent',    -- present | absent | late
    check_in_time   TEXT    DEFAULT NULL,
    source          TEXT    NOT NULL DEFAULT 'manual',    -- manual | qr | video_assisted
    corrected_by    TEXT    DEFAULT NULL,
    corrected_at    TEXT    DEFAULT NULL,
    notes           TEXT    DEFAULT '',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(session_id, student_id)
);
CREATE INDEX IF NOT EXISTS idx_attendance_session ON attendance_records(session_id);
CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance_records(student_id);

-- Activity summaries table  (from video / audio analysis)
CREATE TABLE IF NOT EXISTS activity_summaries (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id              INTEGER NOT NULL REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    analysis_type           TEXT    NOT NULL,   -- video | audio | combined
    person_count_avg        REAL    DEFAULT NULL,
    movement_score          REAL    DEFAULT NULL,
    audio_activity_pct      REAL    DEFAULT NULL,
    quiet_periods           INTEGER DEFAULT 0,
    active_periods          INTEGER DEFAULT 0,
    activity_timeline       TEXT    DEFAULT '[]',   -- JSON array of {time, score}
    raw_data                TEXT    DEFAULT '{}',
    processing_status       TEXT    NOT NULL DEFAULT 'pending',   -- pending | processing | done | failed
    processing_error        TEXT    DEFAULT NULL,
    processed_at            TEXT    DEFAULT NULL,
    created_at              TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_activity_session ON activity_summaries(session_id);

-- Participation events (educator-recorded interactions)
CREATE TABLE IF NOT EXISTS participation_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    student_id  INTEGER REFERENCES students(id) ON DELETE SET NULL,
    event_type  TEXT    NOT NULL,   -- question_asked | answer_given | discussion | quiz_response
    event_time  TEXT    NOT NULL    DEFAULT (datetime('now')),
    notes       TEXT    DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_participation_session ON participation_events(session_id);

-- Teaching recommendations
CREATE TABLE IF NOT EXISTS teaching_recommendations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES classroom_sessions(id) ON DELETE CASCADE,
    category        TEXT    NOT NULL,   -- activity | break | pacing | discussion | quiz | revision
    recommendation  TEXT    NOT NULL,
    reason          TEXT    NOT NULL,
    supporting_data TEXT    DEFAULT '{}',   -- JSON evidence
    priority        INTEGER NOT NULL DEFAULT 2,   -- 1=high 2=medium 3=low
    is_dismissed    INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_recommendations_session ON teaching_recommendations(session_id);

-- Application settings
CREATE TABLE IF NOT EXISTS application_settings (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    key       TEXT NOT NULL UNIQUE,
    value     TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Insert default settings
INSERT OR IGNORE INTO application_settings(key, value) VALUES
    ('consent_obtained',         'false'),
    ('audio_analysis_enabled',   'true'),
    ('video_analysis_enabled',   'true'),
    ('data_retention_days',      '7'),
    ('late_threshold_minutes',   '15'),
    ('attendance_pass_pct',      '75'),
    ('app_name',                 'Multimodal Attendance & Engagement Agent'),
    ('institution_name',         'My Institution');
"""

DEMO_DATA_SQL = """
-- Demo students
INSERT OR IGNORE INTO students(student_id, name, department, email) VALUES
    ('STU001', 'Aarav Sharma',    'Computer Science', 'aarav@example.edu'),
    ('STU002', 'Priya Patel',     'Computer Science', 'priya@example.edu'),
    ('STU003', 'Rohan Mehta',     'Computer Science', 'rohan@example.edu'),
    ('STU004', 'Ananya Iyer',     'Computer Science', 'ananya@example.edu'),
    ('STU005', 'Karthik Raj',     'Computer Science', 'karthik@example.edu'),
    ('STU006', 'Divya Nair',      'Mathematics',      'divya@example.edu'),
    ('STU007', 'Arjun Kumar',     'Mathematics',      'arjun@example.edu'),
    ('STU008', 'Sneha Reddy',     'Mathematics',      'sneha@example.edu'),
    ('STU009', 'Vikram Singh',    'Physics',          'vikram@example.edu'),
    ('STU010', 'Meera Joshi',     'Physics',          'meera@example.edu');

-- Demo sessions
INSERT OR IGNORE INTO classroom_sessions(id, session_name, subject, department, session_date, start_time, end_time, status, notes) VALUES
    (1, 'CS Morning Lecture',   'Data Structures',     'Computer Science', date('now', '-6 days'), '09:00', '10:30', 'completed', 'Demo session'),
    (2, 'Math Morning Lecture', 'Linear Algebra',      'Mathematics',      date('now', '-5 days'), '10:00', '11:30', 'completed', 'Demo session'),
    (3, 'CS Afternoon Lab',     'Algorithms Lab',      'Computer Science', date('now', '-4 days'), '14:00', '16:00', 'completed', 'Demo session'),
    (4, 'Physics Lecture',      'Quantum Mechanics',   'Physics',          date('now', '-3 days'), '11:00', '12:30', 'completed', 'Demo session'),
    (5, 'CS Workshop',          'Python Programming',  'Computer Science', date('now', '-1 days'), '09:00', '11:00', 'completed', 'Demo session');

-- Demo attendance
INSERT OR IGNORE INTO attendance_records(session_id, student_id, status, check_in_time, source) VALUES
    (1, 1, 'present', datetime('now', '-6 days', '+9 hours'),  'manual'),
    (1, 2, 'present', datetime('now', '-6 days', '+9 hours'),  'manual'),
    (1, 3, 'late',    datetime('now', '-6 days', '+9 hours', '+18 minutes'), 'manual'),
    (1, 4, 'present', datetime('now', '-6 days', '+9 hours'),  'manual'),
    (1, 5, 'absent',  NULL,                                    'manual'),
    (2, 6, 'present', datetime('now', '-5 days', '+10 hours'), 'manual'),
    (2, 7, 'present', datetime('now', '-5 days', '+10 hours'), 'manual'),
    (2, 8, 'absent',  NULL,                                    'manual'),
    (3, 1, 'present', datetime('now', '-4 days', '+14 hours'), 'manual'),
    (3, 2, 'present', datetime('now', '-4 days', '+14 hours'), 'manual'),
    (3, 3, 'present', datetime('now', '-4 days', '+14 hours'), 'manual'),
    (3, 4, 'absent',  NULL,                                    'manual'),
    (3, 5, 'present', datetime('now', '-4 days', '+14 hours'), 'manual'),
    (4, 9, 'present', datetime('now', '-3 days', '+11 hours'), 'manual'),
    (4,10, 'present', datetime('now', '-3 days', '+11 hours'), 'manual'),
    (5, 1, 'present', datetime('now', '-1 days', '+9 hours'),  'qr'),
    (5, 2, 'present', datetime('now', '-1 days', '+9 hours'),  'qr'),
    (5, 3, 'late',    datetime('now', '-1 days', '+9 hours', '+20 minutes'), 'qr'),
    (5, 4, 'present', datetime('now', '-1 days', '+9 hours'),  'qr'),
    (5, 5, 'present', datetime('now', '-1 days', '+9 hours'),  'qr');

-- Demo activity summaries
INSERT OR IGNORE INTO activity_summaries(session_id, analysis_type, person_count_avg, movement_score, audio_activity_pct, quiet_periods, active_periods, activity_timeline, processing_status, processed_at) VALUES
    (1, 'combined', 4.2, 62.5, 78.3, 2, 8, '[{"t":0,"s":55},{"t":10,"s":70},{"t":20,"s":65},{"t":30,"s":80},{"t":40,"s":60},{"t":50,"s":75},{"t":60,"s":55},{"t":70,"s":68},{"t":80,"s":72},{"t":90,"s":63}]', 'done', datetime('now','-6 days')),
    (3, 'combined', 4.8, 74.1, 85.2, 1, 11, '[{"t":0,"s":60},{"t":15,"s":78},{"t":30,"s":82},{"t":45,"s":70},{"t":60,"s":88},{"t":75,"s":75},{"t":90,"s":80},{"t":105,"s":73},{"t":120,"s":66}]', 'done', datetime('now','-4 days')),
    (5, 'combined', 4.9, 81.3, 90.1, 1, 13, '[{"t":0,"s":65},{"t":15,"s":85},{"t":30,"s":90},{"t":45,"s":78},{"t":60,"s":88},{"t":75,"s":92},{"t":90,"s":82},{"t":105,"s":86},{"t":120,"s":79}]', 'done', datetime('now','-1 days'));

-- Demo recommendations
INSERT OR IGNORE INTO teaching_recommendations(session_id, category, recommendation, reason, priority) VALUES
    (1, 'break',      'Schedule a 5-minute break at the 45-minute mark', 'Audio activity dropped significantly around minute 45, suggesting reduced engagement.', 1),
    (1, 'activity',   'Introduce a quick group activity', 'Movement scores were below 50 during the second half of the session.', 2),
    (3, 'quiz',       'Start with a 5-question quick quiz', 'Previous session showed high initial engagement that dropped after 60 minutes.', 2),
    (5, 'pacing',     'Maintain the current pace – high engagement observed', 'Activity score 81/100 with sustained audio activity throughout the session.', 3);
"""
