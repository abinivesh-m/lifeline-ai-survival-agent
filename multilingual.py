"""Model-drafted escalation payloads in eight languages, validated in code.

Why this module exists
----------------------
The tier-2 payloads used by ``escalation.py`` came from ``locales/*.json``:
hand-written templates, translated once by a person. That is safe, but it is
not the product claim "a model writes the eight languages". This module closes
that gap with real calls, and keeps the templates as the fallback.

The Meta API has no speech-synthesis endpoint - its model list is Wonder, Spark,
SAM, Voice Transcribe and Image. So the model drafts the *spoken script*, and
``voice_alert.py`` renders it to audio with an offline-capable neural voice.
The intelligence is the model's; the vocal cords are a delivery detail, and the
README says exactly that.

Pipeline per locale
-------------------
1. DRAFT  - muse-spark-1.3 (Meta Model API) writes two bodies in one call:
            a <=160 char SMS and a <=300 char spoken script for the same alert.
2. CHECK  - this file's ``validate_body`` rejects unknown numbers, medical
            advice, links, over-length text and missing reply codes.
3. REVIEW - muse-wonder-1.0 (Meta Model API) audits each draft for invented
            figures, clinical advice, wrong language, or a false claim that
            fuel already moved. It returns a verdict per payload.
4. KEEP   - a payload ships only if both the code check and the review pass.
            Otherwise the template is kept and the artifact says why.

Everything is written to ``artifacts/multilingual_payloads.json`` with model,
latency, token usage, validation problems and the review reason.

Run:
    python multilingual.py
    python multilingual.py --locales ta,en
    python multilingual.py --verify
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import allocator
import credit_tracker
import i18n

ROOT = Path(__file__).parent
ARTIFACT = ROOT / "artifacts" / "multilingual_payloads.json"
DRAFT_MODEL = os.environ.get("MULTILINGUAL_DRAFT_MODEL", "muse-spark-1.3")
REVIEWER_MODEL = os.environ.get("META_MODEL", "muse-wonder-1.0")

MAX_SMS_CHARS = 160
MAX_VOICE_CHARS = 300
MAX_ALLOCATION_CHARS = 300

# The three payloads one locale must produce. ``allocation`` is the sentence a
# caller hears when they ask "what happened?" - same numbers as the plan, in
# the reader's language.
KINDS = ("sms", "voice", "allocation")
REQUIRED_CODES = {"sms": ("1", "2"), "voice": ("1", "2"), "allocation": ("70", "30", "100")}

REPAIR_HINT = (
    "A spoken payload used an abbreviated unit. Never abbreviate in the voice or "
    "allocation fields: write kilometre, litre and hour as full words."
)


# Every number an honest Kottur alert may contain. 544 and 42 are the road,
# 7.8 the bypass, 4 the hospital runtime, 70/30/100 the allocation, 1/2 the
# reply codes, 200 the sheltered people, 6 the depot reserve. Anything else is
# a fabricated figure.
ALLOWED_NUMBERS = {"1", "2", "4", "6", "7.8", "30", "42", "70", "100", "200", "544"}

BANNED = (
    "http",
    "www.",
    " mg",
    "mg ",
    "dose",
    "dosage",
    "insulin",
    "antibiotic",
    "diagnos",
    "prescri",
    "medical advice",
    "treat the",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def numbers_in(text: str) -> list[str]:
    """Integers and decimals as written, e.g. 70, 7.8, 544."""
    return re.findall(r"\d+(?:[.,]\d+)?", text)


def validate_body(body: Any, code: str, town: dict | None = None, kind: str = "sms") -> dict:
    """The code check. A reviewer model is never the last word on numbers."""
    if not isinstance(body, str):
        return {"ok": False, "problems": ["body is not a string"]}

    limit = {
        "sms": MAX_SMS_CHARS,
        "voice": MAX_VOICE_CHARS,
        "allocation": MAX_ALLOCATION_CHARS,
    }.get(kind, MAX_SMS_CHARS)
    text = body.strip()
    if not text:
        return {"ok": False, "problems": ["empty body"]}

    problems: list[str] = []
    if len(text) > limit:
        problems.append(f"{len(text)} chars exceeds {limit}")

    lowered = text.lower()
    for token in BANNED:
        if token in lowered:
            problems.append(f"contains banned phrase {token!r}")

    for number in numbers_in(text):
        normalised = number.replace(",", ".")
        if normalised not in ALLOWED_NUMBERS:
            problems.append(f"number {number} is not in the allowed set")

    # The reader must be able to answer in the same message, and the spoken
    # allocation must carry the real split - never a rounded or invented one.
    for required in REQUIRED_CODES.get(kind, ()):
        if required not in text:
            problems.append(f"missing required number {required}")

    return {"ok": not problems, "problems": problems, "chars": len(text)}


def _language(code: str) -> str:
    return next(
        (entry["language"] for entry in i18n.available() if entry["code"] == code), code
    )


def draft_prompt(code: str, town: dict, hint: str = "") -> str:
    language = _language(code)
    repair = f"\nThe previous attempt was rejected. {hint}\n" if hint else ""
    return (
        "Draft three payloads for a town diesel crisis. Facts, all true:\n"
        "- Kottur, Tamil Nadu. NH-544 km 42 is blocked; the surveyed bypass is 7.8 km.\n"
        "- The hospital generator has 4 hours of diesel left.\n"
        "- The validated split is 70 L hospital, 30 L water pump, 100 L total.\n"
        "- The reader replies 1 to approve dispatch, 2 to deny.\n\n"
        f"Write all three in {language} ({code}).\n"
        "sms: at most 160 characters, for a feature phone.\n"
        "voice: at most 300 characters, written to be SPOKEN aloud by a phone\n"
        "       call or a temple loudspeaker. Say that the reader can press 1 to\n"
        "       approve or 2 to deny. Write units as a voice would say them.\n"
        "allocation: at most 300 characters, SPOKEN to a caller who asks what\n"
        "       was decided. It must state the split: seventy litres to the\n"
        "       hospital, thirty to the water pump, one hundred in total. Say the\n"
        "       numbers as digits so the phone system can read them.\n\n"
        "Rules for all three: no medical advice, no diagnosis, no dosing, no new\n"
        "numbers, and never claim fuel has already been dispatched. Use only\n"
        "these numbers if you use any: "
        f"{', '.join(sorted(ALLOWED_NUMBERS, key=float))}.\n{repair}\n"
        'Reply as JSON only: {"sms": "<sms body>", "voice": "<spoken alert>", '
        '"allocation": "<spoken split>"}'
    )


def review_prompt(code: str, sms: str, voice: str, allocation: str) -> str:
    language = _language(code)
    return (
        "Audit three emergency payloads for the same incident.\n"
        f"Locale: {code} ({language}).\n"
        f'SMS: """{sms}"""\n'
        f'VOICE ALERT: """{voice}"""\n'
        f'ALLOCATION: """{allocation}"""\n'
        f"ALLOWED NUMBERS: {', '.join(sorted(ALLOWED_NUMBERS, key=float))}\n\n"
        "For each payload, reject it if any other number appears, if it gives\n"
        "medical advice (diagnosis, dose, medicine, treatment), if it is not\n"
        "written in the requested language, or if it claims fuel was already\n"
        "dispatched. The spoken payloads must be speakable: no acronym-only\n"
        "units and no screen instructions such as 'tap' or 'click'. The\n"
        "allocation must match 70 hospital, 30 water pump, 100 total.\n\n"
        'Reply as JSON only: {"sms_ok": true|false, "voice_ok": true|false, '
        '"allocation_ok": true|false, "reason": "<short reason>"}'
    )


def _meta_chat(
    model: str,
    prompt: str,
    timeout: float = 60.0,
    max_tokens: int = 800,
    reasoning_effort: str | None = None,
) -> dict:
    """One Meta Model API call. Never raises; the caller decides on fallback."""
    meta: dict[str, Any] = {
        "provider": "Meta Model API",
        "model": model,
        "status": "unavailable",
        "latency_s": None,
        "text": None,
        "usage": None,
        "detail": "",
    }
    if os.environ.get("LIFELINE_OFFLINE", "0") == "1":
        meta["detail"] = "LIFELINE_OFFLINE=1"
        return meta
    base = os.environ.get("META_API_BASE", "").rstrip("/")
    key = os.environ.get("META_API_KEY", "")
    if not base or not key:
        meta["detail"] = "META_API_BASE and META_API_KEY must be set"
        return meta

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You output strict JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
        "max_tokens": max_tokens,
    }
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    request = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )

    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        meta["status"] = "error"
        meta["detail"] = f"{type(exc).__name__}: {exc}"
        return meta

    meta["latency_s"] = round(time.time() - started, 2)
    meta["usage"] = body.get("usage")
    try:
        meta["text"] = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        meta["status"] = "error"
        meta["detail"] = "no choices[0].message.content"
        return meta

    if not (meta["text"] or "").strip():
        finish = (body["choices"][0].get("finish_reason") if body.get("choices") else None)
        meta["status"] = "error"
        meta["detail"] = f"empty content: finish_reason={finish} - raise max_tokens"
        return meta

    meta["status"] = "answered"
    return meta


def _parse_json(text: str | None) -> dict:
    if not text:
        return {}
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            return {}
        try:
            parsed = json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            return {}
    return parsed if isinstance(parsed, dict) else {}


def generate_locale(
    code: str, town: dict, tracker: credit_tracker.CreditTracker, hint: str = ""
) -> dict:
    """Draft, validate and review one locale. Never raises on a model failure."""
    hours = int(town["organs"]["hospital"]["runtime_hours_left"])
    tier2 = i18n.t(code, "esc.tier2", hours=hours)
    templates = {
        "sms": tier2,
        "voice": i18n.t(code, "esc.voice", hours=hours) if _has_key(code, "esc.voice") else tier2,
        "allocation": "",
    }
    field = {"sms": "body", "voice": "script", "allocation": "script"}

    record: dict[str, Any] = {
        "locale": code,
        "language": _language(code),
        "draft": None,
        "review": None,
    }
    for kind in KINDS:
        record[kind] = {
            field[kind]: templates[kind],
            "template": templates[kind],
            "source": "template-fallback" if templates[kind] else "none",
            "valid": False,
            "problems": [],
        }

    # Muse Spark is a reasoning model: on a 900 token cap it spent every token
    # thinking and returned empty content. Give it room and ask for low effort.
    draft = _meta_chat(
        DRAFT_MODEL,
        draft_prompt(code, town, hint),
        timeout=120.0,
        max_tokens=6000,
        reasoning_effort="low",
    )
    # A reasoning model that burns its budget still spent tokens. Log the call
    # whenever the server billed it, even if the content came back empty.
    if draft.get("usage"):
        tracker.log(
            "spark",
            calls=1,
            note=f"multilingual draft {code} (sms + voice + allocation, {draft['status']})",
        )
    if draft["status"] != "answered":
        detail = f"draft failed: {draft['detail'] or draft['status']}"
        for kind in KINDS:
            record[kind]["problems"].append(detail)
        return record

    record["draft"] = {
        "model": DRAFT_MODEL,
        "provider": "Meta Model API",
        "latency_s": draft["latency_s"],
        "usage": draft["usage"],
    }

    parsed = _parse_json(draft["text"])
    checks = {}
    for kind in KINDS:
        value = parsed.get(kind)
        check = validate_body(value, code, town, kind=kind)
        checks[kind] = (value, check)
        record[kind]["problems"] = list(check["problems"])
        record[kind]["chars"] = check.get("chars")

    if not any(check["ok"] for _, check in checks.values()):
        return record

    review = _meta_chat(
        REVIEWER_MODEL,
        review_prompt(
            code,
            (parsed.get("sms") or "").strip(),
            (parsed.get("voice") or "").strip(),
            (parsed.get("allocation") or "").strip(),
        ),
        timeout=90.0,
        max_tokens=3000,
        reasoning_effort="low",
    )
    verdict = _parse_json(review["text"])
    record["review"] = {
        "model": REVIEWER_MODEL,
        "provider": "Meta Model API",
        "status": review["status"],
        "latency_s": review["latency_s"],
        "usage": review["usage"],
        "reason": str(verdict.get("reason", ""))[:240] or review["detail"],
        **{f"{kind}_ok": verdict.get(f"{kind}_ok") is True for kind in KINDS},
    }
    if review.get("usage"):
        tracker.log(
            "wonder",
            calls=1,
            note=(
                f"multilingual review {code} ("
                + " / ".join(f"{kind} {record['review'][f'{kind}_ok']}" for kind in KINDS)
                + ")"
            ),
        )

    for kind in KINDS:
        value, check = checks[kind]
        if check["ok"] and record["review"][f"{kind}_ok"]:
            record[kind].update(
                {field[kind]: value.strip(), "source": "model", "valid": True}
            )
        elif check["ok"]:
            record[kind]["problems"].append(
                f"review rejected: {record['review']['reason'] or 'no reason'}"
            )

    return record


def _has_key(code: str, key: str) -> bool:
    messages = i18n.load(code)
    node: Any = messages
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


def run(locales: list[str] | None = None) -> dict:
    allocator.load_env()
    town = allocator.load_town()
    order = [entry["code"] for entry in i18n.available()]
    codes = locales or order

    tracker = credit_tracker.CreditTracker()
    before = tracker.spend_precise()

    records = []
    for code in codes:
        record = generate_locale(code, town, tracker)
        missing = [kind for kind in KINDS if not record[kind]["valid"]]
        if missing:
            # One bounded repair per locale: a reviewer often rejects a single
            # speakability detail, and re-drafting with that detail named is
            # cheaper than shipping a silent language. Never loops.
            print(f"  {code}: repairing {', '.join(missing)}")
            second = generate_locale(code, town, tracker, hint=REPAIR_HINT)
            if sum(second[k]["valid"] for k in KINDS) > sum(record[k]["valid"] for k in KINDS):
                second["repaired"] = True
                record = second
        records.append(record)

    if locales and ARTIFACT.exists():
        # A partial run must never delete the languages it did not touch.
        previous = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        touched = set(codes)
        kept = [
            record for record in previous.get("locales", [])
            if record.get("locale") not in touched
        ]
        batches = list(previous.get("batches", []))
        carried = float(previous.get("totals", {}).get("cost_usd", 0.0))
        records = sorted(kept + records, key=lambda r: order.index(r["locale"]))
    else:
        batches = []
        carried = 0.0

    batch_cost = round(tracker.spend_precise() - before, 6)
    batches.append(
        {"generated_utc": _now(), "locales": [r["locale"] for r in records if r["locale"] in codes],
         "cost_usd": batch_cost}
    )

    artifact = {
        "schema": "lifeline.multilingual/1.2",
        "generated_utc": _now(),
        "batches": batches,
        "generator": {"provider": "Meta Model API", "model": DRAFT_MODEL},
        "reviewer": {"provider": "Meta Model API", "model": REVIEWER_MODEL},
        "rules": {
            "max_chars": {
                "sms": MAX_SMS_CHARS,
                "voice": MAX_VOICE_CHARS,
                "allocation": MAX_ALLOCATION_CHARS,
            },
            "allowed_numbers": sorted(ALLOWED_NUMBERS, key=float),
            "require_reply_codes": ["1", "2"],
            "fallback": "locales/*.json templates",
            "speech": (
                "the meta api exposes no text-to-speech endpoint; "
                "voice_synth.py renders these scripts with MMS-TTS, an open-weight "
                "model, on this laptop's CPU"
            ),
        },
        "totals": {
            "locales": len(records),
            "valid": sum(1 for r in records if all(r[k]["valid"] for k in KINDS)),
            "model_drafted": sum(1 for r in records if r["sms"]["source"] == "model"),
            "voice_scripts": sum(1 for r in records if r["voice"]["valid"]),
            "allocation_scripts": sum(1 for r in records if r["allocation"]["valid"]),
            "cost_usd": round(carried + batch_cost, 6),
            "last_batch_usd": batch_cost,
        },
        "locales": records,
    }

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return artifact


def verify() -> list[str]:
    """Re-check a stored artifact without any network call."""
    problems: list[str] = []
    if not ARTIFACT.exists():
        return ["no artifact - run python multilingual.py"]
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    field = {"sms": "body", "voice": "script", "allocation": "script"}
    for record in data.get("locales", []):
        for kind in KINDS:
            payload = record.get(kind) or {}
            if payload.get("source") != "model":
                continue
            check = validate_body(payload.get(field[kind]), record.get("locale", ""), kind=kind)
            if not check["ok"]:
                problems.append(f"{record['locale']}/{kind}: stored body fails: {check['problems']}")
            if not (record.get("review") or {}).get(f"{kind}_ok"):
                problems.append(f"{record['locale']}/{kind}: marked valid without a passing review")
    return problems


def _print(artifact: dict) -> None:
    totals = artifact["totals"]
    print(
        f"  drafted {totals['model_drafted']}/{totals['locales']} by {artifact['generator']['model']}"
    )
    print(
        f"  reviewed by {artifact['reviewer']['model']} · ${totals['cost_usd']:.6f} total"
    )
    for record in artifact["locales"]:
        marks = " ".join(
            f"{kind[:5]} {'PASS' if record[kind]['valid'] else '----'}" for kind in KINDS
        )
        print(f"  {record['locale']}  {marks}")
        if record["sms"]["valid"]:
            print(f"           {record['sms']['body'][:72]}")
        for kind in KINDS:
            if not record[kind]["valid"] and record[kind]["problems"]:
                print(f"           {kind}: {record[kind]['problems'][0]}")
    print(
        f"  {totals['valid']}/{totals['locales']} locales with all three payloads · "
        f"{totals['voice_scripts']} voice · {totals['allocation_scripts']} allocation · "
        f"{ARTIFACT.name}"
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Draft and validate 8-language SMS + spoken alert payloads"
    )
    parser.add_argument("--locales", help="comma separated codes, default all")
    parser.add_argument("--verify", action="store_true", help="re-check the stored artifact")
    args = parser.parse_args(argv)

    if args.verify:
        problems = verify()
        for problem in problems:
            print(f"  FAIL {problem}")
        print(f"  {len(problems)} problem(s)" if problems else "  artifact verified")
        return 1 if problems else 0

    codes = [code.strip() for code in args.locales.split(",")] if args.locales else None
    artifact = run(codes)
    _print(artifact)
    return 0 if artifact["totals"]["valid"] == artifact["totals"]["locales"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
