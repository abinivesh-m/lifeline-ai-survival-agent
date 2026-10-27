"""LIFELINE AI - step 2, LISTEN. Real Muse Voice Transcribe over Tamil audio.

    python capture_voice.py                       # every wav in artifacts/audio
    python capture_voice.py --file artifacts/audio/report_01.wav

Contract (dev.meta.ai/docs/speech-to-text):
  * POST {META_API_BASE}/asr/transcribe   (NOT /audio/transcriptions)
  * multipart/form-data with two parts:
        request : JSON settings
        audio   : RIFF/WAVE, mono, 16-bit PCM, 16 kHz or 24 kHz
  * languageBias takes a list of language NAMES ("Tamil", "English")
  * keywords bias recognition toward domain vocabulary

Writes artifacts/voice_reports.json, which agent.py step 2 consumes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path

import allocator

ROOT = Path(__file__).parent
AUDIO = ROOT / "artifacts" / "audio"
OUT = ROOT / "artifacts" / "voice_reports.json"

MODEL = "muse-voice-transcribe-1.0"
COST_PER_HOUR_USD = 0.18

# Domain vocabulary the model would otherwise mishear.
KEYWORDS = [
    "NH-544", "km 42", "Kottur", "Pollachi", "landslide",
    "diesel", "hospital", "water pump", "shelter",
]


def _wav_shape(path: Path) -> dict:
    with wave.open(str(path), "rb") as wav:
        return {
            "channels": wav.getnchannels(),
            "sample_rate_hz": wav.getframerate(),
            "sample_width_bytes": wav.getsampwidth(),
            "frames": wav.getnframes(),
            "seconds": round(wav.getnframes() / wav.getframerate(), 2),
        }


def transcribe(path: Path, timeout: float = 120.0) -> dict:
    audio = path.read_bytes()
    settings = {
        "model": MODEL,
        "mode": "PUSH_TO_TALK",
        "audioEncoding": "WAV",
        "languageBias": ["Tamil", "English"],
        "keywords": KEYWORDS,
    }
    boundary = f"----lifeline{uuid.uuid4().hex}"
    body = b""
    body += (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="request"\r\n'
        f"Content-Type: application/json\r\n\r\n"
        f"{json.dumps(settings)}\r\n"
    ).encode()
    body += (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="audio"; filename="{path.name}"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode()
    body += audio + b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    url = os.environ["META_API_BASE"].rstrip("/") + f"/asr/transcribe?sessionId=lifeline-{uuid.uuid4().hex[:12]}"
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Authorization": f"Bearer {os.environ['META_API_KEY']}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode())


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Muse Voice Transcribe capture")
    parser.add_argument("--audio", default=str(AUDIO))
    parser.add_argument("--file", default=None)
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--log-credit", action="store_true")
    args = parser.parse_args(argv)

    allocator.load_env()
    if not os.environ.get("META_API_KEY"):
        print("META_API_KEY missing", file=sys.stderr)
        return 2

    files = [Path(args.file)] if args.file else sorted(Path(args.audio).glob("*.wav"))
    if not files:
        print(f"no wav files in {args.audio}", file=sys.stderr)
        return 2

    print(f"Muse Voice Transcribe  model={MODEL}  files={len(files)}\n")
    reports, failures, seconds = [], [], 0.0
    for path in files:
        try:
            shape = _wav_shape(path)
            result = transcribe(path)
            seconds += shape["seconds"]
            reports.append({
                "file": path.name,
                "transcript": result.get("transcript", ""),
                "audio_duration_ms": result.get("audioDurationMs"),
                "turns": result.get("turns", []),
                "audio": shape,
                "language_bias": ["Tamil", "English"],
                "keywords": KEYWORDS,
                "synthetic": path.stem.startswith("report_") and os.environ.get("LIFELINE_TTS") == "1",
            })
            print(f"  {path.name}: {result.get('transcript', '')!r}")
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:300].decode(errors="replace")
            failures.append({"file": path.name, "status": exc.code, "detail": detail})
            print(f"  {path.name}: HTTP {exc.code} {detail[:120]}")
        except Exception as exc:
            failures.append({"file": path.name, "error": f"{type(exc).__name__}: {exc}"})
            print(f"  {path.name}: {type(exc).__name__}: {exc}")

    if not reports:
        print("\nno transcripts - artifact not written", file=sys.stderr)
        return 1

    artifact = {
        "schema": "lifeline.voice_reports/1.0",
        "captured_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": MODEL,
        "endpoint": "/asr/transcribe",
        "mode": "PUSH_TO_TALK",
        "audio_seconds": round(seconds, 2),
        "cost_usd": round(seconds / 3600 * COST_PER_HOUR_USD, 6),
        "reports": reports,
        "failures": failures,
        "note": (
            "Placeholder audio synthesised with edge-tts (ta-IN-ValluvarNeural) because "
            "this machine has no Tamil voice installed. It is labelled synthetic in each "
            "report. Replace artifacts/audio/report_01.wav with a real field recording and "
            "re-run - nothing else changes."
        ),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out.relative_to(ROOT)}  ({len(reports)} reports, {seconds:.1f}s audio)")

    if args.log_credit:
        import credit_tracker
        try:
            entry = credit_tracker.CreditTracker().log(
                "voice", calls=len(reports), cost=max(seconds / 3600 * COST_PER_HOUR_USD, 0.0001),
                note=f"Muse Voice Transcribe, {len(reports)} report(s), {seconds:.1f}s",
            )
            print(f"credit logged: ${entry['cost_usd']:.6f}")
        except Exception as exc:
            print(f"credit log failed: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
