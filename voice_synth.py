"""Speak the model-drafted alerts with MMS-TTS, an open-weight voice, on CPU.

Why this file exists
--------------------
The Meta API publishes Wonder, Spark, SAM, Voice Transcribe and Image. It does
not publish a text-to-speech endpoint - so calling ``/v1/tts`` would be a lie.

The product still needs sound: a reader who cannot read an SMS is not served by
a text ladder. So the model writes the words (``multilingual.py``) and this file
turns those words into audio with **MMS-TTS** (``facebook/mms-tts-*``), an
open-weight model that runs on this laptop's CPU with no network, no API key and
no credits. It is the same pattern as the Baseten open-weight brain: a real
model, honestly labelled, not a mock.

Two clips per locale, because the ladder needs two different sentences:
    tier2_<code>.wav       the tier-2 alert, spoken (SMS read aloud)
    allocation_<code>.wav  the 70/30 split, spoken (the "what was decided" reply)

Every clip is keyed to the text it speaks: ``text_sha256`` makes a stale clip
detectable, and the UI refuses to play audio for a different allocation.

Run:
    python voice_synth.py                 # all locales in the artefact
    python voice_synth.py --locales ta,en
    python voice_synth.py --verify        # no model load, just hashes and files
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
ARTIFACT = ROOT / "artifacts" / "multilingual_payloads.json"
OUT_DIR = ROOT / "artifacts" / "audio" / "voice"
MANIFEST = ROOT / "artifacts" / "voice_synth.json"

ENGINE = "MMS-TTS"
LICENCE = "CC-BY-NC 4.0 (facebook/mms-tts)"
SAMPLE_RATE = 16000

# One checkpoint per locale. MMS-TTS is VITS: small, CPU-friendly, 16 kHz.
# Mandarin has no checkpoint in the released MMS-TTS set, so zh stays silent
# and the manifest says why - a Min Nan or wrong-language voice would be worse.
VOICES = {
    "en": "facebook/mms-tts-eng",
    "es": "facebook/mms-tts-spa",
    "fr": "facebook/mms-tts-fra",
    "ar": "facebook/mms-tts-ara",
    "pt": "facebook/mms-tts-por",
    "sw": "facebook/mms-tts-swh",
    "ta": "facebook/mms-tts-tam",
}

UNAVAILABLE = {
    "zh": "no Mandarin checkpoint in the released MMS-TTS set (facebook/mms-tts-cmn returns 401)",
}

CLIPS = {
    "tier2": ("voice", "script"),
    "allocation": ("allocation", "script"),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def read_artifact() -> dict:
    if not ARTIFACT.exists():
        raise SystemExit(
            "artifacts/multilingual_payloads.json missing - run python multilingual.py first"
        )
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def _load(code: str):
    """Load one MMS-TTS checkpoint. Imported lazily so --verify stays offline."""
    import torch  # noqa: F401  (imported for its side effect: registers backends)
    from transformers import AutoTokenizer, VitsModel

    name = VOICES[code]
    tokenizer = AutoTokenizer.from_pretrained(name)
    model = VitsModel.from_pretrained(name)
    model.eval()
    return tokenizer, model


def _speak(tokenizer, model, text: str) -> tuple[list[int], float]:
    import torch

    started = time.time()
    inputs = tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        waveform = model(**inputs).waveform
    audio = waveform.squeeze(0).numpy()
    # Clip to [-1, 1] before int16 conversion; a VITS tail can overshoot.
    audio = audio.clip(-1.0, 1.0)
    return (audio * 32767).astype("int16").tolist(), round(time.time() - started, 2)


def _write_wav(path: Path, samples: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(SAMPLE_RATE)
        out.writeframes(b"".join(int(s).to_bytes(2, "little", signed=True) for s in samples))


def synth(locales: list[str] | None = None) -> dict:
    data = read_artifact()
    records = data.get("locales", [])
    codes = locales or [record["locale"] for record in records]
    by_code = {record["locale"]: record for record in records}

    clips: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    started_all = time.time()

    for code in codes:
        record = by_code.get(code)
        if record is None:
            print(f"  {code}: not in the artefact, skipped")
            skipped.append({"locale": code, "reason": "not in the payload artefact"})
            continue
        if code in UNAVAILABLE:
            print(f"  {code}: {UNAVAILABLE[code]}")
            skipped.append({"locale": code, "reason": UNAVAILABLE[code]})
            continue
        if code not in VOICES:
            print(f"  {code}: no MMS-TTS checkpoint mapped, skipped")
            skipped.append({"locale": code, "reason": "no checkpoint mapped"})
            continue

        pending = []
        for clip, (kind, field) in CLIPS.items():
            payload = record.get(kind) or {}
            if not payload.get("valid"):
                print(f"  {code}/{clip}: no validated {kind} payload - skipped")
                continue
            text = (payload.get(field) or "").strip()
            if text:
                pending.append((clip, kind, text))

        if not pending:
            continue

        try:
            print(f"  {code}: loading {VOICES[code]}")
            tokenizer, model = _load(code)
        except Exception as exc:  # network, gated repo, disk - never abort the batch
            print(f"  {code}: load failed: {type(exc).__name__}: {exc}")
            skipped.append({"locale": code, "reason": f"load failed: {type(exc).__name__}"})
            continue

        for clip, kind, text in pending:
            try:
                samples, seconds = _speak(tokenizer, model, text)
            except Exception as exc:
                print(f"  {code}/{clip}: synth failed: {type(exc).__name__}: {exc}")
                skipped.append(
                    {"locale": code, "clip": clip, "reason": f"synth failed: {type(exc).__name__}"}
                )
                continue
            path = OUT_DIR / f"{clip}_{code}.wav"
            _write_wav(path, samples)
            duration = round(len(samples) / SAMPLE_RATE, 2)
            clips.append(
                {
                    "file": path.relative_to(ROOT).as_posix(),
                    "locale": code,
                    "clip": clip,
                    "kind": kind,
                    "model": VOICES[code],
                    "text": text,
                    "text_sha256": sha256_text(text),
                    "chars": len(text),
                    "seconds": duration,
                    "bytes": path.stat().st_size,
                    "synth_s": seconds,
                    "sample_rate": SAMPLE_RATE,
                    "channels": 1,
                    "synthetic": True,
                }
            )
            print(
                f"    {clip}_{code}.wav  {duration:5.1f}s  "
                f"{path.stat().st_size // 1024:4d} KB  synth {seconds:5.1f}s"
            )
        del model, tokenizer

    if locales and MANIFEST.exists():
        # A partial re-render must not delete the clips it did not touch.
        previous = json.loads(MANIFEST.read_text(encoding="utf-8"))
        touched = set(codes)
        kept = [clip for clip in previous.get("clips", []) if clip["locale"] not in touched]
        skipped = [
            item for item in previous.get("skipped", []) if item.get("locale") not in touched
        ] + skipped
        clips = sorted(kept + clips, key=lambda c: (c["locale"], c["clip"]))

    manifest = {
        "schema": "lifeline.voice_synth/1.0",
        "generated_utc": _now(),
        "engine": {
            "name": ENGINE,
            "licence": LICENCE,
            "device": "cpu",
            "sample_rate_hz": SAMPLE_RATE,
            "runs_locally": True,
            "network_at_playback": False,
            "cost_usd": 0.0,
            "checkpoints": VOICES,
        },
        "source_artifact": ARTIFACT.name,
        "source_generated_utc": data.get("generated_utc"),
        "totals": {
            "clips": len(clips),
            "locales": len({clip["locale"] for clip in clips}),
            "seconds": round(sum(clip["seconds"] for clip in clips), 2),
            "bytes": sum(clip["bytes"] for clip in clips),
            "synth_s": round(time.time() - started_all, 1),
        },
        "skipped": skipped,
        "clips": clips,
        "note": (
            "Synthetic speech, not a human recording. MMS-TTS is an open-weight "
            "model run on this laptop; the words are the model-drafted, "
            "code-validated payloads from multilingual_payloads.json. The Meta "
            "API has no TTS endpoint, so no Meta credits are spent here - and "
            "this file never claims otherwise. A locale with no released "
            "checkpoint ships text-only rather than in the wrong language."
        ),
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def verify() -> list[str]:
    """Check every clip against the text it claims to speak. No model load."""
    problems: list[str] = []
    if not MANIFEST.exists():
        return ["no manifest - run python voice_synth.py"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    data = read_artifact()
    by_code = {record["locale"]: record for record in data.get("locales", [])}

    for clip in manifest.get("clips", []):
        path = ROOT / clip["file"]
        if not path.exists():
            problems.append(f"{clip['file']}: missing")
            continue
        if path.stat().st_size != clip["bytes"]:
            problems.append(f"{clip['file']}: size drift")
        record = by_code.get(clip["locale"], {})
        payload = record.get(clip["kind"], {})
        field = CLIPS[clip["clip"]][1]
        current = (payload.get(field) or "").strip()
        if sha256_text(current) != clip["text_sha256"]:
            problems.append(
                f"{clip['file']}: speaks stale text - re-run voice_synth.py"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Render spoken alerts with MMS-TTS")
    parser.add_argument("--locales", help="comma separated codes, default all")
    parser.add_argument("--verify", action="store_true", help="check clips against the text")
    parser.add_argument("--log-credit", action="store_true", default=True)
    args = parser.parse_args(argv)

    if args.verify:
        problems = verify()
        for problem in problems:
            print(f"  FAIL {problem}")
        print(f"  {len(problems)} problem(s)" if problems else "  clips verified")
        return 1 if problems else 0

    codes = [code.strip() for code in args.locales.split(",")] if args.locales else None
    manifest = synth(codes)
    totals = manifest["totals"]
    print(
        f"\n  {totals['clips']} clips / {totals['locales']} locales · "
        f"{totals['seconds']}s of audio · {totals['bytes'] // 1024} KB · "
        f"{totals['synth_s']}s of CPU"
    )
    print(f"  engine {manifest['engine']['name']} (open weight, local, $0.00)")
    print(f"  wrote {MANIFEST.relative_to(ROOT)}")

    if args.log_credit and totals["clips"]:
        import credit_tracker

        entry = credit_tracker.CreditTracker().log(
            "voice_synth",
            calls=totals["clips"],
            note=f"MMS-TTS local synthesis, {totals['clips']} clips, {totals['seconds']}s, $0",
        )
        print(f"  ledger row: voice_synth {entry['calls']} calls ${entry['cost_usd']:.2f}")

    return 0 if totals["clips"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
