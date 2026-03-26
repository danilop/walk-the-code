#!/usr/bin/env python3
"""walk-the-code — local server for interactive code tutorials.

Reads config.json to discover code samples, serves explanations from
comments/ mirror structure, diagrams from diagrams/, and optionally
executes labs via SSE streaming.

Usage:
    python server.py [port] [--config path/to/config.json]
"""

import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingMixIn

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def find_arg(flag, default=None):
    for i, a in enumerate(sys.argv[1:], 1):
        if a == flag and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default

PORT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8000
CONFIG_PATH = Path(find_arg("--config", "config.json"))
ROOT = Path(__file__).resolve().parent
CONFIG_DIR = CONFIG_PATH.resolve().parent

config = json.loads(CONFIG_PATH.read_text())
CODE_DIR = (CONFIG_DIR / config.get("code_dir", ".")).resolve()
LABS = config.get("labs", [])
DEFAULT_LANG = config.get("language", "python")

EXT_TO_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
    ".rs": "rust", ".go": "go", ".java": "java",
}

def detect_language(filename, fallback=None):
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    return EXT_TO_LANG.get(ext, fallback or DEFAULT_LANG)

# Track running processes
_running: dict[str, subprocess.Popen] = {}


class WTCHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path == "/api/labs":
            self._json([{
                "id": l["id"], "title": l["title"], "tagline": l.get("tagline", ""),
                "file": l["file"], "language": l.get("language", detect_language(l["file"])),
            } for l in LABS])
        elif self.path.startswith("/api/code/"):
            self._serve_code(self.path[len("/api/code/"):])
        elif self.path.startswith("/api/explanations/"):
            self._serve_explanations(self.path[len("/api/explanations/"):])
        elif self.path.startswith("/api/diagrams/"):
            self._serve_diagram(self.path[len("/api/diagrams/"):])
        elif self.path.startswith("/api/run/"):
            self._run_lab(self.path[len("/api/run/"):])
        elif self.path.startswith("/api/stop/"):
            self._stop_lab(self.path[len("/api/stop/"):])
        elif self.path.startswith("/lab/") or self.path.startswith("/lab.html"):
            self._serve_file("lab.html")
        else:
            super().do_GET()

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _serve_code(self, lab_id):
        lab = next((l for l in LABS if l["id"] == lab_id), None)
        if not lab:
            return self._json({"error": "not found"}, 404)
        code_path = CODE_DIR / lab["id"] / lab["file"]
        if code_path.exists():
            self._json({"code": code_path.read_text(), "filename": lab["file"],
                         "language": lab.get("language", detect_language(lab["file"]))})
        else:
            self._json({"error": "file not found"}, 404)

    def _serve_explanations(self, lab_id):
        lab = next((l for l in LABS if l["id"] == lab_id), None)
        if not lab:
            return self._json({})
        exp_path = CONFIG_DIR / "comments" / lab["id"] / f"{Path(lab['file']).stem}.json"
        if exp_path.exists():
            self._json(json.loads(exp_path.read_text()))
        else:
            self._json({})

    def _serve_diagram(self, diagram_id):
        diagram_id = diagram_id.replace("..", "").replace("/", "")
        path = CONFIG_DIR / "diagrams" / f"{diagram_id}.mmd"
        if path.exists():
            self._json({"id": diagram_id, "source": path.read_text()})
        else:
            self._json({"error": "not found"}, 404)

    def _run_lab(self, lab_id):
        lab = next((l for l in LABS if l["id"] == lab_id), None)
        if not lab or "run_command" not in lab:
            return self._json({"error": "not found or no run_command"}, 404)
        work_dir = CODE_DIR / lab["id"]
        cmd = lab["run_command"]

        if lab_id in _running:
            try: _running[lab_id].kill()
            except OSError: pass
            del _running[lab_id]

        try:
            proc = subprocess.Popen(
                cmd, cwd=work_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, env={**os.environ, "PYTHONUNBUFFERED": "1"})
        except Exception as e:
            return self._json({"error": str(e)}, 500)

        _running[lab_id] = proc
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def send_event(event, data):
            try:
                self.wfile.write(f"event: {event}\ndata: {json.dumps(data)}\n\n".encode())
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                proc.kill()

        send_event("status", {"state": "running", "cmd": " ".join(cmd)})
        try:
            for line in proc.stdout:
                send_event("output", {"text": line})
            proc.wait()
            send_event("status", {"state": "done", "exit_code": proc.returncode})
        except (BrokenPipeError, ConnectionResetError):
            proc.kill()
        finally:
            _running.pop(lab_id, None)

    def _stop_lab(self, lab_id):
        if lab_id in _running:
            try:
                _running[lab_id].kill()
                _running[lab_id].wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired): pass
            _running.pop(lab_id, None)
            self._json({"status": "stopped"})
        else:
            self._json({"status": "not_running"})

    def _serve_file(self, filename):
        filepath = ROOT / filename
        if filepath.exists():
            content = filepath.read_bytes()
            ct = "text/html" if filename.endswith(".html") else "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    try:
        server = ThreadedHTTPServer(("localhost", PORT), WTCHandler)
    except OSError as e:
        if "Address already in use" in str(e) or getattr(e, "errno", 0) == 48:
            print(f"Error: port {PORT} is already in use. Try: python server.py {PORT + 1}")
            sys.exit(1)
        raise
    print(f"walk-the-code running at http://localhost:{PORT}")
    print(f"  config: {CONFIG_PATH}")
    print(f"  code_dir: {CODE_DIR}")
    print(f"  labs: {len(LABS)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
