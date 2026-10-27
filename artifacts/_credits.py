import json, re
from pathlib import Path

sam = json.loads(Path("artifacts/sam_flood_segments.json").read_text(encoding="utf-8"))

def plain(html):
    text = re.sub(r"<[^>]+>", "", html or "")
    return re.sub(r"\s+", " ", text).strip()

images = []
for img in sam["images"]:
    images.append({
        "file": img["file"],
        "title": img.get("title"),
        "author": plain(img.get("author")),
        "license": img.get("license"),
        "source": img.get("source"),
        "used_for": "SAM 3.1 flood-water mask measurement (real API output)",
    })

credits = {
    "note": (
        "Every photographic frame on this page is a Wikimedia Commons file under the "
        "licence shown. None of them is a photo of Kottur. The Kottur flood account is "
        "first-hand; the imagery is public flood evidence used to run SAM 3.1."
    ),
    "images": images,
    "voice": {
        "file": "artifacts/audio/report_01.wav",
        "status": "synthetic placeholder until the real Kottur voice note is supplied",
        "model": "muse-voice-transcribe-1.0",
    },
    "fonts": "system stack plus bundled local fonts; see ui/app/globals.css",
}
Path("CREDITS.json").write_text(json.dumps(credits, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"wrote CREDITS.json with {len(images)} image attributions")
for i in images:
    print(" ", i["file"], "|", i["license"], "|", i["author"][:40])
