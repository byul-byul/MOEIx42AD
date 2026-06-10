# /backend/app/agent/prosody.py
"""Audio prosody analysis — a real signal-processing pass over the raw
voice recording, complementing the transcript-based sentiment in
sentiment.py. A customer can say polite words in an agitated tone, or vice
versa; this module estimates loudness (RMS energy) and pitch (F0, via
autocorrelation) directly from the waveform and turns them into a coarse
"tone" label.

This is a heuristic, not a trained ML model — thresholds are tuned for a
single adult voice on a laptop/phone mic. See docs/DECISIONS.md for the
trade-off discussion (why not a full prosody/emotion model).

Decoding uses ffmpeg (already bundled in the image for Whisper) so any
browser-recorded format (webm/opus, ogg, mp4, ...) works without extra deps.
"""
import asyncio

import numpy as np

from app.core.logger import get_logger

logger = get_logger(__name__)

_TARGET_SR = 16000
_FRAME_MS = 40
_MIN_VOICED_FRAMES = 3

# Heuristic thresholds for a single adult voice on a laptop/phone mic.
_LOUD_RMS = 0.06
_QUIET_RMS = _LOUD_RMS * 0.4
_HIGH_PITCH_HZ = 200.0
_HIGH_PITCH_VARIANCE_HZ = 40.0

_VALID_TONES = {"agitated", "calm", "flat"}


async def analyze_prosody(audio_bytes: bytes) -> dict | None:
    """Best-effort prosody analysis. Returns None on any failure — never
    blocks the voice pipeline (same defensive pattern as sentiment.py)."""
    try:
        pcm = await _decode_to_pcm16(audio_bytes)
        samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        if samples.size < _TARGET_SR // 4:  # shorter than ~0.25s — too little signal
            return None

        rms = float(np.sqrt(np.mean(samples ** 2)))
        pitch_hz, pitch_std = _estimate_pitch(samples)
        tone = _classify_tone(rms, pitch_hz, pitch_std)

        return {
            "tone": tone,
            "rms": round(rms, 4),
            "pitch_hz": round(pitch_hz, 1),
            "pitch_std": round(pitch_std, 1),
        }
    except Exception as exc:
        logger.warning("Prosody analysis failed: %s", exc)
        return None


async def _decode_to_pcm16(audio_bytes: bytes) -> bytes:
    """Decode arbitrary audio bytes to 16kHz mono signed-16-bit PCM via ffmpeg."""
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i", "pipe:0",
        "-f", "s16le", "-ac", "1", "-ar", str(_TARGET_SR),
        "-loglevel", "error",
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=audio_bytes)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg decode failed: {stderr.decode(errors='ignore')[:200]}")
    return stdout


def _estimate_pitch(samples: np.ndarray) -> tuple[float, float]:
    """Frame-wise autocorrelation pitch (F0) estimate over the human voice
    range (80-400 Hz). Returns (mean_hz, std_hz) across voiced frames."""
    frame_len = int(_TARGET_SR * _FRAME_MS / 1000)
    hop = frame_len // 2
    min_lag = _TARGET_SR // 400  # 400 Hz upper bound
    max_lag = _TARGET_SR // 80   # 80 Hz lower bound

    pitches = []
    for start in range(0, len(samples) - frame_len, hop):
        frame = samples[start:start + frame_len]
        if np.max(np.abs(frame)) < 0.01:  # silence — skip
            continue

        frame = frame - np.mean(frame)
        corr = np.correlate(frame, frame, mode="full")[len(frame) - 1:]
        if corr[0] <= 0 or max_lag >= len(corr):
            continue

        segment = corr[min_lag:max_lag]
        if segment.size == 0:
            continue

        peak_lag = int(np.argmax(segment)) + min_lag
        confidence = corr[peak_lag] / corr[0]
        if confidence < 0.3:  # not periodic enough — likely unvoiced
            continue

        pitches.append(_TARGET_SR / peak_lag)

    if len(pitches) < _MIN_VOICED_FRAMES:
        return 0.0, 0.0

    arr = np.array(pitches)
    return float(np.mean(arr)), float(np.std(arr))


def _classify_tone(rms: float, pitch_hz: float, pitch_std: float) -> str:
    """Map loudness + pitch stats to a coarse tone label."""
    if pitch_hz == 0.0:
        return "flat"
    if rms >= _LOUD_RMS and (pitch_hz >= _HIGH_PITCH_HZ or pitch_std >= _HIGH_PITCH_VARIANCE_HZ):
        return "agitated"
    if rms < _QUIET_RMS and pitch_std < _HIGH_PITCH_VARIANCE_HZ * 0.5:
        return "flat"
    return "calm"
