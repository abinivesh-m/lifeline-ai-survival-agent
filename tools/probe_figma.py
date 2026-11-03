import json, urllib.request, urllib.error

URL = "https://mcp.figma.com/mcp"
body = {
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "opencode", "version": "probe"},
    },
}
req = urllib.request.Request(
    URL, data=json.dumps(body).encode(), method="POST",
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    },
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("POST initialize ->", r.status)
        print(r.read()[:400].decode(errors="replace"))
except urllib.error.HTTPError as e:
    print("POST initialize -> HTTP", e.code)
    print("WWW-Authenticate:", e.headers.get("WWW-Authenticate"))
    print("content-type:", e.headers.get("content-type"))
    print(e.read()[:300].decode(errors="replace"))

req2 = urllib.request.Request(URL, method="GET", headers={"Accept": "text/event-stream"})
try:
    with urllib.request.urlopen(req2, timeout=20) as r:
        print("GET sse ->", r.status)
except urllib.error.HTTPError as e:
    print("GET sse -> HTTP", e.code, "|", e.headers.get("allow"))
