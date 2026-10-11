"""Single local server: static frontend and bounded, deterministic JSON API."""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from backend.simulation.engine import analyze, SCHEMA

ASSETS = {"/": ("frontend/index.html", "text/html; charset=utf-8"),
          "/styles.css": ("frontend/styles.css", "text/css; charset=utf-8"),
          "/app.js": ("frontend/app.js", "text/javascript; charset=utf-8")}
MAX_BODY = 16384

class Handler(BaseHTTPRequestHandler):
    def send_body(self, status, body, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, value):
        self.send_body(status, json.dumps(value, allow_nan=False).encode())

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/health":
            return self.send_json(200, {"status": "ok", "simulationImplemented": True})
        if path == "/api/schema":
            return self.send_json(200, SCHEMA)
        if path == "/api/example":
            return self.send_json(200, json.loads((ROOT / "data/synthetic/community-clinic.json").read_text()))
        if path in ASSETS:
            filename, content_type = ASSETS[path]
            return self.send_body(200, (ROOT / filename).read_bytes(), content_type)
        self.send_json(404, {"error": "Not found."})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/analyze":
            return self.send_json(404, {"error": "Not found."})
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self.send_json(415, {"error": "Send application/json."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                return self.send_json(413, {"error": "Scenario must be between 1 and 16384 bytes."})
            self.connection.settimeout(5)
            data = json.loads(self.rfile.read(length))
            result = analyze(data)
        except (ValueError, UnicodeError, OverflowError, RecursionError):
            return self.send_json(400, {"error": "Invalid scenario. Check all fields against their displayed limits."})
        except TimeoutError:
            return self.send_json(408, {"error": "Request timed out."})
        self.send_json(200, result)

    def log_message(self, format, *args):
        pass  # Do not log potentially sensitive scenario inputs or URLs.

if __name__ == "__main__":
    print("CareBalance: http://127.0.0.1:3200", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 3200), Handler).serve_forever()
