"""SERI GATE - one spoken word approves the dispatch, in the reader's language.

The problem it solves
---------------------
The paper QR needs a reader. The temple bell needs a listener who knows the
code. An elder who cannot read either is still the person the town trusts to
say yes. Tamil "சரி", Spanish "sí", Swahili "ndiyo" - one word is enough.

The gate, end to end
--------------------
1. VOICE   an open-weight MMS-TTS clip says the approval phrase, rendered here.
2. EARS    muse-voice-transcribe-1.0 transcribes it.
3. MEANING muse-wonder-1.0 classifies the transcript as APPROVE / DENY / UNCLEAR.
4. CODE    this file decides. Approval requires a known approval token *and*
           an agreeing model *and* confidence >= 0.80. Anything else is a no.
5. RECORD  the decision is appended to the hash-chained escalation ledger with
           the audio's sha256, so the word and the record cannot drift apart.

The model never gets the last word: a misheard "no" must never dispatch fuel.
The model's opinion is one input, and the per-language token matcher is the
other. Mandarin has no released MMS-TTS checkpoint, so zh is listed as
text-only rather than spoken in the wrong language.

Run:
    python seri_gate.py                      # every spoken locale (7)
    python seri_gate.py --locale ta          # one locale
    python seri_gate.py --transcript "சரி"   # skip audio/ASR, test the gate
    python seri_gate.py --locale en --file my-recording.wav
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import allocator
import capture_voice
import credit_tracker
import escalation
import i18n
import multilingual

ROOT = Path(__file__).parent
AUDIO = ROOT / "artifacts" / "audio"
ARTIFACT = ROOT / "artifacts" / "seri_gate.json"
THRESHOLD = 0.80
PAD_S = 0.5

# One natural approval sentence per spoken locale. The phrase must contain a
# token from ``approve`` - that is what the deterministic matcher keys on.
LOCALES: dict[str, dict] = {
    "ta": {
        "native": "தமிழ்",
        "language": "Tamil",
        "phrase": "சரி, அனுமதிக்கிறேன்.",
        "bias": ["Tamil", "English"],
        # Tamil speakers code-switch, so Voice Transcribe returns "sari", "ok"
        # and "not ok" from the same speaker. The English words ride along in
        # the Tamil vocabulary. Denial still wins and a negation before an
        # approval word is a denial, so "not ok" can never dispatch fuel.
        "approve": ("சரி", "ஆம்", "ஒப்பு", "seri", "sari", "aam", "ok", "okay", "yes"),
        "deny": ("சரியில்லை", "இல்லை", "வேண்டாம்", "illai", "vendaam", "no", "nope", "never"),
        "negations": ("not", "no", "never"),
    },
    "en": {
        "native": "English",
        "language": "English",
        "phrase": "Yes, I approve.",
        "bias": ["English"],
        "approve": ("yes", "ok", "okay", "approve", "approved", "yep", "yeah"),
        "deny": ("no", "nope", "never", "deny", "reject"),
        "negations": ("not", "no", "never", "don't", "dont"),
    },
    "es": {
        "native": "Español",
        "language": "Spanish",
        "phrase": "Sí, apruebo.",
        "bias": ["Español"],
        "approve": ("sí", "si", "claro", "apruebo", "vale", "yes", "ok"),
        "deny": ("no", "nunca", "niego", "rechazo"),
        "negations": ("no", "nunca"),
    },
    "fr": {
        "native": "Français",
        "language": "French",
        "phrase": "Oui, j'approuve.",
        "bias": ["Français"],
        "approve": ("oui", "approuve", "accord", "ok"),
        "deny": ("non", "jamais", "refuse"),
        "negations": ("ne", "pas", "jamais"),
    },
    "ar": {
        "native": "العربية",
        "language": "Arabic",
        "phrase": "نعم، أوافق.",
        "bias": ["العربية"],
        "approve": ("نعم", "أوافق", "أوفقوا", "اوفق", "اوفقوا", "موافق", "تمام"),
        "deny": ("لا", "رفض", "ارفض"),
        "negations": ("لا",),
    },
    "pt": {
        "native": "Português",
        "language": "Portuguese",
        "phrase": "Sim, aprovo.",
        "bias": ["Português"],
        "approve": ("sim", "aprovo", "claro", "ok"),
        "deny": ("não", "nao", "nunca", "recuso"),
        "negations": ("não", "nao", "nunca"),
    },
    "sw": {
        "native": "Kiswahili",
        "language": "Swahili",
        "phrase": "Ndiyo, nakubali.",
        "bias": ["Kiswahili"],
        "approve": ("ndiyo", "ndio", "nakubali", "kubali", "sawa"),
        "deny": ("hapana", "siwezi", "kataa"),
        "negations": ("si", "hapana"),
    },
}

# No released MMS-TTS checkpoint, so the gate cannot listen in Mandarin. The
# page says so instead of shipping a Min Nan or English voice for a zh reader.
TEXT_ONLY = {"zh": "no released MMS-TTS checkpoint - text-only, not spoken"}

# Voice Transcribe code-switches and sometimes glues scripts together
# ("sariசரி"). Splitting at script boundaries recovers whole words. It does NOT
# turn "சரியில்லை" ("it is not OK") into approval: that stays one Tamil token.
SCRIPT_RUN = re.compile(
    r"[a-z\u00c0-\u00ff]+|[\u0b80-\u0bff]+|[\u0600-\u06ff]+|[\u4e00-\u9fff]+"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _spec(locale: str) -> dict:
    return LOCALES.get(locale, LOCALES["ta"])


def _collapse(word: str, locale: str) -> str:
    """Undo an ASR stutter: an exact doubling of one known token.

    "சரிசரி" and "sarisari" are the transcriber echoing the same word. Only an
    exact ``token + token`` collapses, so "சரியில்லை" and "Ansari" survive.
    """
    spec = _spec(locale)
    for token in spec["approve"] + spec["deny"]:
        if word == token + token:
            return token
    return word


def token_intent(transcript: str, locale: str = "ta") -> str:
    """Deterministic first pass, in one language's vocabulary.

    Denial wins over approval, and a negation immediately before an approval
    word ("not ok") is a denial. Silence, a cough, a question: UNCLEAR.
    """
    spec = _spec(locale)
    words = [
        _collapse(word, locale)
        for word in SCRIPT_RUN.findall((transcript or "").lower())
    ]
    if any(token in words for token in spec["deny"]):
        return "DENY"
    for index, word in enumerate(words):
        if word in spec["approve"]:
            if index and words[index - 1] in spec["negations"]:
                return "DENY"
            return "APPROVE"
    return "UNCLEAR"


def decide(transcript: str, model: dict, locale: str = "ta") -> dict:
    """The gate. Code has the last word, and the default is no."""
    token = token_intent(transcript, locale)
    intent = str(model.get("intent", "UNCLEAR")).upper()
    confidence = float(model.get("confidence") or 0.0)
    reasons = []

    if token == "UNCLEAR":
        reasons.append("no approval or denial token in the transcript")
    if model.get("status") != "answered":
        reasons.append(f"intent model unavailable ({model.get('status')})")
    if intent != token:
        reasons.append(f"model said {intent}, the words said {token}")
    if intent != "APPROVE":
        reasons.append(f"intent is {intent}, only APPROVE dispatches")
    if confidence < THRESHOLD:
        reasons.append(f"confidence {confidence:.2f} below {THRESHOLD:.2f}")

    approved = not reasons
    return {
        "decision": "APPROVED" if approved else "WITHHELD",
        "approved": approved,
        "locale": locale,
        "token_intent": token,
        "model_intent": intent,
        "confidence": confidence,
        "threshold": THRESHOLD,
        "reasons": reasons,
        "rule": "approval needs an approval token, an agreeing model and confidence >= 0.80",
    }


def intent_prompt(transcript: str, locale: str) -> str:
    spec = _spec(locale)
    return (
        "A caller heard a spoken answer to: 'Approve 70 litres to the hospital "
        "and 30 litres to the water pump?'\n"
        f'TRANSCRIPT: """{transcript}"""\n\n'
        f"The expected language is {spec['language']}. Words that mean APPROVE "
        f"include: {', '.join(spec['approve'])}. Words that mean DENY include: "
        f"{', '.join(spec['deny'])}. Anything else, including a question, a "
        "cough or an unclear word, is UNCLEAR. Never guess.\n\n"
        'Reply as JSON only: {"intent": "APPROVE"|"DENY"|"UNCLEAR", '
        '"confidence": <0-1>, "reason": "<short reason>"}'
    )


def classify(transcript: str, locale: str = "ta") -> dict:
    """Ask Wonder for an intent. Never raises; returns a status the gate reads."""
    if os.environ.get("LIFELINE_OFFLINE", "0") == "1":
        return {"status": "unavailable", "detail": "LIFELINE_OFFLINE=1"}
    reply = multilingual._meta_chat(
        os.environ.get("META_MODEL", "muse-wonder-1.0"),
        intent_prompt(transcript, locale),
        timeout=60.0,
        max_tokens=3000,
        reasoning_effort="low",
    )
    parsed = multilingual._parse_json(reply.get("text"))
    return {
        "status": reply["status"],
        "detail": reply.get("detail", ""),
        "latency_s": reply.get("latency_s"),
        "usage": reply.get("usage"),
        "intent": parsed.get("intent"),
        "confidence": parsed.get("confidence"),
        "reason": str(parsed.get("reason", ""))[:200],
    }


def render_clip(locale: str, path: Path | None = None) -> Path:
    """Speak the approval phrase with MMS-TTS, locally, at zero credit cost."""
    import voice_synth  # torch stays out of the import path until it is needed

    spec = _spec(locale)
    if locale not in voice_synth.VOICES:
        raise RuntimeError(TEXT_ONLY.get(locale, "no MMS-TTS checkpoint for this locale"))
    out = path or AUDIO / f"seri_{locale}.wav"
    tokenizer, model = voice_synth._load(locale)
    samples, _ = voice_synth._speak(tokenizer, model, spec["phrase"])
    silence = [0] * int(voice_synth.SAMPLE_RATE * PAD_S)
    out.parent.mkdir(parents=True, exist_ok=True)
    voice_synth._write_wav(out, silence + samples + silence)
    return out


def run_locale(
    locale: str,
    path: Path | None = None,
    transcript: str | None = None,
    tracker: credit_tracker.CreditTracker | None = None,
) -> dict:
    """One locale: clip -> ASR -> intent -> code gate -> ledger."""
    spec = _spec(locale)
    own = tracker is None
    tracker = tracker or credit_tracker.CreditTracker()
    before_voice = tracker.spend_precise("voice")
    before_wonder = tracker.spend_precise("wonder")

    clip = path or AUDIO / f"seri_{locale}.wav"
    audio_sha = None
    audio_seconds = None
    asr = {"status": "skipped", "model": capture_voice.MODEL}

    if transcript is None:
        if not clip.exists():
            render_clip(locale, clip)
        shape = capture_voice._wav_shape(clip)
        audio_seconds = shape["seconds"]
        audio_sha = hashlib.sha256(clip.read_bytes()).hexdigest()
        started = time.time()
        # The transcriber wants each language's own name ("Español", not
        # "Spanish"). With the English name it phonetically transliterated a
        # clear "Sí, apruebo" into "Siapolevo" - which the gate then, correctly,
        # withheld. Bias is per locale and recorded in the artefact.
        result = capture_voice.transcribe(clip, languages=spec["bias"])
        transcript = (result.get("transcript") or "").strip()
        asr = {
            "status": "answered" if transcript else "empty",
            "model": capture_voice.MODEL,
            "latency_s": round(time.time() - started, 2),
            "language_bias": spec["bias"],
        }
        tracker.log(
            "voice",
            calls=1,
            cost=max(audio_seconds / 3600 * capture_voice.COST_PER_HOUR_USD, 0.0001),
            note=f"SERI GATE {locale} asr, {audio_seconds:.1f}s",
        )
    else:
        asr["status"] = "bypassed"

    model = classify(transcript or "", locale)
    if model.get("usage"):
        tracker.log("wonder", calls=1, note=f"SERI GATE {locale} intent ({model.get('intent')})")

    verdict = decide(transcript or "", model, locale)

    ledger_entry = None
    if verdict["approved"]:
        ledger_entry = escalation.HashLedger().append(
            tier=1,
            action="VOICE_APPROVAL",
            detail={
                "locale": locale,
                "transcript": transcript,
                "audio_sha256": audio_sha,
                "intent": verdict["model_intent"],
                "confidence": verdict["confidence"],
                "model": os.environ.get("META_MODEL", "muse-wonder-1.0"),
                "asr_model": asr["model"],
            },
        )

    return {
        "locale": locale,
        "native": spec["native"],
        "language": spec["language"],
        "phrase": spec["phrase"],
        "audio": {
            "file": (
                str(clip.relative_to(ROOT)) if Path(clip).is_relative_to(ROOT) else str(clip)
            ),
            "sha256": audio_sha,
            "seconds": audio_seconds,
        },
        "asr": asr,
        "transcript": transcript,
        "model": {
            key: model.get(key)
            for key in ("status", "intent", "confidence", "reason", "latency_s")
        },
        "gate": verdict,
        "ledger": ledger_entry,
        "cost_usd": round(
            (tracker.spend_precise("voice") - before_voice)
            + (tracker.spend_precise("wonder") - before_wonder),
            6,
        ),
    }


def run(locales: list[str] | None = None) -> dict:
    """Run the gate for every spoken locale and write one batch artefact."""
    allocator.load_env()
    tracker = credit_tracker.CreditTracker()
    order = [entry["code"] for entry in i18n.available()]
    codes = locales or [code for code in order if code in LOCALES]

    entries: list[dict] = []
    for code in codes:
        try:
            entry = run_locale(code, tracker=tracker)
        except Exception as exc:  # a missing clip or a dead API must not hide the rest
            entry = {
                "locale": code,
                "native": _spec(code)["native"],
                "language": _spec(code)["language"],
                "phrase": _spec(code)["phrase"],
                "audio": {"file": None, "sha256": None, "seconds": None},
                "asr": {"status": "unavailable", "model": capture_voice.MODEL},
                "transcript": None,
                "model": {"status": "unavailable", "intent": None, "confidence": 0},
                "gate": {
                    "decision": "WITHHELD",
                    "approved": False,
                    "locale": code,
                    "token_intent": "UNCLEAR",
                    "model_intent": "UNCLEAR",
                    "confidence": 0.0,
                    "threshold": THRESHOLD,
                    "reasons": [f"{type(exc).__name__}: {exc}"],
                    "rule": "a run that did not happen cannot approve fuel",
                },
                "ledger": None,
                "cost_usd": 0.0,
            }
        entries.append(entry)
        print(
            f"  {code}: {entry['gate']['decision']:<9}"
            f" token={entry['gate']['token_intent']:<9}"
            f" model={entry['gate']['model_intent']:<9}"
            f" {entry['gate']['confidence']:.2f}"
            f"  {entry['transcript']!r}"
        )

    approved = sum(1 for entry in entries if entry["gate"]["approved"])
    artifact = {
        "schema": "lifeline.seri_gate/1.1",
        "generated_utc": _now(),
        "engine": {
            "tts": "MMS-TTS (open weight, local CPU, $0.00)",
            "asr": capture_voice.MODEL,
            "intent": os.environ.get("META_MODEL", "muse-wonder-1.0"),
            "threshold": THRESHOLD,
        },
        "summary": {
            "languages": len(entries),
            "spoken": sum(1 for entry in entries if entry["audio"]["sha256"]),
            "approved": approved,
            "withheld": len(entries) - approved,
            "text_only": TEXT_ONLY,
        },
        "locales": entries,
        "note": (
            "Voice approval, not delivery. Each clip is rendered locally by "
            "MMS-TTS, transcribed by Muse Voice Transcribe, classified by Muse "
            "Wonder, and decided in code. Nothing is dispatched - there is no "
            "gateway on this machine. A locale that cannot be heard is text-only "
            "rather than spoken in the wrong language."
        ),
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return artifact


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Spoken approval gate, every language")
    parser.add_argument("--locale", default=None, help="one locale (default: every spoken locale)")
    parser.add_argument("--file", default=None, help="a real recording for that locale")
    parser.add_argument("--transcript", default=None, help="skip audio/ASR and test the gate")
    args = parser.parse_args(argv)

    if args.transcript is not None:
        locale = args.locale or "ta"
        entry = run_locale(locale, Path(args.file) if args.file else None, args.transcript)
        artifact = {
            "schema": "lifeline.seri_gate/1.1",
            "generated_utc": _now(),
            "engine": {"tts": "skipped", "asr": capture_voice.MODEL,
                       "intent": os.environ.get("META_MODEL", "muse-wonder-1.0"),
                       "threshold": THRESHOLD},
            "summary": {"languages": 1, "spoken": 0,
                        "approved": int(entry["gate"]["approved"]),
                        "withheld": int(not entry["gate"]["approved"]),
                        "text_only": TEXT_ONLY},
            "locales": [entry],
            "note": "Gate tested with a supplied transcript; no audio was heard.",
        }
        ARTIFACT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        artifact = run([args.locale] if args.locale else None)

    summary = artifact["summary"]
    print(
        f"\n  {summary['approved']}/{summary['languages']} approved · "
        f"{summary['withheld']} withheld · {summary['spoken']} spoken clips"
    )
    for entry in artifact["locales"]:
        if entry["ledger"]:
            print(
                f"  ledger {entry['locale']}: seq {entry['ledger']['seq']} · "
                f"{entry['ledger']['hash'][:16]}..."
            )
    total = round(sum(entry.get("cost_usd", 0.0) for entry in artifact["locales"]), 6)
    print(f"  cost ${total:.6f} · artifact {ARTIFACT.name}")
    return 0 if summary["approved"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
