"""HTTP server: WTCHandler, ThreadedHTTPServer, SSE streaming."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any
from urllib.parse import urlparse, parse_qs

from . import ASSETS_DIR
from .config import CONTENT_TYPES, _unit_code_path, detect_language, unit_files, primary_file


_running: dict[str, subprocess.Popen] = {}


def flatten_groups(groups):
    """Recursively flatten nested groups into a flat list."""
    result = []
    for ch in groups:
        result.append(ch)
        result.extend(flatten_groups(ch.get("groups", [])))
    return result


class WTCHandler(SimpleHTTPRequestHandler):
    config: dict[str, Any] | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ASSETS_DIR), **kwargs)

    def _check_origin(self) -> bool:
        """Reject cross-origin requests to dangerous endpoints (CSRF protection)."""
        addr = self.server.server_address
        port = addr[1] if isinstance(addr, tuple) else 0
        allowed = {f"http://localhost:{port}", f"http://127.0.0.1:{port}"}
        origin = self.headers.get("Origin")
        if origin:
            return origin in allowed
        referer = self.headers.get("Referer")
        if referer:
            parsed = urlparse(referer)
            return f"{parsed.scheme}://{parsed.netloc}" in allowed
        return True  # same-origin requests may omit both headers

    def _cfg(self) -> dict[str, Any]:
        cfg = self.__class__.config
        assert cfg is not None
        return cfg

    def do_GET(self):
        cfg = self._cfg()
        units = cfg.get("units", [])
        config_dir = Path(cfg["_config_dir"])
        code_dir = Path(cfg["_code_dir"])
        default_lang = cfg.get("language", "python")

        if self.path == "/api/units":
            result = []
            for u in units:
                uf = unit_files(u, default_lang)
                pf = next((f for f in uf if f["role"] == "primary"), uf[0])
                exp_path = config_dir / "comments" / u["id"] / f"{Path(pf['path']).stem}.json"
                annotated = 0
                if exp_path.exists():
                    try:
                        annotated = len(json.loads(exp_path.read_text()))
                    except (json.JSONDecodeError, OSError):
                        pass
                result.append({
                    "id": u["id"], "title": u["title"], "tagline": u.get("tagline", ""),
                    "description": u.get("description", ""),
                    "learning_objectives": u.get("learning_objectives", []),
                    "exercises": u.get("exercises", []),
                    "file": u["file"], "language": u.get("language", detect_language(u["file"], default_lang)),
                    "files": uf,
                    "annotated_lines": annotated,
                })
            self._json(result)
        elif self.path == "/api/config":
            self._json({
                "title": cfg.get("title", ""),
                "tagline": cfg.get("tagline", ""),
                "repo_url": cfg.get("repo_url", ""),
                "terminology": cfg.get("terminology"),
                "show_credits": cfg.get("show_credits", True),
            })
        elif self.path == "/api/groups":
            self._json(cfg.get("groups", []))
        elif self.path.startswith("/api/code/"):
            parsed = urlparse(self.path)
            unit_id = parsed.path[len("/api/code/"):]
            qs = parse_qs(parsed.query)
            unit = next((u for u in units if u["id"] == unit_id), None)
            if not unit:
                return self._json({"error": "not found"}, 404)
            req_file = qs.get("file", [None])[0]
            if req_file:
                filename = req_file
            else:
                pf = primary_file(unit, default_lang)
                filename = pf["path"]
            p = _unit_code_path(code_dir, unit, filename)
            if p.exists():
                self._json({"code": p.read_text(), "filename": filename,
                             "language": detect_language(filename, default_lang)})
            else:
                self._json({"error": "file not found"}, 404)
        elif self.path.startswith("/api/explanations/"):
            parsed = urlparse(self.path)
            unit_id = parsed.path[len("/api/explanations/"):]
            qs = parse_qs(parsed.query)
            unit = next((u for u in units if u["id"] == unit_id), None)
            if not unit:
                return self._json({})
            req_file = qs.get("file", [None])[0]
            if req_file:
                stem = Path(req_file).stem
            else:
                pf = primary_file(unit, default_lang)
                stem = Path(pf["path"]).stem
            p = config_dir / "comments" / unit["id"] / f"{stem}.json"
            if p.exists():
                try:
                    self._json(json.loads(p.read_text()))
                except (json.JSONDecodeError, OSError) as exc:
                    self._json({"error": f"bad comment file: {exc}"}, 500)
            else:
                self._json({})
        elif self.path.startswith("/api/diagrams/"):
            did = self.path[len("/api/diagrams/"):].replace("..", "").replace("/", "")
            p = config_dir / "diagrams" / f"{did}.mmd"
            if p.exists():
                self._json({"id": did, "source": p.read_text()})
            else:
                self._json({"error": "not found"}, 404)
        elif self.path.startswith("/api/run/"):
            self._run_unit(self.path[len("/api/run/"):])
        elif self.path.startswith("/api/stop/"):
            self._stop_unit(self.path[len("/api/stop/"):])
        elif self.path.split("?")[0] in ("/unit", "/unit.html", "/unit/"):
            self._serve_asset("unit.html", frame_options="DENY")
        elif self.path.split("?")[0] in ("/group", "/group.html", "/group/"):
            self._serve_asset("group.html", frame_options="DENY")
        elif self.path.split("?")[0] in ("/embed", "/embed.html", "/embed/"):
            self._serve_asset("embed.html", embed=True)
        elif self.path.split("?")[0] in ("/", "/index.html"):
            self._serve_asset("index.html", frame_options="DENY")
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/run-modified/"):
            self._run_modified_unit(self.path[len("/api/run-modified/"):])
        elif self.path.startswith("/api/stop/"):
            self._stop_unit(self.path[len("/api/stop/"):])
        else:
            self.send_error(404)

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _kill_running(self, unit_id):
        if unit_id in _running:
            try:
                _running[unit_id].kill()
            except OSError:
                pass
            del _running[unit_id]

    def _run_unit(self, unit_id):
        if not self._check_origin():
            return self._json({"error": "forbidden: cross-origin request"}, 403)
        cfg = self._cfg()
        unit = next((u for u in cfg.get("units", []) if u["id"] == unit_id), None)
        if not unit or "run_command" not in unit:
            return self._json({"error": "not found or no run_command"}, 404)
        code_dir = Path(cfg["_code_dir"])
        work_dir = _unit_code_path(code_dir, unit, unit["file"]).parent
        cmd = unit["run_command"]
        self._kill_running(unit_id)
        try:
            proc = subprocess.Popen(cmd, cwd=work_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, bufsize=1, env={**os.environ, "PYTHONUNBUFFERED": "1"})
        except Exception as e:
            return self._json({"error": str(e)}, 500)
        _running[unit_id] = proc
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
            if proc.stdout:
                for line in proc.stdout:
                    send_event("output", {"text": line})
            proc.wait()
            send_event("status", {"state": "done", "exit_code": proc.returncode})
        except (BrokenPipeError, ConnectionResetError):
            proc.kill()
        finally:
            _running.pop(unit_id, None)

    def _run_modified_unit(self, unit_id):
        """Run a unit with modified code posted by the client."""
        if not self._check_origin():
            return self._json({"error": "forbidden: cross-origin request"}, 403)
        cfg = self._cfg()
        unit = next((u for u in cfg.get("units", []) if u["id"] == unit_id), None)
        if not unit or "run_command" not in unit:
            return self._json({"error": "not found or no run_command"}, 404)
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0 or content_len > 1_000_000:
            return self._json({"error": "invalid content length"}, 400)
        modified_code = self.rfile.read(content_len).decode("utf-8", errors="replace")
        code_dir = Path(cfg["_code_dir"])
        work_dir = _unit_code_path(code_dir, unit, unit["file"]).parent
        code_path = work_dir / unit["file"]
        # Write modified code to a temp file in the unit directory
        suffix = code_path.suffix
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, dir=work_dir, prefix=".wtc_edit_", delete=False
        )
        tmp.write(modified_code)
        tmp.close()
        tmp_path = Path(tmp.name)
        # Build command replacing the original file with the temp file
        cmd = [arg.replace(unit["file"], tmp_path.name) for arg in unit["run_command"]]
        self._kill_running(unit_id)
        try:
            proc = subprocess.Popen(cmd, cwd=work_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, bufsize=1, env={**os.environ, "PYTHONUNBUFFERED": "1"})
        except Exception as e:
            tmp_path.unlink(missing_ok=True)
            return self._json({"error": str(e)}, 500)
        _running[unit_id] = proc
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

        send_event("status", {"state": "running", "cmd": " ".join(cmd), "modified": True})
        try:
            if proc.stdout:
                for line in proc.stdout:
                    send_event("output", {"text": line})
            proc.wait()
            send_event("status", {"state": "done", "exit_code": proc.returncode})
        except (BrokenPipeError, ConnectionResetError):
            proc.kill()
        finally:
            _running.pop(unit_id, None)
            tmp_path.unlink(missing_ok=True)

    def _stop_unit(self, unit_id):
        if not self._check_origin():
            return self._json({"error": "forbidden: cross-origin request"}, 403)
        if unit_id in _running:
            try:
                _running[unit_id].kill()
                _running[unit_id].wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                pass
            _running.pop(unit_id, None)
            self._json({"status": "stopped"})
        else:
            self._json({"status": "not_running"})

    # Cache for analytics snippet
    _analytics_snippet: str | None = None
    _analytics_loaded = False

    @classmethod
    def _load_analytics(cls):
        if cls._analytics_loaded:
            return cls._analytics_snippet
        cls._analytics_loaded = True
        cfg = cls.config or {}
        af = cfg.get("analytics_file")
        if af:
            config_dir = Path(cfg.get("_config_dir", "."))
            p = config_dir / af
            if p.exists():
                cls._analytics_snippet = p.read_text()
        return cls._analytics_snippet

    def _serve_asset(self, filename, frame_options=None, embed=False):
        filepath = ASSETS_DIR / filename
        if filepath.exists():
            content = filepath.read_bytes()
            # Inject analytics before </body>
            snippet = self._load_analytics()
            if snippet and filename.endswith(".html"):
                text = content.decode("utf-8")
                content = text.replace("</body>", snippet + "</body>").encode("utf-8")
            ext = Path(filename).suffix
            ct = CONTENT_TYPES.get(ext, "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(content)))
            if embed:
                self.send_header("Content-Security-Policy", "frame-ancestors *")
            elif frame_options:
                self.send_header("X-Frame-Options", frame_options)
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
