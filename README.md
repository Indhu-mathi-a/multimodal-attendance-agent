# Multimodal Attendance & Engagement Agent

> **AI-powered, privacy-preserving classroom intelligence system**  
> Built for the SkillWallet Generative AI with Google Cloud experiential learning program.

---

## What This Project Does

This application helps educators:

- 📋 **Record classroom attendance** – manually, by student ID, or via QR scan.
- 📊 **Analyse classroom activity** – using local video and audio processing.
- 💡 **Get teaching suggestions** – from an offline rule-based recommendation engine.
- 📈 **View engagement analytics** – transparent Activity & Participation Indicator scores.
- 📄 **Export reports** – CSV and printable HTML, with date-range filters.

All media processing happens **locally on your device**. No video or audio is uploaded to external servers by default.

---

## Project Architecture

```
multimodal-attendance-agent/
├── app.py                   ← Flask application entry point (factory pattern)
├── config.py                ← Environment-aware configuration
├── requirements.txt
├── .env.example             ← Copy to .env and fill in your settings
├── database/
│   ├── db.py                ← SQLite connection manager
│   └── schema.py            ← All CREATE TABLE SQL + demo data
├── routes/                  ← Flask Blueprints (API endpoints)
│   ├── students.py          ← /api/students   (CRUD + CSV)
│   ├── sessions.py          ← /api/sessions   (CRUD + status)
│   ├── attendance.py        ← /api/attendance (check-in, QR, correction)
│   ├── analysis.py          ← /api/analysis   (video/audio upload & results)
│   ├── engagement.py        ← /api/engagement (scores, trends, participation)
│   ├── reports.py           ← /api/reports    (CSV, HTML, dashboard stats)
│   └── settings.py          ← /api/settings   (app config, health check)
├── services/                ← Business logic (no Flask dependency)
│   ├── attendance_service.py
│   ├── video_analysis.py    ← OpenCV-based (graceful fallback if absent)
│   ├── audio_analysis.py    ← pydub-based (graceful fallback if absent)
│   ├── engagement_service.py
│   ├── recommendation_service.py
│   └── report_service.py
├── templates/               ← Jinja2 HTML pages
├── static/
│   ├── css/app.css          ← Custom design system (no Tailwind)
│   └── js/                  ← Per-page JavaScript modules
├── tests/
│   └── test_app.py          ← pytest test suite
├── sample_data/
│   └── load_demo.py         ← Load demo students, sessions, attendance
├── uploads/                 ← Temporary media uploads (not committed)
└── reports/                 ← Generated report files (not committed)
```

---

## Quick Setup (Windows)

### 1 – Prerequisites
- Python 3.11 or 3.12
- Git (optional)

### 2 – Create and activate a virtual environment

```powershell
cd d:\smartbride\multimodal-attendance-agent
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> **Tip:** If PowerShell blocks execution, run:  
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 3 – Install dependencies

```powershell
pip install -r requirements.txt
```

If you want video analysis with OpenCV, also run:
```powershell
pip install opencv-python-headless==4.10.0.84
```

### 4 – Configure environment (optional)

```powershell
copy .env.example .env
# Edit .env – at minimum, change SECRET_KEY
```

### 5 – Load demo data (optional)

```powershell
python sample_data\load_demo.py
```

### 6 – Start the server

```powershell
python app.py
```

Open your browser at: **http://localhost:5000**

### 7 – Run tests

```powershell
python -m pytest tests/ -v
```

---

## Pages

| URL | Description |
|-----|-------------|
| `/` | Dashboard – stats, charts, recent sessions |
| `/students` | Register, edit, search, import/export students |
| `/sessions` | Create and manage classroom sessions |
| `/attendance` | Mark attendance, QR check-in, correct records |
| `/video-analysis` | Upload and analyse classroom videos locally |
| `/audio-analysis` | Upload and analyse audio activity locally |
| `/engagement` | Activity & Participation Indicator scores |
| `/recommendations` | Teaching suggestions with supporting evidence |
| `/reports` | CSV and HTML report downloads |
| `/settings` | App settings, privacy controls, health check |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/students` | List students |
| POST | `/api/students` | Create student |
| PUT | `/api/students/{id}` | Update student |
| DELETE | `/api/students/{id}` | Deactivate student |
| GET | `/api/students/export/csv` | Export CSV |
| POST | `/api/students/import/csv` | Import CSV |
| GET | `/api/sessions` | List sessions |
| POST | `/api/sessions` | Create session |
| PATCH | `/api/sessions/{id}/status` | Change status |
| POST | `/api/attendance/checkin` | Manual check-in |
| POST | `/api/attendance/checkin/qr` | QR/ID check-in |
| PATCH | `/api/attendance/correct/{id}` | Correct record |
| POST | `/api/analysis/video/upload/{id}` | Upload video |
| GET | `/api/analysis/video/progress/{id}` | Poll progress |
| POST | `/api/analysis/audio/upload/{id}` | Upload audio |
| GET | `/api/engagement/score/{id}` | Get session score |
| GET | `/api/engagement/trend` | Multi-session trend |
| POST | `/api/engagement/participation` | Log event |
| GET | `/api/engagement/recommendations/{id}` | Get/generate recs |
| GET | `/api/reports/attendance/csv` | Download CSV |
| GET | `/api/reports/attendance/html/{id}` | Printable HTML |
| GET | `/api/reports/dashboard/stats` | Dashboard stats |
| GET | `/api/settings/health` | Health check |

---

## Privacy Design

| Feature | Status |
|---------|--------|
| Local-only video processing | ✅ |
| No face recognition | ✅ |
| No speaker identification | ✅ |
| No emotion inference | ✅ |
| Manual attendance alternative | ✅ |
| Attendance source visible in every record | ✅ |
| Educator can correct/delete all records | ✅ |
| Consent checkbox in Settings | ✅ |
| Temporary file retention configurable | ✅ |

---

## Optional Features

### Video Analysis (OpenCV)
Install `opencv-python-headless`. If not installed, a simulation fallback runs automatically.

### Audio Analysis (pydub)
Install `pydub`. Uses energy-based silence detection only – no transcription.

### Gemini AI
Set `GEMINI_API_KEY` in `.env` and `USE_GEMINI=true`.  
If not configured, the offline rule-based engine runs instead.

---

## Publish to GitHub

```powershell
git init
git add .
git commit -m "Initial commit: Multimodal Attendance & Engagement Agent"
git remote add origin https://github.com/YOUR_USERNAME/multimodal-attendance-agent.git
git branch -M main
git push -u origin main
```

> **Note:** `.gitignore` already excludes the database, uploads, reports, and `.env`.

---

## Deployment Notes

- **Local / Development:** `python app.py` is sufficient.  
- **PythonAnywhere / Railway / Render:** Works with standard Python hosting.  
- **Video/Audio processing:** Cloud platforms often disable local media libraries.  
  Consider pre-processing media locally and uploading only the result JSON.  
- **Production:** Set `FLASK_ENV=production`, use gunicorn, and protect the instance behind a reverse proxy (nginx).

---

## Feature Checklist

| Feature | Implemented | Tested |
|---------|:-----------:|:------:|
| Student CRUD | ✅ | ✅ |
| CSV import/export | ✅ | ✅ |
| Session CRUD | ✅ | ✅ |
| Manual attendance | ✅ | ✅ |
| QR/ID check-in | ✅ | ✅ |
| Duplicate prevention | ✅ | ✅ |
| Educator correction | ✅ | ✅ |
| Attendance % calculation | ✅ | ✅ |
| Video upload & analysis | ✅ | ✅ |
| Video processing fallback | ✅ | — |
| Audio upload & analysis | ✅ | ✅ |
| Audio fallback | ✅ | — |
| Engagement score | ✅ | ✅ |
| Session trend chart | ✅ | — |
| Participation logging | ✅ | ✅ |
| Teaching recommendations | ✅ | ✅ |
| CSV reports (4 types) | ✅ | ✅ |
| HTML print report | ✅ | ✅ |
| Dashboard stats | ✅ | ✅ |
| Settings / Privacy page | ✅ | ✅ |
| Demo data | ✅ | — |
| Responsive design | ✅ | — |
| Dark sidebar | ✅ | — |
| Gemini AI integration | Optional | — |
| MediaPipe head-pose | Optional | — |
| Real-time audio capture | Not included | — |

---

## Known Limitations

1. **Video processing speed** – HOG detector is CPU-only and can be slow for long videos.
2. **Audio requires pydub** – ffmpeg must be installed on the system for non-WAV formats.
3. **No authentication** – This is a single-educator local tool. Add Flask-Login for multi-user scenarios.
4. **No real-time streaming** – Video must be uploaded as a file; live camera feeds are not supported.
5. **MediaPipe** – Not included due to Python version compatibility constraints; HOG detector is used instead.

---

*Built with Flask, SQLite, Bootstrap 5, Chart.js, OpenCV, and pydub.*
