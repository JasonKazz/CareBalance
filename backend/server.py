"""Local starter server. Run from any directory with Python 3.9+."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/health":
            body = json.dumps({"status": "ok", "simulationImplemented": False}).encode()
            content_type = "application/json"
        elif path in ASSETS:
            filename, content_type = ASSETS[path]
            body = (FRONTEND / filename).read_bytes()
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # Do not log submitted paths or query strings.

if __name__ == "__main__":
    print("CareBalance starter: http://127.0.0.1:3200", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 3200), Handler).serve_forever()
