import base64, json, os, sys, urllib.request, urllib.error
sys.path.insert(0, "."); import allocator; allocator.load_env()
BASE = os.environ["META_API_BASE"].rstrip("/"); KEY = os.environ["META_API_KEY"]

def post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()[:1200].decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:1200].decode(errors="replace")
    except Exception as e:
        return "ERR", f"{type(e).__name__}: {e}"

img = base64.b64encode(open("figma/graph.png","rb").read()).decode()

print("=== /responses  sam-3.1  (input_image)")
print(*post("/responses", {
    "model": "sam-3.1",
    "input": [{"role": "user", "content": [
        {"type": "input_text", "text": "Describe what this image contains in one sentence."},
        {"type": "input_image", "image_url": f"data:image/png;base64,{img}"},
    ]}],
    "max_output_tokens": 128,
}), sep="\n")

aura = base64.b64encode(open("_probe.wav","rb").read()).decode()
print("\n=== /responses  muse-voice-transcribe-1.0  (input_audio)")
print(*post("/responses", {
    "model": "muse-voice-transcribe-1.0",
    "input": [{"role": "user", "content": [
        {"type": "input_audio", "input_audio": {"data": aura, "format": "wav"}},
    ]}],
}), sep="\n")
