import json, urllib.parse, urllib.request
from pathlib import Path

TITLES = [
    "File:Aerial view of Chennai during floods.jpg",
    "File:Aerial view of Chennai during floods - 2.jpg",
    "File:An aerial view of rain hit area in Chennai, Tamil Nadu on December 03, 2015.jpg",
]
api = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
    "action": "query", "titles": "|".join(TITLES), "prop": "imageinfo",
    "iiprop": "url|size|extmetadata", "iiurlwidth": "1600", "format": "json",
})
req = urllib.request.Request(api, headers={"User-Agent": "LIFELINE-AI-hackathon/1.0 (research)"})
data = json.loads(urllib.request.urlopen(req, timeout=40).read().decode())

out = Path("artifacts/photos"); out.mkdir(parents=True, exist_ok=True)
credits = json.loads((out / "CREDITS.json").read_text(encoding="utf-8"))
have = {c["file"] for c in credits}

for page in data["query"]["pages"].values():
    ii = page["imageinfo"][0]; em = ii.get("extmetadata", {})
    safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in page["title"].replace("File:", "").rsplit(".", 1)[0]).strip().replace(" ", "_")[:50]
    fname = f"{safe}.jpg"
    if fname in have:
        print("  skip", fname); continue
    url = ii.get("thumburl") or ii["url"]
    r = urllib.request.Request(url, headers={"User-Agent": "LIFELINE-AI-hackathon/1.0 (research)"})
    blob = urllib.request.urlopen(r, timeout=90).read()
    (out / fname).write_bytes(blob)
    credits.append({"file": fname, "title": page["title"], "source": ii.get("descriptionurl", ""),
                    "author": (em.get("Artist", {}).get("value", "") or "").replace("\n", " ")[:200],
                    "license": em.get("LicenseShortName", {}).get("value", ""),
                    "bytes": len(blob), "size": f'{ii["width"]}x{ii["height"]}'})
    print(f"  ok {fname}  {len(blob)//1024} KB  {em.get('LicenseShortName',{}).get('value','')}")

(out / "CREDITS.json").write_text(json.dumps(credits, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"credits: {len(credits)} entries")
