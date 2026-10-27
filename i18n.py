"""LIFELINE AI - world-level i18n over the eight generated locales.

    python i18n.py --list
    python i18n.py --demo                    # LIFEGRID rendered in all 8 languages
    python i18n.py --lang ta --key alloc.total litres=100
    python i18n.py --check

The point is not decoration. A dispatch warning that falls back to English in
Arabic or Swahili is a safety failure in exactly the towns this is built for,
so make_locales.py refuses to ship a locale with a missing key and this module
never silently substitutes English for a present locale.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).parent
LOCALES = ROOT / "locales"

_cache: dict[str, dict[str, str]] = {}


class MissingLocaleError(KeyError):
    """Raised when a key is absent from a loaded locale."""


def available() -> list[dict]:
    index = LOCALES / "index.json"
    if index.exists():
        return json.loads(index.read_text(encoding="utf-8"))["locales"]
    return [
        {"code": path.stem, "language": path.stem, "native": path.stem, "dir": "ltr"}
        for path in sorted(LOCALES.glob("*.json"))
        if path.stem != "index"
    ]


def load(code: str) -> dict[str, str]:
    if code in _cache:
        return _cache[code]
    path = LOCALES / f"{code}.json"
    if not path.exists():
        raise MissingLocaleError(f"no locale file for '{code}'")
    table = json.loads(path.read_text(encoding="utf-8"))
    _cache[code] = table
    return table


def t(code: str, key: str, **fmt) -> str:
    """Translate one key. Missing keys raise - never silently fall back."""
    table = load(code)
    if key not in table:
        raise MissingLocaleError(f"{code}: missing key '{key}'")
    template = table[key]
    try:
        return template.format(**fmt) if fmt else template
    except (KeyError, IndexError) as exc:
        raise MissingLocaleError(f"{code}: bad placeholder in '{key}': {exc}") from exc


def direction(code: str) -> str:
    return load(code).get("dir", "ltr")


def _width(text: str) -> int:
    """Terminal cells a string occupies - CJK glyphs are double width."""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _width(text))


def render_lifegrid(code: str, town: dict) -> str:
    """The town-as-body view, in the reader's language."""
    organs = town["organs"]
    hospital = organs["hospital"]
    pump = organs["water_pump"]
    shelters = organs["shelters"]
    labels = [
        t(code, "lifegrid.blood"),
        t(code, "lifegrid.heart"),
        t(code, "lifegrid.lungs"),
        t(code, "lifegrid.organs"),
    ]
    pad = max(_width(label) for label in labels) + 3
    lines = [
        f'{t(code, "app.title")}  -  {t(code, "app.subtitle")}',
        "",
        f'  {_pad(labels[0], pad)} {organs["fuel_depot"]["fuel_litres"]} L   '
        f'{t(code, "lifegrid.fuel")}',
        f'  {_pad(labels[1], pad)} {hospital["fuel_demand_litres"]} L   '
        f'{t(code, "lifegrid.runtime", hours=int(hospital["runtime_hours_left"]))}',
        f'  {_pad(labels[2], pad)} {pump["fuel_demand_litres"]} L   '
        f'{t(code, "lifegrid.feeder")}',
        f'  {_pad(labels[3], pad)} {shelters["people"]}    '
        f'{t(code, "lifegrid.nowater", hours=int(town["crisis"]["expected_clear_hours"]))}',
        "",
        f'  {t(code, "alloc.total", litres=100)}',
        f'  {t(code, "alloc.note")}',
        f'  {t(code, "world.scope")}',
    ]
    return "\n".join(lines)


def _check() -> list[str]:
    """No locale may ship with a key missing - that is a safety bug, not a typo."""
    problems: list[str] = []
    if not LOCALES.exists():
        return ["locales/ does not exist - run python make_locales.py"]
    entries = available()
    if not entries:
        return ["locales/ has no locale files"]
    baseline = set(load("en"))
    for entry in entries:
        code = entry["code"]
        table = load(code)
        missing = sorted(baseline - set(table))
        extra = sorted(set(table) - baseline)
        if missing:
            problems.append(f"{code}: {len(missing)} missing key(s) {missing[:5]}")
        if extra:
            problems.append(f"{code}: {len(extra)} unexpected key(s) {extra[:5]}")
        for key, value in table.items():
            if not isinstance(value, str) or not value.strip():
                problems.append(f"{code}: '{key}' is empty")
        # placeholders must match the English template exactly
        for key in sorted(baseline & set(table)):
            want = set(re.findall(r"\{(\w+)\}", load("en")[key]))
            got = set(re.findall(r"\{(\w+)\}", table[key]))
            if want != got:
                problems.append(f"{code}: '{key}' placeholders {sorted(got)} != {sorted(want)}")
    return problems


def _demo(town: dict) -> int:
    for entry in available():
        code = entry["code"]
        print("=" * 70)
        print(f'{code.upper()}  {entry["native"]}  ({entry["language"]}, {entry["dir"]})')
        print("=" * 70)
        print(render_lifegrid(code, town))
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="LIFELINE AI world i18n")
    parser.add_argument("--list", action="store_true", help="show the eight locales")
    parser.add_argument("--demo", action="store_true", help="render LIFEGRID in every locale")
    parser.add_argument("--check", action="store_true", help="validate key + placeholder parity")
    parser.add_argument("--lang", default="en", help="locale code for --key")
    parser.add_argument("--key", default=None, help="print one translated key")
    parser.add_argument("values", nargs="*", help="key=value placeholders for --key")
    args = parser.parse_args(argv)

    if not LOCALES.exists():
        print("locales/ missing - run: python make_locales.py", file=sys.stderr)
        return 2

    if args.check:
        problems = _check()
        total = len(load("en"))
        if problems:
            print(f"COVERAGE FAILED - {len(problems)} problem(s)")
            for problem in problems:
                print("  -", problem)
            return 1
        print(f"COVERAGE OK - {len(available())} locales x {total} keys, "
              f"placeholders match")
        return 0

    if args.key:
        fmt: dict[str, str] = {}
        for pair in args.values:
            if "=" not in pair:
                print(f"bad placeholder '{pair}' - expected key=value", file=sys.stderr)
                return 2
            name, value = pair.split("=", 1)
            fmt[name] = value
        try:
            print(t(args.lang, args.key, **fmt))
        except MissingLocaleError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        return 0

    if args.demo:
        town_path = ROOT / "town.json"
        if not town_path.exists():
            print("town.json missing", file=sys.stderr)
            return 2
        return _demo(json.loads(town_path.read_text(encoding="utf-8")))

    for entry in available():
        code = entry["code"]
        print(f'  {code}  {_pad(entry["native"], 12)} {entry["language"]:<12} {entry["dir"]}')
    print(f'\n{len(available())} world locales, {len(load("en"))} keys each')
    print("  python i18n.py --demo    --check    --lang ta --key alloc.total litres=100")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
