"""One line about the open-weight proof, for the capture scripts and the README.

    python scripts/proof_summary.py

Prints: <runs> <valid> <latency> / <latency> / ...

Nothing here is typed by hand, which is the point: the numbers the page, the
README and the video quote all come from artifacts/openweight_proof.json, and a
new capture changes them by existing.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROOF = ROOT / "artifacts" / "openweight_proof.json"


def main() -> int:
    if not PROOF.exists():
        print("0 0 no proof on file")
        return 1
    data = json.loads(PROOF.read_text(encoding="utf-8"))
    runs = data.get("runs", [])
    valid = [run for run in runs if run.get("valid")]
    latencies = " / ".join(f"{run['latency_s']}" for run in valid) or "-"
    print(f"{len(runs)} {len(valid)} {latencies}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
