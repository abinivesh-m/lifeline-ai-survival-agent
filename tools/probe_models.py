import json, os, urllib.request, urllib.error, sys
sys.path.insert(0, ".")
import allocator
allocator.load_env()

def get(url, key, label):
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=40) as r:
            body = json.loads(r.read().decode())
        ids = [m.get("id") for m in body.get("data", [])]
        print(f"{label}: HTTP {r.status}  {len(ids)} models")
        for i in ids: print("   ", i)
    except urllib.error.HTTPError as e:
        print(f"{label}: HTTP {e.code}  {e.read()[:300].decode(errors='replace')}")
    except Exception as e:
        print(f"{label}: {type(e).__name__}: {e}")

get(os.environ["META_API_BASE"].rstrip("/") + "/models", os.environ["META_API_KEY"], "META")
get(os.environ.get("BASETEN_BASE_URL","https://inference.baseten.co/v1").rstrip("/") + "/models",
    os.environ.get("BASETEN_API_KEY",""), "BASETEN")
