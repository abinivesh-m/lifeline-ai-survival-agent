"""LIFELINE AI - build the two looping background videos from our own artefacts.

    python make_video.py                # both
    python make_video.py --flood
    python make_video.py --fuel

flood.mp4  is built from artifacts/photos/overlays/ - the real SAM 3.1 masks
           decoded from the model, composited over the source photos. Not stock
           footage, not a stock gradient: what the model actually saw.
fuel_flow.mp4  is the 70 L / 30 L split animated along the dependency chain.

No third-party video, no licence question, no download. Frames are rendered
with Pillow and piped to ffmpeg as raw RGB - no temp frame files on disk.

Output: artifacts/videos/flood.mp4, artifacts/videos/fuel_flow.mp4
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).parent
OVERLAYS = ROOT / "artifacts" / "photos" / "overlays"
SEGMENTS = ROOT / "artifacts" / "sam_flood_segments.json"
OUT = ROOT / "artifacts" / "videos"

W, H = 1920, 1080
FPS = 24

INK = (232, 243, 246)
TEAL = (45, 212, 191)
RED = (248, 113, 113)
BLUE = (96, 165, 250)
AMBER = (245, 185, 66)
MUTED = (134, 160, 171)
BG = (10, 18, 22)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = ["seguisb.ttf", "segoeuib.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]
    for name in names:
        for base in (r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu"):
            path = Path(base) / name
            if path.exists():
                return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _cover(image: Image.Image, width: int, height: int, zoom: float = 1.0) -> Image.Image:
    """Fill the frame, keeping aspect ratio, then apply a slow zoom."""
    target_w, target_h = width * zoom, height * zoom
    scale = max(target_w / image.width, target_h / image.height)
    resized = image.resize(
        (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
        Image.LANCZOS,
    )
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def _gradient(width: int, height: int, top: tuple, bottom: tuple) -> Image.Image:
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        t = y / max(1, height - 1)
        draw.line(
            [(0, y), (width, y)],
            fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)),
        )
    return image


def _ffmpeg(out_path: Path, frames: int) -> subprocess.Popen:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path),
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


# --------------------------------------------------------------------------- #
# flood.mp4 - real SAM masks over real flood photographs
# --------------------------------------------------------------------------- #

def build_flood(frames_per_image: int = 26) -> Path:
    if not SEGMENTS.exists():
        raise SystemExit("run capture_sam.py --overlay first")
    data = json.loads(SEGMENTS.read_text(encoding="utf-8"))
    worst = max(f["water_severity_percent"] for f in data["frames"])

    shots = []
    for frame in sorted(data["frames"], key=lambda f: -f["water_severity_percent"]):
        overlay = OVERLAYS / f"{Path(frame['file']).stem}.png"
        if not overlay.exists():
            continue
        shots.append((overlay, frame["water_severity_percent"], frame["file"]))

    if not shots:
        raise SystemExit(f"no overlays in {OVERLAYS}")

    out = OUT / "flood.mp4"
    total = len(shots) * frames_per_image
    proc = _ffmpeg(out, total)
    assert proc.stdin is not None

    big = _font(150, bold=True)
    mid = _font(34, bold=True)
    small = _font(24)
    tiny = _font(20)

    for overlay, severity, name in shots:
        base = Image.open(overlay).convert("RGB")
        for index in range(frames_per_image):
            t = index / max(1, frames_per_image - 1)
            zoom = 1.03 + 0.06 * t
            frame_image = _cover(base, W, H, zoom)
            frame_image = ImageEnhance.Brightness(frame_image).enhance(0.72)

            veil = Image.new("RGBA", (W, H), (6, 12, 16, 0))
            vdraw = ImageDraw.Draw(veil)
            vdraw.rectangle([0, H - 340, W, H], fill=(6, 12, 16, 200))
            vdraw.rectangle([0, 0, W, 190], fill=(6, 12, 16, 170))
            frame_image = Image.alpha_composite(frame_image.convert("RGBA"), veil)

            draw = ImageDraw.Draw(frame_image)
            draw.text((80, 56), "LIFELINE AI", font=small, fill=TEAL)
            draw.text((80, 92), "SAM 3.1  ·  prompt \"flood water\"", font=mid, fill=INK)
            draw.text((W - 80, 62), f'{data["model"]}', font=tiny, fill=MUTED, anchor="ra")
            draw.text((W - 80, 92), f"{len(data['frames'])} frames segmented",
                      font=tiny, fill=MUTED, anchor="ra")

            draw.text((80, H - 322), "water extent", font=small, fill=MUTED)
            draw.text((80, H - 300), f"{severity:.1f}%", font=big, fill=TEAL)

            bar_x, bar_y, bar_w = 80, H - 92, 700
            draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 10], fill=(28, 45, 55))
            draw.rectangle([bar_x, bar_y, bar_x + int(bar_w * severity / 100), bar_y + 10], fill=TEAL)
            draw.text((bar_x, bar_y + 22), "of frame covered by the decoded mask",
                      font=tiny, fill=MUTED)

            draw.text((W - 80, H - 322), "worst frame in set", font=small, fill=MUTED, anchor="ra")
            draw.text((W - 80, H - 300), f"{worst:.1f}%", font=big, fill=AMBER, anchor="ra")
            short = Path(name).stem.replace("_", " ")[:52]
            draw.text((W - 80, H - 70), short, font=tiny, fill=MUTED, anchor="ra")

            proc.stdin.write(frame_image.convert("RGB").tobytes())

    proc.stdin.close()
    proc.wait()
    print(f"  flood.mp4      {out.stat().st_size / 1024 / 1024:.1f} MB  "
          f"{total / FPS:.1f}s  {len(shots)} masks")
    return out


# --------------------------------------------------------------------------- #
# fuel_flow.mp4 - 100 L in the depot, 70 L to the heart, 30 L to the lungs
# --------------------------------------------------------------------------- #

def _bezier(p0, p1, p2, t):
    x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
    y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
    return x, y


def _node(draw, xy, radius, colour, label, sub, font, subfont, pulse=0.0):
    x, y = xy
    r = radius + pulse * 7
    draw.ellipse([x - r, y - r, x + r, y + r], fill=(8, 14, 18))
    draw.ellipse([x - r, y - r, x + r, y + r], outline=colour, width=3)
    glow = Image.new("RGBA", (int(r * 4), int(r * 4)), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        [r * 2 - r * 1.6, r * 2 - r * 1.6, r * 2 + r * 1.6, r * 2 + r * 1.6],
        fill=colour + (38,),
    )
    draw.bitmap((int(x - r * 2), int(y - r * 2)), glow.filter(ImageFilter.GaussianBlur(18)))
    draw.text((x, y + r + 24), label, font=font, fill=colour, anchor="ma")
    draw.text((x, y + r + 58), sub, font=subfont, fill=MUTED, anchor="ma")


def build_fuel(seconds: float = 12.0) -> Path:
    out = OUT / "fuel_flow.mp4"
    total = int(seconds * FPS)
    proc = _ffmpeg(out, total)
    assert proc.stdin is not None

    depot = (330, 540)
    heart = (1290, 360)
    lungs = (1290, 760)

    big = _font(64, bold=True)
    mid = _font(30, bold=True)
    small = _font(24)
    tiny = _font(19)

    for index in range(total):
        t = index / total
        image = _gradient(W, H, (10, 20, 26), (6, 13, 17)).convert("RGBA")
        draw = ImageDraw.Draw(image)

        # faint grid, so the frame does not look empty
        for gx in range(0, W, 80):
            draw.line([(gx, 0), (gx, H)], fill=(255, 255, 255, 5))
        for gy in range(0, H, 80):
            draw.line([(0, gy), (W, gy)], fill=(255, 255, 255, 5))

        draw.text((80, 60), "LIFELINE AI  /  TOWN AS MACHINE", font=small, fill=TEAL)
        draw.text((80, 96), "100 L in. 70 L keeps the heart. 30 L keeps the water.",
                  font=mid, fill=INK)

        # pipes
        for (a, b, colour, width) in (
            (depot, heart, RED, 16),
            (depot, lungs, BLUE, 10),
        ):
            mid_point = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - 60)
            points = [_bezier(a, mid_point, b, s / 60) for s in range(61)]
            for i in range(len(points) - 1):
                draw.line([points[i], points[i + 1]], fill=colour + (60,), width=width)

            # particles travelling along the pipe
            for p in range(26):
                phase = (t * 1.6 + p / 26) % 1.0
                x, y = _bezier(a, mid_point, b, phase)
                fade = math.sin(math.pi * phase)
                radius = (5 if colour is RED else 4) + fade * 3
                draw.ellipse([x - radius, y - radius, x + radius, y + radius],
                             fill=colour + (int(200 * fade) + 40,))

        beat = 0.5 + 0.5 * math.sin(index / FPS * math.pi * 2 * 1.15)
        breath = 0.5 + 0.5 * math.sin(index / FPS * math.pi * 2 * 0.28)

        _node(draw, depot, 76, TEAL, "BLOOD  100 L", "fuel depot", mid, tiny, 0.15)
        _node(draw, heart, 68, RED, "HEART  70 L", "4 h runtime", mid, tiny, beat * 0.5)
        _node(draw, lungs, 54, BLUE, "LUNGS  30 L", "fed by the heart", mid, tiny, breath * 0.4)

        draw.text((depot[0] - 76, depot[1] + 176), "3.5 billion people",
                  font=tiny, fill=MUTED)
        draw.text((depot[0] - 76, depot[1] + 202), "live in towns like Kottur",
                  font=tiny, fill=MUTED)

        # the two numbers that matter
        draw.text((80, H - 158), "70", font=big, fill=RED)
        draw.text((196, H - 124), "L  hospital first, always", font=small, fill=MUTED)
        draw.text((80, H - 86), "30", font=big, fill=BLUE)
        draw.text((196, H - 52), "L  water pump second", font=small, fill=MUTED)

        draw.text((W - 80, H - 150), "NH-544 km 42 · 4.2 km blocked",
                  font=small, fill=MUTED, anchor="ra")
        draw.text((W - 80, H - 116), "A* bypass 7.8 km · 40% fuel saved",
                  font=small, fill=TEAL, anchor="ra")
        draw.text((W - 80, H - 78), "fuel allocation only · no medical advice",
                  font=tiny, fill=MUTED, anchor="ra")

        proc.stdin.write(image.convert("RGB").tobytes())

    proc.stdin.close()
    proc.wait()
    print(f"  fuel_flow.mp4  {out.stat().st_size / 1024 / 1024:.1f} MB  {seconds:.0f}s")
    return out


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="build looping background video")
    parser.add_argument("--flood", action="store_true")
    parser.add_argument("--fuel", action="store_true")
    args = parser.parse_args(argv)

    both = not (args.flood or args.fuel)
    OUT.mkdir(parents=True, exist_ok=True)
    print("rendering video from our own artefacts\n")
    if both or args.flood:
        build_flood()
    if both or args.fuel:
        build_fuel()
    print(f"\nwrote to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
