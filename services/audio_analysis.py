"""
services/audio_analysis.py
Optional, local-only audio activity detection.

What it does:
  - Splits audio into short chunks.
  - Computes RMS energy to identify speech-like activity vs. silence.
  - Returns active/quiet interval counts and a timeline.

What it does NOT do:
  - No speaker identification.
  - No transcription.
  - No emotion inference.
  - No cloud upload.

Requires: pydub, numpy.  Falls back gracefully if libraries are absent.
"""

import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logger.warning("pydub not installed – audio analysis will use a simulated fallback.")


SILENCE_THRESHOLD = 0.02   # RMS below this fraction of max = silence
CHUNK_MS = 5000             # 5-second chunks


def analyze_audio(audio_path: str, chunk_ms: int = CHUNK_MS,
                  silence_threshold: float = SILENCE_THRESHOLD) -> dict:
    """
    Analyse an audio file and return activity data.

    Returns:
        dict with audio_activity_pct, active_periods, quiet_periods,
        activity_timeline, duration_seconds, status, error
    """
    if not Path(audio_path).exists():
        return {"status": "failed", "error": "Audio file not found.", "audio_activity_pct": 0}

    if not PYDUB_AVAILABLE:
        return _simulate_audio_analysis()

    try:
        return _run_pydub_analysis(audio_path, chunk_ms, silence_threshold)
    except Exception as exc:
        logger.exception("Audio analysis error: %s", exc)
        return {"status": "failed", "error": str(exc), "audio_activity_pct": 0}


def _run_pydub_analysis(audio_path: str, chunk_ms: int,
                        silence_threshold: float) -> dict:
    audio = AudioSegment.from_file(audio_path)
    duration_ms = len(audio)
    duration_sec = duration_ms / 1000

    # Normalise to mono, 16-bit PCM for consistent RMS
    audio = audio.set_channels(1).set_sample_width(2)

    chunks = [audio[i: i + chunk_ms] for i in range(0, duration_ms, chunk_ms)]
    active_periods = 0
    quiet_periods = 0
    timeline = []

    for idx, chunk in enumerate(chunks):
        samples = np.array(chunk.get_array_of_samples(), dtype=np.float32)
        if len(samples) == 0:
            continue
        rms = float(np.sqrt(np.mean(samples ** 2)))
        max_rms = 32768.0   # 16-bit max
        normalised_rms = rms / max_rms

        is_active = normalised_rms > silence_threshold
        if is_active:
            active_periods += 1
        else:
            quiet_periods += 1

        t_sec = idx * (chunk_ms / 1000)
        activity_score = min(round(normalised_rms / silence_threshold * 50, 1), 100)
        timeline.append({"t": int(t_sec), "s": activity_score, "active": is_active})

    total = active_periods + quiet_periods
    activity_pct = round(active_periods / total * 100, 1) if total else 0

    return {
        "status": "done",
        "error": None,
        "audio_activity_pct": activity_pct,
        "active_periods": active_periods,
        "quiet_periods": quiet_periods,
        "activity_timeline": timeline,
        "duration_seconds": round(duration_sec, 1),
    }


def _simulate_audio_analysis() -> dict:
    """Fallback simulation when pydub is not available."""
    logger.info("Using simulated audio analysis (pydub not available).")
    rng = np.random.default_rng(seed=7)
    timeline = [
        {"t": t * 5, "s": round(float(rng.uniform(10, 95)), 1),
         "active": bool(rng.random() > 0.25)}
        for t in range(20)
    ]
    active = sum(1 for p in timeline if p["active"])
    quiet = len(timeline) - active
    pct = round(active / len(timeline) * 100, 1) if timeline else 0
    return {
        "status": "done",
        "error": None,
        "audio_activity_pct": pct,
        "active_periods": active,
        "quiet_periods": quiet,
        "activity_timeline": timeline,
        "duration_seconds": 100.0,
        "note": "Simulated data – install pydub for real analysis.",
    }
