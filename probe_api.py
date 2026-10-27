import json, os, sys, urllib.request, urllib.error
sys.path.insert(0, "."); import allocator; allocator.load_env()
BASE = os.environ["META_API_BASE"].rstrip("/"); KEY = os.environ["META_API_KEY"]

def call(path, payload=None, method="GET"):
    url = BASE + path
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, r.read()[:700].decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:700].decode(errors="replace")
    except Exception as e:
        return "ERR", f"{type(e).__name__}: {e}"

for m in ("sam-3.1", "muse-voice-transcribe-1.0"):
    print(f"=== GET /models/{m}")
    print(*call(f"/models/{m}"), sep="\n")
print("=== GET /openapi.json")
print(*call("/openapi.json")[:1], str(call("/openapi.json")[1])[:200])
print("=== tiny chat completions muse-spark-1.3")
print(*call("/chat/completions", {"model":"muse-spark-1.3",
    "messages":[{"role":"user","content":"Reply with the single word: ready"}],
    "max_tokens":8,"temperature":0}, "POST"), sep="\n")
