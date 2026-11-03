"""Rewrite META_API_KEY in .env without ever hardcoding a secret.

Usage:
    python set_key.py                 # reads LIFELINE_NEW_META_KEY from the environment
    python set_key.py --prompt        # asks for the key on stdin (hidden echo not required)

Never put a key literal in this file: the repository is public.
"""
import getpass
import os
import sys
from pathlib import Path


def read_new_key() -> str:
    key = os.environ.get("LIFELINE_NEW_META_KEY", "").strip()
    if key:
        return key
    if "--prompt" in sys.argv or not key:
        try:
            key = getpass.getpass("New META_API_KEY (input hidden): ").strip()
        except (EOFError, KeyboardInterrupt):
            sys.exit("no key supplied")
    if not key:
        sys.exit("no key supplied - set LIFELINE_NEW_META_KEY or pass --prompt")
    return key


def main() -> int:
    new = read_new_key()

    p = Path(".env")
    raw = p.read_text(encoding="utf-8-sig") if p.exists() else ""
    lines, hit = [], 0
    for line in raw.splitlines():
        if line.strip().startswith("META_API_KEY="):
            line = f"META_API_KEY={new}"
            hit += 1
        lines.append(line)
    if not hit:
        lines.append(f"META_API_KEY={new}")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"rewrote META_API_KEY lines: {hit}")

    sys.path.insert(0, ".")
    import allocator

    allocator.load_env()
    loaded = os.environ["META_API_KEY"]
    print("key loaded, length", len(loaded), "prefix", loaded[:4], "| base", os.environ["META_API_BASE"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
