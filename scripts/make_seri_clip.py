"""One word, rendered locally: the clip the Seri Gate listens to.

    python scripts/make_seri_clip.py

Writes artifacts/audio/seri.wav (16 kHz mono). Synthetic by construction and
labelled as such; replace it with a real recording of a person saying "சரி".

Why the phrase is not the bare word: a 0.38 s "சரி" is below what the
transcriber can resolve (it returned "The"). "சரி, அனுமதிக்கிறேன்." - "yes, I
approve" - survives the round trip, and the gate still keys on the சரி token.
"""

from __future__ import annotations

import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import voice_synth  # noqa: E402

TEXT = "சரி, அனுமதிக்கிறேன்."
OUT = ROOT / "artifacts" / "audio" / "seri.wav"
PAD_S = 0.5


def main() -> int:
    tokenizer, model = voice_synth._load("ta")
    samples, seconds = voice_synth._speak(tokenizer, model, TEXT)
    silence = [0] * int(voice_synth.SAMPLE_RATE * PAD_S)
    samples = silence + samples + silence
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(voice_synth.SAMPLE_RATE)
        handle.writeframes(b"".join(int(s).to_bytes(2, "little", signed=True) for s in samples))
    print(f"wrote {OUT.relative_to(ROOT)}  {len(samples) / voice_synth.SAMPLE_RATE:.2f}s  "
          f"{OUT.stat().st_size // 1024} KB  ({seconds:.1f}s synth, {voice_synth.VOICES['ta']})")
    print("synthetic clip - replace with a real recording when you have one")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
