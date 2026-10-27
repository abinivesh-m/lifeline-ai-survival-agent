import json, urllib.parse, urllib.request
from pathlib import Path

TITLES = [
    "File:Flooded Marina beach Near Service Road ( 2015 ).jpg",
    "File:Kerala flood 2018.jpg",
    "File:Flood kerala 2018 3.jpg",
    "File:Flood kerala 2018 4.jpg",
    "File:Pala during 2018 Kerala floods 02.jpg",
    "File:Flood affected house (2).jpg",
]
api = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
    "action": "query", "titles": "|".join(TITLES), "prop": "imageinfo",
    "iiprop": "url|size|extmetadata", "iiurlwidth": "1600", "format": "json",
})
req = urllib.request.Request(api, headers={"User-Agent": "LIFELINE-AI-hackathon/1.0 (research)"})
data = json.loads(urllib.request.urlopen(req, timeout=40).read().decode())

out = Path("artifacts/photos"); out.mkdir(parents=True, exist_ok=True)
credits = []
for page in data["query"]["pages"].values():
    title = page["title"]
    ii = page["imageinfo"][0]
    em = ii.get("extmetadata", {})
    name = title.replace("File:", "").rsplit(".", 1)[0]
    safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in name).strip().replace(" ", "_")[:50]
    url = ii.get("thumburl") or ii["url"]
    try:
        r = urllib.request.Request(url, headers={"User-Agent": "LIFELINE-AI-hackathon/1.0 (research)"})
        blob = urllib.request.urlopen(r, timeout=90).read()
        (out / f"{safe}.jpg").write_bytes(blob)
        credits.append({
            "file": f"{safe}.jpg",
            "title": title,
            "source": ii.get("descriptionurl", ""),
            "author": (em.get("Artist", {}).get("value", "") or "").replace("\n", " ")[:200],
            "license": em.get("LicenseShortName", {}).get("value", ""),
            "bytes": len(blob),
            "size": f'{ii["width"]}x{ii["height"]}',
        })
        print(f"  ok {safe}.jpg  {len(blob)//1024} KB  {em.get('LicenseShortName',{}).get('value','')}")
    except Exception as e:
        print(f"  FAIL {title}: {e}")

(out / "CREDITS.json").write_text(json.dumps(credits, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\n{len(credits)} images + CREDITS.json in artifacts/photos/")
