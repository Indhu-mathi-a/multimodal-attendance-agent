"""
services/video_analysis.py
Local-only video processing using OpenCV.
Detects and tracks persons frame-by-frame, produces movement/activity scores.

Privacy notes:
  - No face recognition or biometric identification.
  - No data sent to external servers.
  - Raw video is deleted after processing unless the user keeps it.
  - Results are aggregate, not tied to a specific individual.
"""

import json
import logging
import os
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# ── Lazy-load OpenCV so the app starts even if cv2 is missing ──────────────────
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not installed – video analysis will use a simulated fallback.")


def _allowed_video(filename: str, allowed_ext: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_ext


def analyze_video(video_path: str, frame_sample_rate: int = 5,
                  progress_callback=None) -> dict:
    """
    Process a video file and return aggregate activity data.

    Returns a dict with:
        person_count_avg, movement_score (0-100), activity_timeline,
        duration_seconds, frames_processed, status, error
    """
    if not CV2_AVAILABLE:
        return _simulate_video_analysis(video_path)

    if not Path(video_path).exists():
        return {"status": "failed", "error": "Video file not found.", "movement_score": 0}

    try:
        return _run_cv2_analysis(video_path, frame_sample_rate, progress_callback)
    except Exception as exc:
        logger.exception("Video analysis error: %s", exc)
        return {"status": "failed", "error": str(exc), "movement_score": 0}


def _run_cv2_analysis(video_path: str, sample_rate: int, progress_cb) -> dict:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"status": "failed", "error": "Cannot open video file.", "movement_score": 0}

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps if fps > 0 else 0

    # HOG person detector (CPU-only, no GPU required)
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    # Background subtractor for movement detection
    bg_sub = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=40)

    person_counts = []
    movement_scores = []
    timeline = []
    frame_idx = 0
    processed = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if frame_idx % sample_rate != 0:
            continue

        processed += 1
        timestamp_sec = frame_idx / fps

        # Resize for speed
        small = cv2.resize(frame, (640, 360))

        # Movement via background subtraction
        fg_mask = bg_sub.apply(small)
        movement_pct = (np.sum(fg_mask > 200) / fg_mask.size) * 100

        # Person detection (lighter version on smaller frame)
        try:
            rects, _ = hog.detectMultiScale(
                small, winStride=(16, 16), padding=(4, 4), scale=1.05
            )
            n_persons = len(rects)
        except Exception:
            n_persons = 0

        person_counts.append(n_persons)
        movement_scores.append(min(movement_pct * 5, 100))  # scale to 0-100

        # Aggregate every ~60 seconds of video into one timeline point
        bucket = int(timestamp_sec // 60) * 60
        if not timeline or timeline[-1]["t"] != bucket:
            timeline.append({"t": bucket, "s": round(movement_scores[-1], 1)})
        else:
            # Running average
            prev = timeline[-1]["s"]
            timeline[-1]["s"] = round((prev + movement_scores[-1]) / 2, 1)

        if progress_cb and processed % 50 == 0:
            pct = min(int(frame_idx / total_frames * 100), 99)
            progress_cb(pct)

    cap.release()

    avg_persons = round(float(np.mean(person_counts)), 1) if person_counts else 0
    avg_movement = round(float(np.mean(movement_scores)), 1) if movement_scores else 0

    if progress_cb:
        progress_cb(100)

    return {
        "status": "done",
        "error": None,
        "person_count_avg": avg_persons,
        "movement_score": avg_movement,
        "activity_timeline": timeline,
        "duration_seconds": round(duration_sec, 1),
        "frames_processed": processed,
    }


def _simulate_video_analysis(video_path: str) -> dict:
    """
    Fallback when OpenCV is not installed.
    Generates realistic-looking random data so the rest of the app can be tested.
    """
    logger.info("Using simulated video analysis (OpenCV not available).")
    rng = np.random.default_rng(seed=42)
    timeline = [
        {"t": t * 60, "s": round(float(rng.uniform(40, 95)), 1)}
        for t in range(10)
    ]
    return {
        "status": "done",
        "error": None,
        "person_count_avg": round(float(rng.uniform(3, 8)), 1),
        "movement_score": round(float(rng.uniform(50, 85)), 1),
        "activity_timeline": timeline,
        "duration_seconds": 600.0,
        "frames_processed": 120,
        "note": "Simulated data – install opencv-python for real analysis.",
    }
