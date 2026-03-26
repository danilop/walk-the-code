"""walk-the-code CLI entry points."""

import hashlib
import json
import os
import subprocess
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingMixIn


def _line_hash(text):
    return hashlib.sha256(text.strip().encode()).hexdigest()[:8]

from . import ASSETS_DIR

EXT_TO_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
    ".rs": "rust", ".go": "go", ".java": "java",
}


def detect_language(filename, fallback="python"):
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    return EXT_TO_LANG.get(ext, fallback)


def load_config(config_path):
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text())
    config_dir = config_path.parent
    config["_config_dir"] = str(config_dir)
    config["_code_dir"] = str((config_dir / config.get("code_dir", ".")).resolve())
    return config


_running: dict[str, subprocess.Popen] = {}

CONTENT_TYPES = {
    ".html": "text/html", ".css": "text/css", ".js": "application/javascript",
    ".json": "application/json", ".mjs": "application/javascript",
}


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
            self._json([{
                "id": l["id"], "title": l["title"], "tagline": l.get("tagline", ""),
                "description": l.get("description", ""),
                "file": l["file"], "language": l.get("language", detect_language(l["file"], default_lang)),
            } for l in labs])
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


def serve():
    """CLI entry point: walk-the-code serve [port] [--config path]"""
    args = sys.argv[1:]
    port = 8000
    config_path = "config.json"
    i = 0
    while i < len(args):
        if args[i] == "--config" and i + 1 < len(args):
            config_path = args[i + 1]; i += 2
        elif args[i].isdigit():
            port = int(args[i]); i += 1
        else:
            i += 1

    config = load_config(config_path)
    WTCHandler.config = config

    try:
        server = ThreadedHTTPServer(("localhost", port), WTCHandler)
    except OSError as e:
        if "Address already in use" in str(e) or getattr(e, "errno", 0) == 48:
            print(f"Error: port {port} is already in use. Try: walk-the-code serve {port + 1}")
            sys.exit(1)
        raise
    print(f"walk-the-code running at http://localhost:{port}")
    print(f"  config: {config_path}")
    print(f"  code_dir: {config['_code_dir']}")
    print(f"  labs: {len(config.get('labs', []))}")
    print(f"  chapters: {len(config.get('chapters', []))}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


def build():
    """CLI entry point: walk-the-code build [config_path]"""
    config_path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "config.json"
    config = load_config(config_path)
    config_dir = Path(config["_config_dir"])
    code_dir = Path(config["_code_dir"])
    default_lang = config.get("language", "python")

    labs = []
    for lab in config.get("labs", []):
        code_path = code_dir / lab["id"] / lab["file"]
        stem = Path(lab["file"]).stem
        exp_path = config_dir / "comments" / lab["id"] / f"{stem}.json"
        labs.append({
            "id": lab["id"], "title": lab["title"], "tagline": lab.get("tagline", ""),
            "description": lab.get("description", ""),
            "file": lab["file"],
            "language": lab.get("language", detect_language(lab["file"], default_lang)),
            "code": code_path.read_text() if code_path.exists() else "",
            "explanations": json.loads(exp_path.read_text()) if exp_path.exists() else {},
        })

    diagrams_dir = config_dir / "diagrams"
    diagrams = {}
    if diagrams_dir.exists():
        for mmd in diagrams_dir.glob("*.mmd"):
            diagrams[mmd.stem] = mmd.read_text()

    chapters = config.get("chapters", [])

    # --- Validation ---
    warnings = []
    errors = []
    referenced_diagrams = set()

    for lab_entry in labs:
        lid = lab_entry["id"]
        code_lines = lab_entry["code"].split("\n") if lab_entry["code"] else []
        total_lines = len(code_lines)
        explanations = lab_entry.get("explanations", {})

        for line_str, entry in explanations.items():
            line_num = int(line_str)
            # Out-of-range line numbers
            if line_num < 1 or line_num > total_lines:
                errors.append(f"{lid}: annotation for line {line_num} but code has only {total_lines} lines")
            # Empty text
            text = entry.get("text", "") if isinstance(entry, dict) else entry
            if not text or not text.strip():
                warnings.append(f"{lid}: empty annotation text at line {line_num}")
            # Missing diagram references
            if isinstance(entry, dict) and entry.get("diagram"):
                diag_id = entry["diagram"]
                referenced_diagrams.add(diag_id)
                if diag_id not in diagrams:
                    errors.append(f"{lid}: line {line_num} references diagram '{diag_id}' but no {diag_id}.mmd found")
            # Highlight without diagram
            if isinstance(entry, dict) and entry.get("highlight") and not entry.get("diagram"):
                warnings.append(f"{lid}: line {line_num} has highlight but no diagram reference")
            # Stale hash detection
            if isinstance(entry, dict) and entry.get("hash") and 1 <= line_num <= total_lines:
                expected = _line_hash(code_lines[line_num - 1])
                if entry["hash"] != expected:
                    warnings.append(f"{lid}: line {line_num} hash mismatch (annotation may be outdated)")

    # Chapter lab and diagram references
    all_lab_ids = {l["id"] for l in labs}
    for ch in chapters:
        for lab_id in ch.get("labs", []):
            if lab_id not in all_lab_ids:
                errors.append(f"Chapter '{ch['id']}': references lab '{lab_id}' which is not in the labs list")
        comp_diag = ch.get("comparison_diagram")
        if comp_diag:
            referenced_diagrams.add(comp_diag)
            if comp_diag not in diagrams:
                errors.append(f"Chapter '{ch['id']}': comparison_diagram '{comp_diag}' not found in diagrams/")

    # Orphaned diagram files
    orphaned = set(diagrams.keys()) - referenced_diagrams
    # Exclude diagrams referenced in chapter inline definitions
    for ch in chapters:
        ch_diag = ch.get("diagram", "")
        for d in orphaned.copy():
            if d in ch_diag:
                orphaned.discard(d)
    if orphaned:
        warnings.append(f"Orphaned diagram files not referenced by any annotation: {', '.join(sorted(orphaned))}")

    stale = [w for w in warnings if "hash mismatch" in w]
    other_warnings = [w for w in warnings if "hash mismatch" not in w]
    if stale:
        print(f"\n  Stale annotations ({len(stale)}) — run add_hashes.py to fix:")
        for w in stale:
            print(f"    ~ {w}")
    if other_warnings:
        print(f"\n  Warnings ({len(other_warnings)}):")
        for w in other_warnings:
            print(f"    - {w}")
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors:
            print(f"    ! {e}")

    output_dir = config_dir / "data"
    output_dir.mkdir(exist_ok=True)
    bundle = {
        "config": {
            "title": config.get("title", ""),
            "tagline": config.get("tagline", ""),
            "repo_url": config.get("repo_url", ""),
        },
        "labs": labs, "diagrams": diagrams, "chapters": chapters,
    }
    output_path = output_dir / "labs.json"
    output_path.write_text(json.dumps(bundle))
    print(f"\nBuilt {output_path} ({len(labs)} labs, {len(chapters)} chapters, {len(diagrams)} diagrams, {output_path.stat().st_size / 1024:.0f} KB)")
    if errors:
        print(f"\nBuild completed with {len(errors)} error(s). Fix them to ensure the tutorial works correctly.")
        sys.exit(1)
