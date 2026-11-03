"""LIFELINE AI - step 1, PERCEIVE. Real SAM 3.1 masks over flood imagery.

    python capture_sam.py                       # all photos in artifacts/photos
    python capture_sam.py --limit 1             # cheap smoke test
    python capture_sam.py --offline             # replay the cached artifact

Contract (dev.meta.ai/docs/sam):
  * POST {META_API_BASE}/responses, model sam-3.1
  * the prompt must be a SHORT NOUN PHRASE ("flood water"). Commands and
    questions return zero matches - that is a valid result, not an error.
  * one record per match:  id <|box;..|> <|mask;..|>
  * masks are decoded with Meta's own parser (meta-sam-parser), not by hand.

Severity is measured, never asserted:

    fill      = mask pixels / mask raster pixels      (water density in a box)
    box_area  = (x2-x1+1) * (y2-y1+1)                 (source pixels)
    water_px  = fill * box_area                       (per detected object)
    severity% = min(100, sum(water_px) / (w*h) * 100)

Writes artifacts/sam_flood_segments.json, which agent.py step 1 consumes.
Also writes artifacts/photos/CREDITS.json alongside the imagery so every
placeholder photo keeps its author and licence.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from meta_sam_parser import SegmentationMask, decode_mask_to_raster

import allocator

ROOT = Path(__file__).parent
PHOTOS = ROOT / "artifacts" / "photos"
ARTIFACTS = ROOT / "artifacts"
OUT = ARTIFACTS / "sam_flood_segments.json"

MODEL = "sam-3.1"
PROMPT = "flood water"          # noun phrase, per the SAM docs
COST_PER_IMAGE_USD = 2.50 / 1000  # $2.50 per 1,000 images

RECORD = re.compile(r"(\d+)<\|box;([^|]*)\|><\|mask;([^|]*)\|>")


def _fields(blob: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in blob.split(";"):
        if "=" in part:
            key, _, value = part.partition("=")
            out[key.strip()] = value
    return out


def _output_text(body: dict) -> str:
    """Collect every output_text part, in order."""
    chunks: list[str] = []
    for item in body.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for part in item.get("content", []) or []:
            if part.get("type") == "output_text":
                chunks.append(part.get("text", ""))
    if not chunks and isinstance(body.get("output_text"), str):
        chunks.append(body["output_text"])
    return "".join(chunks)


def _render_overlay(image_path: Path, cells: list, out_path: Path) -> None:
    """Draw the decoded masks over the source photo so the videos and slides
    show real model output rather than a decorative gradient."""
    from PIL import Image, ImageDraw

    base = Image.open(image_path).convert("RGBA")
    tint = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(tint)
    for raster, height, width, box in cells:
        x1, y1, x2, y2 = box
        mask = Image.frombytes("L", (width, height), bytes(255 if v else 0 for v in raster))
        target_w, target_h = max(1, x2 - x1 + 1), max(1, y2 - y1 + 1)
        mask = mask.resize((target_w, target_h), Image.BILINEAR)
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        layer.paste(Image.new("RGBA", (target_w, target_h), (45, 212, 191, 120)), (x1, y1), mask)
        tint = Image.alpha_composite(tint, layer)
        draw.rectangle([x1, y1, x2, y2], outline=(45, 212, 191, 220), width=3)

    Image.alpha_composite(base, tint).convert("RGB").save(out_path, "PNG", optimize=True)


def segment(image_path: Path, timeout: float = 120.0) -> dict:
    mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(image_path.read_bytes()).decode()
    payload = {
        "model": MODEL,
        "input": [{
            "type": "message",
            "role": "user",
            "content": [
                {"type": "input_text", "text": PROMPT},
                {"type": "input_image", "image_url": f"data:{mime};base64,{b64}"},
            ],
        }],
        "stream": False,
        # one_bit keeps the payload small; confidence lets us report certainty
        "metadata": {"mask_encoding": "one_bit", "include_confidence": "true"},
    }
    req = urllib.request.Request(
        os.environ["META_API_BASE"].rstrip("/") + "/responses",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['META_API_KEY']}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = json.loads(response.read().decode())

    text = _output_text(body)
    objects = []
    cells: list = []
    for match in RECORD.finditer(text):
        object_id, box_blob, mask_blob = match.groups()
        box, mask = _fields(box_blob), _fields(mask_blob)
        try:
            x1, y1 = int(box["x1"]), int(box["y1"])
            x2, y2 = int(box["x2"]), int(box["y2"])
            frame_w, frame_h = int(box["w"]), int(box["h"])
            height, width, enc_payload = mask["data"].split(",", 2)
            mask_obj = SegmentationMask(
                encoding="one_bit" if enc_payload.startswith("!") else "lossless",
                payload=enc_payload,
                width=int(width),
                height=int(height),
            )
            raster = decode_mask_to_raster(mask_obj)
        except Exception as exc:  # never lose a whole image to one bad record
            objects.append({"object_id": int(object_id), "error": f"{type(exc).__name__}: {exc}"})
            continue

        filled = sum(1 for value in raster if value)
        fill = filled / len(raster) if raster else 0.0
        box_area = max(0, (x2 - x1 + 1)) * max(0, (y2 - y1 + 1))
        cells.append((raster, int(height), int(width), (x1, y1, x2, y2)))
        objects.append({
            "object_id": int(object_id),
            "box": [x1, y1, x2, y2],
            "frame_px": [frame_w, frame_h],
            "confidence": float(box.get("c")) if box.get("c") else None,
            "mask_raster": [int(height), int(width)],
            "mask_fill_ratio": round(fill, 4),
            "box_area_px": box_area,
            "water_px_estimate": round(fill * box_area),
        })

    frame_w = frame_h = 0
    for obj in objects:
        if "frame_px" in obj:
            frame_w, frame_h = obj["frame_px"]
            break
    frame_area = frame_w * frame_h
    water_px = sum(obj.get("water_px_estimate", 0) for obj in objects)
    severity = round(min(100.0, water_px / frame_area * 100), 1) if frame_area else 0.0

    return {
        "file": image_path.name,
        "prompt": PROMPT,
        "objects_found": len(objects),
        "water_severity_percent": severity,
        "frame_px": [frame_w, frame_h],
        "water_px_estimate": water_px,
        "method": "sum(fill_ratio * box_area) / frame_area, clamped to 100",
        "objects": objects,
        "_cells": cells,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="SAM 3.1 flood capture")
    parser.add_argument("--photos", default=str(PHOTOS))
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--log-credit", action="store_true")
    parser.add_argument("--overlay", action="store_true", help="render mask overlays for video")
    args = parser.parse_args(argv)

    allocator.load_env()
    if not os.environ.get("META_API_KEY"):
        print("META_API_KEY missing", file=sys.stderr)
        return 2

    photos = sorted(Path(args.photos).glob("*.jpg")) + sorted(Path(args.photos).glob("*.jpeg"))
    photos += sorted(Path(args.photos).glob("*.png"))
    if args.limit:
        photos = photos[: args.limit]
    if not photos:
        print(f"no photos in {args.photos}", file=sys.stderr)
        return 2

    print(f"SAM 3.1  prompt='{PROMPT}'  images={len(photos)}\n")
    frames, failures = [], []
    for path in photos:
        try:
            frame = segment(path)
            cells = frame.pop("_cells", [])
            if args.overlay and cells:
                overlay_dir = Path(args.photos) / "overlays"
                overlay_dir.mkdir(exist_ok=True)
                _render_overlay(path, cells, overlay_dir / f"{path.stem}.png")
            frames.append(frame)
            print(f"  {path.name[:44]:44s} {frame['water_severity_percent']:5.1f}%  "
                  f"{frame['objects_found']} object(s)")
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:300].decode(errors="replace")
            failures.append({"file": path.name, "status": exc.code, "detail": detail})
            print(f"  {path.name[:44]:44s} HTTP {exc.code}  {detail[:80]}")
        except Exception as exc:
            failures.append({"file": path.name, "error": f"{type(exc).__name__}: {exc}"})
            print(f"  {path.name[:44]:44s} {type(exc).__name__}: {exc}")

    if not frames:
        print("\nno frames captured - artifact not written", file=sys.stderr)
        return 1

    credits_path = Path(args.photos) / "CREDITS.json"
    credits = json.loads(credits_path.read_text(encoding="utf-8")) if credits_path.exists() else []

    artifact = {
        "schema": "lifeline.sam_flood_segments/1.0",
        "captured_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": MODEL,
        "endpoint": "/responses",
        "prompt": PROMPT,
        "prompt_rule": "SAM 3.1 takes a short noun phrase; instructions return zero matches",
        "severity_definition": "sum(mask fill ratio * box area) / frame area * 100, clamped to 100",
        "cost_usd": round(len(frames) * COST_PER_IMAGE_USD, 4),
        "images": credits,
        "frames": frames,
        "failures": failures,
        "note": (
            "Placeholder imagery from Wikimedia Commons with attribution in "
            "artifacts/photos/CREDITS.json. These are NOT Kottur photographs. "
            "Drop real Kottur photos into artifacts/photos/ and re-run to replace them."
        ),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out.relative_to(ROOT)}  ({len(frames)} frames, {len(failures)} failures)")

    worst = max(frames, key=lambda f: f["water_severity_percent"])
    print(f"worst frame: {worst['file']} at {worst['water_severity_percent']}%")

    if args.log_credit:
        import credit_tracker
        try:
            entry = credit_tracker.CreditTracker().log(
                "sam", calls=len(frames), cost=len(frames) * COST_PER_IMAGE_USD,
                note=f"SAM 3.1 flood capture, {len(frames)} images",
            )
            print(f"credit logged: ${entry['cost_usd']:.4f} for {entry['calls']} images")
        except Exception as exc:
            print(f"credit log failed: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
