"""HTTP server: WTCHandler, ThreadedHTTPServer, SSE streaming."""

import json
import os
import subprocess
import tempfile
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingMixIn

from . import ASSETS_DIR
from .config import CONTENT_TYPES, detect_language


_running: dict[str, subprocess.Popen] = {}


class WTCHandler(SimpleHTTPRequestHandler):
    config = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ASSETS_DIR), **kwargs)

    def do_GET(self):
        cfg = self.__class__.config
        labs = cfg.get("labs", [])
        config_dir = Path(cfg["_config_dir"])
        code_dir = Path(cfg["_code_dir"])
        default_lang = cfg.get("language", "python")

        if self.path == "/api/labs":
            result = []
            for l in labs:
                exp_path = config_dir / "comments" / l["id"] / f"{Path(l['file']).stem}.json"
                annotated = 0
                if exp_path.exists():
                    try:
                        annotated = len(json.loads(exp_path.read_text()))
                    except (json.JSONDecodeError, OSError):
                        pass
                result.append({
                    "id": l["id"], "title": l["title"], "tagline": l.get("tagline", ""),
                    "description": l.get("description", ""),
                    "learning_objectives": l.get("learning_objectives", []),
                    "exercises": l.get("exercises", []),
                    "file": l["file"], "language": l.get("language", detect_language(l["file"], default_lang)),
                    "annotated_lines": annotated,
                })
            self._json(result)
        elif self.path == "/api/config":
            self._json({
                "title": cfg.get("title", ""),
                "tagline": cfg.get("tagline", ""),
                "repo_url": cfg.get("repo_url", ""),
            })
        elif self.path == "/api/chapters":
            self._json(cfg.get("chapters", []))
        elif self.path.startswith("/api/code/"):
            lab_id = self.path[len("/api/code/"):]
            lab = next((l for l in labs if l["id"] == lab_id), None)
            if not lab:
                return self._json({"error": "not found"}, 404)
            p = code_dir / lab["id"] / lab["file"]
            if p.exists():
                self._json({"code": p.read_text(), "filename": lab["file"],
                             "language": lab.get("language", detect_language(lab["file"], default_lang))})
            else:
                self._json({"error": "file not found"}, 404)
        elif self.path.startswith("/api/explanations/"):
            lab_id = self.path[len("/api/explanations/"):]
            lab = next((l for l in labs if l["id"] == lab_id), None)
            if not lab:
                return self._json({})
            p = config_dir / "comments" / lab["id"] / f"{Path(lab['file']).stem}.json"
            self._json(json.loads(p.read_text()) if p.exists() else {})
        elif self.path.startswith("/api/diagrams/"):
            did = self.path[len("/api/diagrams/"):].replace("..", "").replace("/", "")
            p = config_dir / "diagrams" / f"{did}.mmd"
            if p.exists():
                self._json({"id": did, "source": p.read_text()})
            else:
                self._json({"error": "not found"}, 404)
        elif self.path.startswith("/api/run/"):
            self._run_lab(self.path[len("/api/run/"):])
        elif self.path.startswith("/api/stop/"):
            self._stop_lab(self.path[len("/api/stop/"):])
        elif self.path.split("?")[0] in ("/lab", "/lab.html", "/lab/"):
            self._serve_asset("lab.html")
        elif self.path.split("?")[0] in ("/chapter", "/chapter.html", "/chapter/"):
            self._serve_asset("chapter.html")
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/run-modified/"):
            self._run_modified_lab(self.path[len("/api/run-modified/"):])
        elif self.path.startswith("/api/stop/"):
            self._stop_lab(self.path[len("/api/stop/"):])
        else:
            self.send_error(404)

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _run_lab(self, lab_id):
        cfg = self.__class__.config
        lab = next((l for l in cfg.get("labs", []) if l["id"] == lab_id), None)
        if not lab or "run_command" not in lab:
            return self._json({"error": "not found or no run_command"}, 404)
        work_dir = Path(cfg["_code_dir"]) / lab["id"]
        cmd = lab["run_command"]
        if lab_id in _running:
            try: _running[lab_id].kill()
            except OSError: pass
            del _running[lab_id]
        try:
            proc = subprocess.Popen(cmd, cwd=work_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
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
            except (BrokenPipeError, ConnectionResetError): proc.kill()
        send_event("status", {"state": "running", "cmd": " ".join(cmd)})
        try:
            for line in proc.stdout:
                send_event("output", {"text": line})
            proc.wait()
            send_event("status", {"state": "done", "exit_code": proc.returncode})
        except (BrokenPipeError, ConnectionResetError): proc.kill()
        finally: _running.pop(lab_id, None)

    def _run_modified_lab(self, lab_id):
        """Run a lab with modified code posted by the client."""
        cfg = self.__class__.config
        lab = next((l for l in cfg.get("labs", []) if l["id"] == lab_id), None)
        if not lab or "run_command" not in lab:
            return self._json({"error": "not found or no run_command"}, 404)
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0 or content_len > 1_000_000:
            return self._json({"error": "invalid content length"}, 400)
        modified_code = self.rfile.read(content_len).decode("utf-8", errors="replace")
        work_dir = Path(cfg["_code_dir"]) / lab["id"]
        code_path = work_dir / lab["file"]
        # Write modified code to a temp file in the lab directory
        suffix = code_path.suffix
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, dir=work_dir, prefix=".wtc_edit_", delete=False
        )
        tmp.write(modified_code)
        tmp.close()
        tmp_path = Path(tmp.name)
        # Build command replacing the original file with the temp file
        cmd = [tmp_path.name if arg == lab["file"] else arg for arg in lab["run_command"]]
        if lab_id in _running:
            try: _running[lab_id].kill()
            except OSError: pass
            del _running[lab_id]
        try:
            proc = subprocess.Popen(cmd, cwd=work_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, bufsize=1, env={**os.environ, "PYTHONUNBUFFERED": "1"})
        except Exception as e:
            tmp_path.unlink(missing_ok=True)
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
            except (BrokenPipeError, ConnectionResetError): proc.kill()
        send_event("status", {"state": "running", "cmd": " ".join(cmd), "modified": True})
        try:
            for line in proc.stdout:
                send_event("output", {"text": line})
            proc.wait()
            send_event("status", {"state": "done", "exit_code": proc.returncode})
        except (BrokenPipeError, ConnectionResetError): proc.kill()
        finally:
            _running.pop(lab_id, None)
            tmp_path.unlink(missing_ok=True)

    def _stop_lab(self, lab_id):
        if lab_id in _running:
            try: _running[lab_id].kill(); _running[lab_id].wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired): pass
            _running.pop(lab_id, None)
            self._json({"status": "stopped"})
        else:
            self._json({"status": "not_running"})

    def _serve_asset(self, filename):
        filepath = ASSETS_DIR / filename
        if filepath.exists():
            content = filepath.read_bytes()
            ext = Path(filename).suffix
            ct = CONTENT_TYPES.get(ext, "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
