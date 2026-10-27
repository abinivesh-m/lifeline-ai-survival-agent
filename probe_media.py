import base64, json, os, sys, urllib.request, urllib.error, io, wave, struct
sys.path.insert(0, "."); import allocator; allocator.load_env()
BASE = os.environ["META_API_BASE"].rstrip("/"); KEY = os.environ["META_API_KEY"]

def post(path, payload, ctype="application/json"):
    data = json.dumps(payload).encode() if ctype == "application/json" else payload
    req = urllib.request.Request(BASE + path, data=data, method="POST",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, r.read()[:900].decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:900].decode(errors="replace")
    except Exception as e:
        return "ERR", f"{type(e).__name__}: {e}"

img = base64.b64encode(open("figma/graph.png","rb").read()).decode()

print("=== sam-3.1 via /chat/completions (image_url)")
print(*post("/chat/completions", {
    "model": "sam-3.1",
    "messages": [{"role": "user", "content": [
        {"type": "text", "text": "Segment flooded road surface. Return JSON."},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}},
    ]}],
    "max_tokens": 64,
}), sep="\n")

print("\n=== sam-3.1 via /segmentations")
print(*post("/segmentations", {"model": "sam-3.1", "image": f"data:image/png;base64,{img}"}), sep="\n")

# 1 second of silence, 16 kHz mono
buf = io.BytesIO()
with wave.open(buf, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
    w.writeframes(b"\x00\x00" * 16000)
audio = buf.getvalue()
open("_probe.wav","wb").write(audio)

boundary = "----lifelineprobe"
def part(name, value):
    return (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n').encode()
body = part("model", "muse-voice-transcribe-1.0")
body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="probe.wav"\r\n'
         f'Content-Type: audio/wav\r\n\r\n').encode() + audio + b"\r\n"
body += f"--{boundary}--\r\n".encode()

print("\n=== voice via /audio/transcriptions")
print(*post("/audio/transcriptions", body, f"multipart/form-data; boundary={boundary}"), sep="\n")
