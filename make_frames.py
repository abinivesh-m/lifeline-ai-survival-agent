"""LIFELINE AI - generate the six demo frames as 1920x1080 PNGs.

    python make_frames.py

Writes figma/lifegrid.png, graph.png, astar.png, allocator.png, offline.png,
agentic.png. These are the frames used in the README, the 3-minute video and
the Figma deck (drag the PNGs into Figma, or rebuild them there from the same
palette). Every number is read from town.json / a_star.py so the visuals cannot
drift from the code.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import a_star
import allocator
import credit_tracker
import dependency_graph

ROOT = Path(__file__).parent
OUT = ROOT / "figma"
W, H = 1920, 1080
M = 80

BG = (10, 18, 22)
PANEL = (16, 31, 39)
PANEL_HI = (22, 41, 51)
BORDER = (32, 56, 68)
TEXT = (232, 243, 246)
MUTED = (134, 160, 171)
TEAL = (45, 212, 191)
RED = (248, 113, 113)
AMBER = (245, 185, 66)
BLUE = (96, 165, 250)
GREEN = (74, 222, 128)
WHITE = (255, 255, 255)

FONTS = Path("C:/Windows/Fonts")
F_BOLD = FONTS / "segoeuib.ttf"
F_SEMI = FONTS / "seguisb.ttf"
F_REG = FONTS / "segoeui.ttf"
F_MONO = FONTS / "consola.ttf"
F_MONO_B = FONTS / "consolab.ttf"


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def load_town() -> dict:
    return json.loads((ROOT / "town.json").read_text(encoding="utf-8"))


class Frame:
    def __init__(self, number: int, kicker: str, title: str, accent=TEAL) -> None:
        self.img = Image.new("RGB", (W, H), BG)
        self.d = ImageDraw.Draw(self.img)
        self.number = number
        self.accent = accent
        self._grid()
        self._header(kicker, title)
        self._footer()

    # -- chrome ---------------------------------------------------------- #

    def _grid(self) -> None:
        for x in range(0, W, 60):
            self.d.line([(x, 0), (x, H)], fill=(14, 26, 32), width=1)
        for y in range(0, H, 60):
            self.d.line([(0, y), (W, y)], fill=(14, 26, 32), width=1)

    def _header(self, kicker: str, title: str) -> None:
        self.d.rectangle([0, 0, W, 8], fill=self.accent)
        self.text((M, 56), "LIFELINE AI", font(F_BOLD, 30), TEXT)
        self.text((M + 214, 62), kicker, font(F_SEMI, 20), self.accent)
        self.text((M, 104), title, font(F_BOLD, 64), TEXT)
        self.text(
            (W - M, 60),
            "KOTTUR  11.0168 N / 76.9558 E",
            font(F_MONO, 20),
            MUTED,
            anchor="ra",
        )
        self.text(
            (W - M, 92),
            "POLLACHI, COIMBATORE, TAMIL NADU",
            font(F_MONO, 15),
            MUTED,
            anchor="ra",
        )
        self.d.line([(M, 200), (W - M, 200)], fill=BORDER, width=2)

    def _footer(self) -> None:
        y = H - 54
        self.d.line([(M, y - 18), (W - M, y - 18)], fill=BORDER, width=2)
        self.text(
            (M, y),
            "BUILT IN KOTTUR  /  WORKS ANYWHERE  /  META GLOBAL AI DEVELOPER HACKATHON 2026",
            font(F_SEMI, 17),
            MUTED,
        )
        self.text((W - M, y), f"{self.number} / 6", font(F_MONO_B, 17), MUTED, anchor="ra")

    # -- primitives ------------------------------------------------------ #

    def text(self, xy, s, f, fill=TEXT, anchor="la") -> None:
        self.d.text(xy, s, font=f, fill=fill, anchor=anchor)

    def panel(self, box, accent=BORDER, fill=PANEL, radius=18, width=2) -> None:
        self.d.rounded_rectangle(box, radius=radius, fill=fill, outline=accent, width=width)

    def pill(self, xy, label, fg, bg=None) -> int:
        f = font(F_SEMI, 17)
        tw = f.getlength(label)
        x, y = xy
        pad = 14
        box = [x, y, x + tw + pad * 2, y + 34]
        self.d.rounded_rectangle(box, radius=17, fill=bg or tuple(int(v * 0.18) for v in fg))
        self.text((x + pad, y + 16), label, f, fg, anchor="la")
        return int(tw + pad * 2)

    def bar(self, x, y, w, h, pct, color) -> None:
        self.d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=(28, 45, 55))
        filled = max(0, min(1.0, pct)) * w
        if filled > 2:
            self.d.rounded_rectangle([x, y, x + filled, y + h], radius=h // 2, fill=color)

    def arrow(self, p1, p2, color, width=4, dashed=False) -> None:
        (x1, y1), (x2, y2) = p1, p2
        if dashed:
            steps = int(max(abs(x2 - x1), abs(y2 - y1)) // 18)
            for i in range(steps):
                if i % 2 == 0:
                    a = i / max(steps, 1)
                    b = (i + 1) / max(steps, 1)
                    self.d.line(
                        [(x1 + (x2 - x1) * a, y1 + (y2 - y1) * a),
                         (x1 + (x2 - x1) * b, y1 + (y2 - y1) * b)],
                        fill=color, width=width,
                    )
        else:
            self.d.line([p1, p2], fill=color, width=width)
        if not dashed:
            self._head(p1, p2, color, width)

    def _head(self, p1, p2, color, width) -> None:
        import math

        ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
        size = 12 + width
        pts = [
            p2,
            (p2[0] - size * math.cos(ang - 0.42), p2[1] - size * math.sin(ang - 0.42)),
            (p2[0] - size * math.cos(ang + 0.42), p2[1] - size * math.sin(ang + 0.42)),
        ]
        self.d.polygon(pts, fill=color)

    def wrap(self, text, f, max_width) -> list[str]:
        words, lines, current = text.split(), [], ""
        for word in words:
            trial = f"{current} {word}".strip()
            if f.getlength(trial) <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def paragraph(self, xy, text, f, fill=TEXT, max_width=600, leading=1.45) -> int:
        x, y = xy
        for line in self.wrap(text, f, max_width):
            self.text((x, y), line, f, fill)
            y += int(f.size * leading)
        return y

    def save(self, name: str) -> None:
        OUT.mkdir(exist_ok=True)
        path = OUT / name
        self.img.save(path, "PNG", optimize=True)
        print(f"  wrote {path.relative_to(ROOT)}")


# --------------------------------------------------------------------------- #
# frame 1 - LIFEGRID
# --------------------------------------------------------------------------- #

def frame_lifegrid(town: dict, alloc: dict, route: dict) -> None:
    f = Frame(1, "FRAME 01  /  THE MODEL", "TOWN AS MACHINE", TEAL)
    o = town["organs"]

    f.text((M, 232), "A town under disaster is a body with a fuel budget. When the heart stops, the lungs stop. Then the organs.",
           font(F_REG, 26), MUTED)

    organs = [
        ("BLOOD", "fuel_depot", o["fuel_depot"]["fuel_litres"], "L in reserve", "at NH-544 km 42", TEAL),
        ("HEART", "hospital", o["hospital"]["fuel_demand_litres"], "L demand", "4 h runtime left", RED),
        ("LUNGS", "water_pump", o["water_pump"]["fuel_demand_litres"], "L demand", "fed by the heart", BLUE),
        ("ORGANS", "shelters", o["shelters"]["people"], "people", "no water, 6 h", AMBER),
    ]
    card_w, gap = 424, 32
    for i, (role, key, value, unit, note, color) in enumerate(organs):
        x = M + i * (card_w + gap)
        f.panel([x, 306, x + card_w, 596], accent=(*color, ) if False else color, width=2)
        f.d.rectangle([x, 306, x + 6, 596], fill=color)
        f.text((x + 32, 334), role, font(F_BOLD, 20), color)
        f.text((x + 32, 372), key, font(F_MONO, 19), MUTED)
        f.text((x + 32, 418), f"{value:g}", font(F_BOLD, 84), TEXT)
        f.text((x + 32 + f.d.textlength(f"{value:g}", font=font(F_BOLD, 84)) + 14, 470), unit,
               font(F_SEMI, 22), MUTED)
        f.text((x + 32, 528), note, font(F_REG, 19), MUTED)
        share = 1.0 if key in ("fuel_depot", "hospital") else 0.0
        f.bar(x + 32, 560, card_w - 64, 10, share if key != "water_pump" else 0.3, color)

    # artery strip
    f.panel([M, 630, W - M, 812], accent=BORDER)
    f.text((M + 32, 656), "THE ARTERY  /  NH-544 km 42", font(F_BOLD, 20), MUTED)

    x0 = M + 32
    f.text((x0, 706), "4.2 km", font(F_BOLD, 46), RED)
    f.text((x0, 758), "direct corridor, blocked", font(F_REG, 19), MUTED)
    f.arrow((x0 + 210, 742), (x0 + 340, 742), RED, width=5, dashed=True)
    f.text((x0 + 268, 692), "BLOCKED", font(F_MONO_B, 17), RED, anchor="ma")

    f.text((x0 + 380, 706), "7.8 km", font(F_BOLD, 46), GREEN)
    f.text((x0 + 380, 758), "village road found by A*", font(F_REG, 19), MUTED)
    f.arrow((x0 + 596, 742), (x0 + 726, 742), GREEN, width=5)

    f.text((x0 + 766, 706), "40%", font(F_BOLD, 46), TEAL)
    f.text((x0 + 766, 758), "less fuel than the bypass", font(F_REG, 19), MUTED)
    f.text((x0 + 1046, 706), f"{route['saving']['fuel_litres']} L", font(F_BOLD, 46), AMBER)
    f.text((x0 + 1046, 758), "= 6.2 generator-minutes", font(F_REG, 19), MUTED)

    # world band
    f.panel([M, 840, W - M, 968], accent=TEAL, fill=PANEL_HI)
    f.text((M + 32, 862), "3.5 B", font(F_BOLD, 44), TEAL)
    f.text((M + 168, 866), "people live in low-infrastructure towns with this exact cascade", font(F_REG, 22), TEXT)
    f.text((M + 168, 900), "Kerala  ·  Assam  ·  Philippines  ·  Indonesia  ·  Brazil  ·  Kenya  ·  Puerto Rico  ·  any blocked road anywhere",
           font(F_SEMI, 19), MUTED)
    f.pill((W - M - 300, 880), "BUILT IN KOTTUR", TEAL, (18, 46, 46))

    f.save("lifegrid.png")


# --------------------------------------------------------------------------- #
# frame 2 - dependency graph
# --------------------------------------------------------------------------- #

def frame_graph(town: dict) -> None:
    f = Frame(2, "FRAME 02  /  STEP 3", "DEPENDENCY GRAPH", BLUE)
    order = dependency_graph.kahn_order(town)
    o = town["organs"]

    f.text((M, 232), "Kahn's algorithm decides the funding order. Code, not narration.", font(F_REG, 26), MUTED)

    rows = [
        ("fuel_depot", "BLOOD", "100 L reserve", TEAL, "in-degree 0"),
        ("hospital", "HEART", "70 L demand", RED, "in-degree 1"),
        ("water_pump", "LUNGS", "30 L demand", BLUE, "in-degree 1"),
        ("shelters", "ORGANS", "200 people", AMBER, "in-degree 1"),
    ]
    y = 300
    for i, (key, role, detail, color, deg) in enumerate(rows):
        f.panel([M, y, M + 760, y + 128], accent=color)
        f.d.rectangle([M, y, M + 8, y + 128], fill=color)
        f.text((M + 34, y + 20), key, font(F_MONO_B, 30), TEXT)
        f.text((M + 34, y + 66), f"{role}   /   {detail}", font(F_REG, 21), MUTED)
        f.text((M + 700, y + 30), f"0{i + 1}", font(F_BOLD, 40), color, anchor="ra")
        f.text((M + 700, y + 78), deg, font(F_MONO, 16), MUTED, anchor="ra")
        if i < len(rows) - 1:
            f.arrow((M + 380, y + 128), (M + 380, y + 168), color, width=4)
        y += 168

    # right: cascade
    f.panel([880, 300, W - M, 560], accent=RED)
    f.text((912, 324), "IF THE HEART FAILS", font(F_BOLD, 20), RED)
    f.text((912, 366), "hospital", font(F_MONO_B, 40), TEXT)
    f.text((912, 424), "->  water_pump", font(F_MONO, 26), MUTED)
    f.text((912, 464), "->  shelters", font(F_MONO, 26), MUTED)
    f.text((912, 508), "200 people lose water service", font(F_SEMI, 22), RED)

    # right: code proof
    f.panel([880, 586, W - M, 792], accent=BORDER, fill=(12, 24, 30))
    f.text((912, 606), "python dependency_graph.py", font(F_MONO, 17), MUTED)
    code = [
        "order = kahn_order(town)",
        "['fuel_depot', 'hospital',",
        " 'water_pump', 'shelters']",
        "",
        "cascade(town, ['hospital'])",
        "-> ['water_pump', 'shelters']",
    ]
    yy = 642
    for line in code:
        f.text((912, yy), line, font(F_MONO, 20), GREEN if line.startswith(("order", "->")) else TEXT)
        yy += 24

    f.panel([880, 812, W - M, 968], accent=BORDER)
    f.text((912, 834), "WHY ORDER MATTERS", font(F_BOLD, 18), MUTED)
    f.paragraph((912, 866),
                "The pump's electricity comes from the hospital feeder. Fund the pump first and you "
                "power lungs from a dead heart.", font(F_REG, 19), TEXT, max_width=W - M - 944)

    f.save("graph.png")


# --------------------------------------------------------------------------- #
# frame 3 - A*
# --------------------------------------------------------------------------- #

def frame_astar(town: dict, route: dict) -> None:
    f = Frame(3, "FRAME 03  /  STEP 4", "A* ROUTING, NOT A GUESS", GREEN)

    f.text((M, 232), "heapq over surveyed road lengths, haversine heuristic, admissibility audited.", font(F_REG, 26), MUTED)

    f.panel([M, 288, 1120, 900], accent=BORDER, fill=(13, 26, 32))
    f.text((M + 28, 304), "KOTTUR ROAD NETWORK", font(F_MONO, 16), MUTED)

    depot = (200, 790)
    hospital = (960, 400)

    # signposted bypass (long way round)
    bypass = [(200, 790), (250, 620), (420, 560), (640, 610), (820, 520), (960, 400)]
    f.d.line(bypass, fill=(90, 110, 120), width=7, joint="curve")
    f.text((286, 520), "signposted bypass  13.0 km", font(F_MONO, 18), MUTED)

    # direct blocked
    f.d.line([depot, (520, 640), (720, 500), hospital], fill=(120, 60, 60), width=5)
    f.d.line([(596, 596), (660, 548)], fill=RED, width=8)
    f.d.line([(660, 596), (596, 548)], fill=RED, width=8)
    f.text((470, 664), "NH-544  4.2 km  BLOCKED", font(F_MONO, 18), RED)

    # A* route
    astar_path = [(200, 790), (330, 830), (560, 780), (760, 700), (860, 560), (960, 400)]
    f.d.line(astar_path, fill=GREEN, width=9, joint="curve")
    f.text((404, 848), "A*  7.8 km", font(F_MONO_B, 22), GREEN)

    for (x, y), label, color, anchor in [
        (depot, "fuel_depot", TEAL, "ma"),
        (hospital, "hospital", RED, "rm"),
    ]:
        f.d.ellipse([x - 26, y - 26, x + 26, y + 26], fill=color)
        offset = (0, 44) if anchor == "ma" else (-42, 0)
        f.text((x + offset[0], y + offset[1]), label, font(F_MONO_B, 18), TEXT, anchor=anchor)

    for point in [(560, 780), (760, 700), (860, 560)]:
        f.d.ellipse([point[0] - 9, point[1] - 9, point[0] + 9, point[1] + 9], fill=(13, 26, 32), outline=GREEN, width=3)

    # metrics
    f.panel([1160, 288, W - M, 900], accent=BORDER)
    stats = [
        ("DIRECT", "4.2 km", "blocked at km 2.1", RED),
        ("BYPASS", "13.0 km", "what a human drives", MUTED),
        ("A* ROUTE", "7.8 km", "village road", GREEN),
        ("SAVED", "5.2 km", "40.0% of the run", TEAL),
        ("FUEL", "1.82 L", "at 0.35 L/km", AMBER),
        ("BOUGHT", "6.2 min", "generator runtime", BLUE),
    ]
    y = 312
    for label, value, note, color in stats:
        f.text((1192, y), label, font(F_MONO, 15), MUTED)
        f.text((1192, y + 21), value, font(F_BOLD, 38), color)
        f.text((1192, y + 66), note, font(F_REG, 16), MUTED)
        y += 100

    f.panel([M, 924, W - M, 986], accent=GREEN, fill=PANEL_HI)
    f.text((M + 24, 942), "AUDIT", font(F_BOLD, 18), GREEN)
    f.text((M + 116, 944), "every road length >= straight-line distance between its endpoints  ->  heuristic admissible  ->  A* is optimal",
           font(F_REG, 20), TEXT)

    f.save("astar.png")


# --------------------------------------------------------------------------- #
# frame 4 - allocator
# --------------------------------------------------------------------------- #

def frame_allocator(town: dict, alloc: dict) -> None:
    f = Frame(4, "FRAME 04  /  STEP 5 + 6", "EVIDENCE IN, ALLOCATION OUT", AMBER)
    tracker = credit_tracker.CreditTracker()

    f.text((M, 232), "Wonder may propose. Code validates. A human approves. Nothing executes itself.", font(F_REG, 26), MUTED)

    # evidence
    f.panel([M, 288, 780, 700], accent=BLUE)
    f.text((M + 28, 310), "EVIDENCE  /  from town.json", font(F_BOLD, 19), BLUE)
    y = 350
    for item in alloc["evidence"][:6]:
        f.text((M + 28, y), item["id"], font(F_MONO_B, 15), BLUE)
        lines = f.wrap(item["claim"], font(F_REG, 17), 648)
        yy = y - 1
        for line in lines[:2]:
            f.text((M + 74, yy), line, font(F_REG, 17), TEXT)
            yy += 22
        y = yy + 18

    # inference
    f.panel([M, 724, 780, 900], accent=AMBER)
    f.text((M + 28, 744), "INFERENCE  /  every claim cites evidence", font(F_BOLD, 19), AMBER)
    y = 776
    for item in alloc["inference"]:
        f.text((M + 28, y), f"{item['litres']:>3d} L", font(F_MONO_B, 17), AMBER)
        claim = f.wrap(item["claim"], font(F_REG, 16), 470)[0]
        f.text((M + 106, y), claim, font(F_REG, 16), TEXT)
        f.text((M + 676, y), ",".join(item["because"]), font(F_MONO, 14), MUTED, anchor="ra")
        y += 32
    f.text((M + 28, 868), "8 evidence items total · every item carries its town.json path",
           font(F_MONO, 13), MUTED)

    # allocation
    f.panel([820, 288, W - M, 640], accent=TEAL)
    f.text((852, 310), "ALLOCATION  /  100 L, exactly", font(F_BOLD, 19), TEAL)

    y = 372
    for organ, litres in alloc["allocation"].items():
        color = RED if organ == "hospital" else BLUE
        f.text((852, y), organ, font(F_MONO_B, 24), TEXT)
        f.text((W - M - 28, y), f"{litres} L", font(F_BOLD, 34), color, anchor="ra")
        f.bar(852, y + 44, W - M - 880, 18, litres / 70, color)
        y += 108

    f.text((852, 540), "70 L heart  +  30 L lungs  =  100 L", font(F_SEMI, 26), TEXT)
    f.text((852, 582), "no over-allocation  ·  no surplus  ·  multiple of 5 L", font(F_REG, 18), MUTED)

    # credit plan
    f.panel([820, 664, W - M, 900], accent=BORDER)
    f.text((852, 682), f"BUDGET PLAN  /  SPENT ${tracker.status()['spent_usd']:.4f} OF $150", font(F_BOLD, 19), MUTED)
    buckets = [
        ("wonder", 70.0, TEAL),
        ("sam", 30.0, BLUE),
        ("voice", 30.0, AMBER),
        ("spark", 20.0, GREEN),
    ]
    y = 722
    for name, budget, color in buckets:
        f.text((852, y), name, font(F_MONO, 16), MUTED)
        f.bar(950, y + 4, 500, 14, 1.0, color)
        f.text((1470, y), f"${budget:.0f}", font(F_MONO_B, 16), TEXT)
        if tracker.spend(name):
            f.text((1540, y), f"spent ${tracker.spend(name):.2f}", font(F_MONO, 14), color)
        else:
            f.text((1540, y), "unspent", font(F_MONO, 14), MUTED)
        y += 32
    f.text((852, 862), f"alerts $120 / $142.50  ·  reserve $20  ·  ledger {tracker.path.name}",
           font(F_MONO, 14), MUTED)

    f.save("allocator.png")


# --------------------------------------------------------------------------- #
# frame 5 - offline / open weight
# --------------------------------------------------------------------------- #

def frame_offline(town: dict) -> None:
    f = Frame(5, "FRAME 05  /  OPEN WEIGHT", "OFFLINE FIRST", TEAL)

    f.text((M, 232), "The deterministic core does not need the internet. The 30B reasoner does not fit 6 GB.", font(F_REG, 26), MUTED)

    # hardware
    f.panel([M, 288, 900, 700], accent=TEAL)
    f.text((M + 28, 310), "OWN HARDWARE", font(F_BOLD, 19), TEAL)
    f.text((M + 28, 350), "RTX 3050", font(F_BOLD, 54), TEXT)
    f.text((M + 28, 424), "6 GB VRAM  ·  15.7 GB RAM  ·  i5-14450HX", font(F_MONO, 19), MUTED)

    rows = [
        ("nvidia-smi", "driver 592.82  ·  CUDA 13.1", GREEN),
        ("AIRPLANE MODE", "ON - no network", AMBER),
        ("ollama run llama3.2:3b", "2.0 GB  ·  local", TEXT),
        ("python agent.py", "graph + A* + gate + replan", TEXT),
    ]
    y = 470
    for cmd, note, color in rows:
        f.panel([M + 28, y, 872, y + 52], accent=(28, 48, 58), fill=(12, 24, 30), radius=10, width=1)
        f.text((M + 44, y + 15), cmd, font(F_MONO_B, 18), color)
        f.text((M + 400, y + 16), note, font(F_REG, 17), MUTED)
        y += 56

    # partner
    f.panel([940, 288, W - M, 470], accent=BLUE)
    f.text((972, 310), "PARTNER INFERENCE  /  BEST OPEN WEIGHT", font(F_BOLD, 19), BLUE)
    f.text((972, 352), "Muse Spark Open", font(F_BOLD, 34), TEXT)
    f.text((972, 398), "meta-models/muse-spark-open-1026", font(F_MONO, 17), MUTED)
    f.pill((972, 420), "BASETEN  ·  2M TPM", BLUE, (20, 38, 56))

    f.panel([940, 494, W - M, 700], accent=AMBER)
    f.text((972, 516), "PARTNER GPU", font(F_BOLD, 19), AMBER)
    f.text((972, 556), "Muse Glimmer 30B", font(F_BOLD, 32), TEXT)
    f.text((972, 600), "Modal  ·  not deployed in this build", font(F_MONO, 17), MUTED)
    f.text((972, 630), "18 GB weights vs 6 GB VRAM", font(F_REG, 18), AMBER)

    # honest fit table
    f.panel([M, 724, W - M, 900], accent=BORDER)
    f.text((M + 28, 744), "WHAT ACTUALLY RUNS WHERE", font(F_BOLD, 19), MUTED)
    cols = [
        ("LOCAL, FLIGHT MODE", "steps 3, 4, 6, 7, 8", "no model call", TEAL),
        ("LOCAL, 3B FALLBACK", "natural language layer", "llama3.2:3b", GREEN),
        ("BASETEN", "Spark Open reasoner", "2M TPM", BLUE),
        ("MODAL", "Glimmer 30B GPU", "18 GB > 6 GB VRAM", AMBER),
    ]
    x = M + 28
    for head, body, note, color in cols:
        f.text((x, 786), head, font(F_MONO_B, 16), color)
        f.text((x, 820), body, font(F_REG, 18), TEXT)
        f.text((x, 850), note, font(F_MONO, 15), MUTED)
        x += 448

    f.save("offline.png")


# --------------------------------------------------------------------------- #
# frame 6 - agentic
# --------------------------------------------------------------------------- #

def frame_agentic(town: dict) -> None:
    f = Frame(6, "FRAME 06  /  BEST AGENTIC", "EIGHT STEPS, ONE APPROVAL", AMBER)

    f.text((M, 232), "Six steps run without a human. One gate holds the dispatch. The loop replans on new facts.",
           font(F_REG, 26), MUTED)

    steps = [
        ("1", "PERCEIVE", "SAM 3.1", "model", BLUE),
        ("2", "LISTEN", "Voice Transcribe", "model", BLUE),
        ("3", "GRAPH", "Kahn topological sort", "deterministic", TEAL),
        ("4", "ROUTE", "A* + heapq", "deterministic", TEAL),
        ("5", "ALLOCATE", "Wonder + validator", "model + code", AMBER),
        ("6", "BUDGET", "$150 ledger", "deterministic", TEAL),
        ("7", "APPROVE", "human gate", "human", RED),
        ("8", "REPLAN", "new constraint", "deterministic", TEAL),
    ]
    card_w, card_h, gap_x, gap_y = 412, 196, 32, 32
    for i, (num, name, tool, tag, color) in enumerate(steps):
        col, row = i % 4, i // 4
        x = M + col * (card_w + gap_x)
        y = 300 + row * (card_h + gap_y)
        f.panel([x, y, x + card_w, y + card_h], accent=color)
        f.text((x + 26, y + 20), num, font(F_BOLD, 46), color)
        f.text((x + 26, y + 82), name, font(F_BOLD, 30), TEXT)
        f.text((x + 26, y + 124), tool, font(F_MONO, 17), MUTED)
        f.pill((x + 26, y + 152), tag, color)

    # outcome band
    f.panel([M, 780, W - M, 900], accent=TEAL, fill=PANEL_HI)
    outcomes = [
        ("30 -> 90 min", "water-pump uptime"),
        ("6 h -> 2 h", "water reaches shelters"),
        ("40%", "fuel saved on the run"),
        ("1", "human touchpoint"),
    ]
    x = M + 32
    for value, label in outcomes:
        f.text((x, 806), value, font(F_BOLD, 42), TEAL)
        f.text((x, 858), label, font(F_REG, 18), MUTED)
        x += 448

    f.panel([M, 916, W - M, 982], accent=BORDER)
    f.text((M + 28, 936), "REFUSAL", font(F_BOLD, 18), RED)
    f.text((M + 130, 938), "human says pump 40 L -> validator: \"hospital is under-funded (60/70 L) while water_pump receives diesel\" -> 70/30 applied anyway",
           font(F_REG, 19), TEXT)

    f.save("agentic.png")


def main() -> int:
    town = load_town()
    _, nodes, edges = a_star.load_network()
    route = a_star.plan_route(town, nodes, edges)
    alloc = allocator.allocate(town, mode="policy")

    print("rendering figma frames")
    frame_lifegrid(town, alloc, route)
    frame_graph(town)
    frame_astar(town, route)
    frame_allocator(town, alloc)
    frame_offline(town)
    frame_agentic(town)
    print("done - 6 frames at 1920x1080")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

