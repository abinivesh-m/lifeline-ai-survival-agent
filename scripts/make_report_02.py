"""The second field report, rendered locally so the loop has something to act on.

    python scripts/make_report_02.py

The first report (report_01.wav) is a real capture of the incident and it only
confirms what town.json already says: km 42 is closed for six hours. That is the
honest "no change" case, and it is worth keeping - an agent that changes its plan
on every phone call is not trustworthy.

The loop still needs a report that *does* change the plan, so this clip is the
one a shelter volunteer would call in next: the village road is under water and
the tanker cannot reach the pump. It is synthesised with MMS-TTS on CPU, labelled
synthetic in the artefact by capture_voice.py, and must be replaced by a real
recording before anyone claims it is one.
"""

from __future__ import annotations

import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import voice_synth  # noqa: E402

TEXT = "கிராமச் சாலை வெள்ளத்தில் அடித்துச் செல்லப்பட்டது. டேங்கர் வண்டி பம்பை அடைய முடியாது."
OUT = ROOT / "artifacts" / "audio" / "report_02.wav"
PAD_S = 0.4


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
    print(f'text: "{TEXT}"')
    print("synthetic clip - label it as such, and replace it with a real recording")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
