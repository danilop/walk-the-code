"""Comprehensive test suite for the walk-the-code platform."""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

# Ensure the src directory is on the import path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from walk_the_code.config import EXT_TO_LANG, CONTENT_TYPES, _line_hash, detect_language, load_config
from walk_the_code.server import WTCHandler, ThreadedHTTPServer

EXAMPLE_DIR = Path(__file__).resolve().parent.parent / "example"


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------
class TestLineHash(unittest.TestCase):
    """Tests for _line_hash."""

    def test_deterministic(self):
        self.assertEqual(_line_hash("hello"), _line_hash("hello"))

    def test_strips_whitespace(self):
        self.assertEqual(_line_hash("  hello  "), _line_hash("hello"))

    def test_length(self):
        h = _line_hash("anything")
        self.assertEqual(len(h), 8)

    def test_hex_chars(self):
        h = _line_hash("test")
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    def test_different_inputs_differ(self):
        self.assertNotEqual(_line_hash("alpha"), _line_hash("beta"))

    def test_empty_string(self):
        h = _line_hash("")
        self.assertEqual(len(h), 8)

    def test_matches_sha256_prefix(self):
        text = "some code line"
        expected = hashlib.sha256(text.strip().encode()).hexdigest()[:8]
        self.assertEqual(_line_hash(text), expected)


class TestDetectLanguage(unittest.TestCase):
    """Tests for detect_language."""

    def test_python(self):
        self.assertEqual(detect_language("main.py"), "python")

    def test_javascript(self):
        self.assertEqual(detect_language("app.js"), "javascript")

    def test_typescript(self):
        self.assertEqual(detect_language("index.ts"), "typescript")

    def test_tsx(self):
        self.assertEqual(detect_language("Component.tsx"), "typescript")

    def test_java(self):
        self.assertEqual(detect_language("Pi.java"), "java")

    def test_rust(self):
        self.assertEqual(detect_language("main.rs"), "rust")

    def test_go(self):
        self.assertEqual(detect_language("main.go"), "go")

    def test_c_source(self):
        self.assertEqual(detect_language("util.c"), "c")

    def test_c_header(self):
        self.assertEqual(detect_language("util.h"), "c")

    def test_cpp_cc(self):
        self.assertEqual(detect_language("main.cc"), "cpp")

    def test_cpp_cpp(self):
        self.assertEqual(detect_language("main.cpp"), "cpp")

    def test_cpp_cxx(self):
        self.assertEqual(detect_language("main.cxx"), "cpp")

    def test_cpp_hpp(self):
        self.assertEqual(detect_language("util.hpp"), "cpp")

    def test_unknown_extension_uses_fallback(self):
        self.assertEqual(detect_language("file.xyz"), "python")

    def test_custom_fallback(self):
        self.assertEqual(detect_language("file.xyz", fallback="ruby"), "ruby")

    def test_no_extension_uses_fallback(self):
        self.assertEqual(detect_language("Makefile"), "python")

    def test_no_extension_custom_fallback(self):
        self.assertEqual(detect_language("Makefile", fallback="bash"), "bash")


class TestExtToLang(unittest.TestCase):
    """Tests for the EXT_TO_LANG mapping completeness."""

    def test_known_extensions_count(self):
        self.assertGreaterEqual(len(EXT_TO_LANG), 11)

    def test_all_values_are_strings(self):
        for ext, lang in EXT_TO_LANG.items():
            self.assertIsInstance(ext, str)
            self.assertIsInstance(lang, str)
            self.assertTrue(ext.startswith("."), f"{ext} should start with a dot")


class TestContentTypes(unittest.TestCase):
    """Tests for the CONTENT_TYPES mapping."""

    def test_html(self):
        self.assertEqual(CONTENT_TYPES[".html"], "text/html")

    def test_css(self):
        self.assertEqual(CONTENT_TYPES[".css"], "text/css")

    def test_js(self):
        self.assertEqual(CONTENT_TYPES[".js"], "application/javascript")

    def test_json(self):
        self.assertEqual(CONTENT_TYPES[".json"], "application/json")


class TestLoadConfig(unittest.TestCase):
    """Tests for load_config."""

    def test_load_example_config(self):
        cfg = load_config(EXAMPLE_DIR / "config.json")
        self.assertEqual(cfg["title"], "Monte Carlo Pi")
        self.assertIn("_config_dir", cfg)
        self.assertIn("_code_dir", cfg)

    def test_config_dir_is_resolved(self):
        cfg = load_config(EXAMPLE_DIR / "config.json")
        self.assertEqual(cfg["_config_dir"], str(EXAMPLE_DIR.resolve()))

    def test_code_dir_respects_code_dir_field(self):
        cfg = load_config(EXAMPLE_DIR / "config.json")
        expected = str((EXAMPLE_DIR / "samples").resolve())
        self.assertEqual(cfg["_code_dir"], expected)

    def test_labs_present(self):
        cfg = load_config(EXAMPLE_DIR / "config.json")
        self.assertEqual(len(cfg["labs"]), 2)
        ids = [l["id"] for l in cfg["labs"]]
        self.assertIn("monte_carlo_python", ids)
        self.assertIn("monte_carlo_java", ids)

    def test_missing_config_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_config("/nonexistent/path/config.json")

    def test_invalid_json_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {{{")
            f.flush()
            try:
                with self.assertRaises(json.JSONDecodeError):
                    load_config(f.name)
            finally:
                os.unlink(f.name)

    def test_empty_config(self):
        """A config with no labs or code_dir should still produce _config_dir and _code_dir."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({}, f)
            f.flush()
            try:
                cfg = load_config(f.name)
                self.assertIn("_config_dir", cfg)
                self.assertIn("_code_dir", cfg)
                # With no code_dir key, defaults to the config directory itself
                self.assertEqual(cfg["_config_dir"], cfg["_code_dir"])
            finally:
                os.unlink(f.name)

    def test_code_dir_default_when_missing(self):
        """When code_dir is absent, _code_dir should equal the config directory."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"title": "Test"}, f)
            f.flush()
            try:
                cfg = load_config(f.name)
                self.assertEqual(cfg["_config_dir"], cfg["_code_dir"])
            finally:
                os.unlink(f.name)


# ---------------------------------------------------------------------------
# Server tests
# ---------------------------------------------------------------------------
class TestServer(unittest.TestCase):
    """Tests for the WTC HTTP server and its API endpoints."""

    @classmethod
    def setUpClass(cls):
        """Start a test server on a random port."""
        cfg = load_config(EXAMPLE_DIR / "config.json")
        WTCHandler.config = cfg

        # Port 0 lets the OS pick a free port
        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), WTCHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def _get(self, path):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode()
        conn.close()
        return resp.status, body

    def _get_json(self, path):
        status, body = self._get(path)
        return status, json.loads(body)

    # /api/config
    def test_api_config(self):
        status, data = self._get_json("/api/config")
        self.assertEqual(status, 200)
        self.assertEqual(data["title"], "Monte Carlo Pi")
        self.assertIn("tagline", data)
        self.assertIn("repo_url", data)

    # /api/labs
    def test_api_labs(self):
        status, data = self._get_json("/api/labs")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)

    def test_api_labs_fields(self):
        _, data = self._get_json("/api/labs")
        lab = data[0]
        for key in ("id", "title", "tagline", "description", "learning_objectives", "file", "language"):
            self.assertIn(key, lab, f"Missing key: {key}")

    def test_api_labs_language_detection(self):
        _, data = self._get_json("/api/labs")
        py_lab = next(l for l in data if l["id"] == "monte_carlo_python")
        java_lab = next(l for l in data if l["id"] == "monte_carlo_java")
        self.assertEqual(py_lab["language"], "python")
        self.assertEqual(java_lab["language"], "java")

    # /api/chapters (empty in example config)
    def test_api_chapters(self):
        status, data = self._get_json("/api/chapters")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)

    # /api/code/<lab_id>
    def test_api_code_python(self):
        status, data = self._get_json("/api/code/monte_carlo_python")
        self.assertEqual(status, 200)
        self.assertIn("code", data)
        self.assertIn("estimate_pi", data["code"])
        self.assertEqual(data["filename"], "pi.py")
        self.assertEqual(data["language"], "python")

    def test_api_code_java(self):
        status, data = self._get_json("/api/code/monte_carlo_java")
        self.assertEqual(status, 200)
        self.assertIn("code", data)
        self.assertIn("estimatePi", data["code"])
        self.assertEqual(data["filename"], "Pi.java")
        self.assertEqual(data["language"], "java")

    def test_api_code_not_found(self):
        status, data = self._get_json("/api/code/nonexistent_lab")
        self.assertEqual(status, 404)
        self.assertIn("error", data)

    # /api/explanations/<lab_id>
    def test_api_explanations_python(self):
        status, data = self._get_json("/api/explanations/monte_carlo_python")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, dict)
        self.assertIn("1", data)
        self.assertIn("text", data["1"])

    def test_api_explanations_java(self):
        status, data = self._get_json("/api/explanations/monte_carlo_java")
        self.assertEqual(status, 200)
        self.assertIn("1", data)

    def test_api_explanations_nonexistent(self):
        """Non-existent lab returns empty dict."""
        status, data = self._get_json("/api/explanations/no_such_lab")
        self.assertEqual(status, 200)
        self.assertEqual(data, {})

    def test_api_explanations_with_diagram_refs(self):
        _, data = self._get_json("/api/explanations/monte_carlo_python")
        # Line 8 should have a diagram reference
        entry = data["8"]
        self.assertEqual(entry["diagram"], "monte_carlo")
        self.assertIn("highlight", entry)

    # /api/diagrams/<id>
    def test_api_diagrams(self):
        status, data = self._get_json("/api/diagrams/monte_carlo")
        self.assertEqual(status, 200)
        self.assertEqual(data["id"], "monte_carlo")
        self.assertIn("graph TD", data["source"])

    def test_api_diagrams_not_found(self):
        status, data = self._get_json("/api/diagrams/nonexistent")
        self.assertEqual(status, 404)
        self.assertIn("error", data)

    def test_api_diagrams_path_traversal(self):
        """Path traversal attempts should be sanitised."""
        status, data = self._get_json("/api/diagrams/..%2F..%2Fetc%2Fpasswd")
        # The handler strips .. and / so it should not find any file
        self.assertEqual(status, 404)

    # /api/stop (no running process)
    def test_api_stop_not_running(self):
        status, data = self._get_json("/api/stop/monte_carlo_python")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "not_running")


# ---------------------------------------------------------------------------
# Builder tests
# ---------------------------------------------------------------------------
class TestBuilder(unittest.TestCase):
    """Tests for the build() function and its validation logic."""

    def setUp(self):
        """Create a temporary directory with a minimal config for build tests."""
        self.tmpdir = Path(tempfile.mkdtemp())
        # Copy the example directory structure
        shutil.copytree(EXAMPLE_DIR, self.tmpdir / "example")
        self.config_path = self.tmpdir / "example" / "config.json"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run_build(self, config_path=None):
        """Run builder.build() with sys.argv patched."""
        path = str(config_path or self.config_path)
        with patch.object(sys, "argv", ["wtc-build", path]):
            from walk_the_code.builder import build
            build()

    def test_build_creates_output(self):
        self._run_build()
        output = self.tmpdir / "example" / "data" / "labs.json"
        self.assertTrue(output.exists())

    def test_build_output_structure(self):
        self._run_build()
        output = self.tmpdir / "example" / "data" / "labs.json"
        bundle = json.loads(output.read_text())
        self.assertIn("config", bundle)
        self.assertIn("labs", bundle)
        self.assertIn("diagrams", bundle)
        self.assertIn("chapters", bundle)

    def test_build_config_section(self):
        self._run_build()
        bundle = json.loads((self.tmpdir / "example" / "data" / "labs.json").read_text())
        self.assertEqual(bundle["config"]["title"], "Monte Carlo Pi")

    def test_build_labs_count(self):
        self._run_build()
        bundle = json.loads((self.tmpdir / "example" / "data" / "labs.json").read_text())
        self.assertEqual(len(bundle["labs"]), 2)

    def test_build_lab_has_code(self):
        self._run_build()
        bundle = json.loads((self.tmpdir / "example" / "data" / "labs.json").read_text())
        py_lab = next(l for l in bundle["labs"] if l["id"] == "monte_carlo_python")
        self.assertIn("estimate_pi", py_lab["code"])

    def test_build_lab_has_explanations(self):
        self._run_build()
        bundle = json.loads((self.tmpdir / "example" / "data" / "labs.json").read_text())
        py_lab = next(l for l in bundle["labs"] if l["id"] == "monte_carlo_python")
        self.assertIn("1", py_lab["explanations"])

    def test_build_diagrams(self):
        self._run_build()
        bundle = json.loads((self.tmpdir / "example" / "data" / "labs.json").read_text())
        self.assertIn("monte_carlo", bundle["diagrams"])
        self.assertIn("graph TD", bundle["diagrams"]["monte_carlo"])

    def test_build_language_detection(self):
        self._run_build()
        bundle = json.loads((self.tmpdir / "example" / "data" / "labs.json").read_text())
        py_lab = next(l for l in bundle["labs"] if l["id"] == "monte_carlo_python")
        java_lab = next(l for l in bundle["labs"] if l["id"] == "monte_carlo_java")
        self.assertEqual(py_lab["language"], "python")
        self.assertEqual(java_lab["language"], "java")

    def test_build_idempotent(self):
        """Running build twice should produce identical output."""
        self._run_build()
        out1 = (self.tmpdir / "example" / "data" / "labs.json").read_text()
        self._run_build()
        out2 = (self.tmpdir / "example" / "data" / "labs.json").read_text()
        self.assertEqual(out1, out2)


class TestBuilderValidation(unittest.TestCase):
    """Tests for builder validation: out-of-range lines, missing diagrams, stale hashes, chapter refs."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_project(self, config_data, code_content="line1\nline2\nline3\n",
                      explanations=None, diagrams=None):
        """Create a minimal project structure in tmpdir and return config path."""
        config_dir = self.tmpdir / "project"
        config_dir.mkdir(parents=True, exist_ok=True)

        lab_id = "test_lab"
        filename = "main.py"

        if "labs" not in config_data:
            config_data["labs"] = [{"id": lab_id, "file": filename, "title": "Test"}]

        # Resolve code_dir
        code_dir_name = config_data.get("code_dir", ".")
        code_base = config_dir / code_dir_name
        code_path = code_base / lab_id
        code_path.mkdir(parents=True, exist_ok=True)
        (code_path / filename).write_text(code_content)

        # Explanations
        if explanations is not None:
            exp_dir = config_dir / "comments" / lab_id
            exp_dir.mkdir(parents=True, exist_ok=True)
            (exp_dir / "main.json").write_text(json.dumps(explanations))

        # Diagrams
        if diagrams:
            diag_dir = config_dir / "diagrams"
            diag_dir.mkdir(parents=True, exist_ok=True)
            for name, content in diagrams.items():
                (diag_dir / f"{name}.mmd").write_text(content)

        config_path = config_dir / "config.json"
        config_path.write_text(json.dumps(config_data))
        return config_path

    def _run_build(self, config_path, expect_exit=False):
        """Run build, optionally expecting a sys.exit(1)."""
        with patch.object(sys, "argv", ["wtc-build", str(config_path)]):
            from walk_the_code.builder import build
            if expect_exit:
                with self.assertRaises(SystemExit) as ctx:
                    build()
                return ctx.exception.code
            else:
                build()

    def test_out_of_range_line(self):
        """Annotation for a line beyond the file length should cause an error."""
        config_path = self._make_project(
            {"title": "T"},
            code_content="line1\nline2\n",
            explanations={"99": {"text": "nonexistent line", "hash": ""}},
        )
        exit_code = self._run_build(config_path, expect_exit=True)
        self.assertEqual(exit_code, 1)

    def test_line_zero_is_out_of_range(self):
        """Line 0 should be flagged as out of range."""
        config_path = self._make_project(
            {"title": "T"},
            code_content="line1\n",
            explanations={"0": {"text": "bad line", "hash": ""}},
        )
        exit_code = self._run_build(config_path, expect_exit=True)
        self.assertEqual(exit_code, 1)

    def test_missing_diagram_reference(self):
        """Annotation referencing a diagram that does not exist should cause an error."""
        config_path = self._make_project(
            {"title": "T"},
            code_content="line1\nline2\nline3\n",
            explanations={"1": {"text": "uses diagram", "hash": "", "diagram": "nonexistent"}},
        )
        exit_code = self._run_build(config_path, expect_exit=True)
        self.assertEqual(exit_code, 1)

    def test_valid_diagram_reference(self):
        """Annotation referencing an existing diagram should not error."""
        config_path = self._make_project(
            {"title": "T"},
            code_content="line1\nline2\nline3\n",
            explanations={"1": {"text": "uses diagram", "hash": "", "diagram": "flow"}},
            diagrams={"flow": "graph TD\n  A-->B"},
        )
        self._run_build(config_path)  # Should not raise

    def test_stale_hash_produces_warning(self):
        """A hash that does not match the current code should produce a warning (not an error)."""
        config_path = self._make_project(
            {"title": "T"},
            code_content="current code\n",
            explanations={"1": {"text": "explanation", "hash": "deadbeef"}},
        )
        # Stale hash is a warning, not an error, so build should succeed
        self._run_build(config_path)

    def test_correct_hash_no_warning(self):
        """A correct hash should not produce any warning."""
        code = "def hello(): pass"
        correct_hash = _line_hash(code)
        config_path = self._make_project(
            {"title": "T"},
            code_content=code + "\n",
            explanations={"1": {"text": "explanation", "hash": correct_hash}},
        )
        self._run_build(config_path)  # Should not raise or warn about hash

    def test_chapter_references_invalid_lab(self):
        """A chapter referencing a non-existent lab should cause an error."""
        config_path = self._make_project(
            {"title": "T", "chapters": [
                {"id": "ch1", "title": "Ch1", "labs": ["nonexistent_lab"]}
            ]},
            code_content="line1\n",
        )
        exit_code = self._run_build(config_path, expect_exit=True)
        self.assertEqual(exit_code, 1)

    def test_chapter_references_valid_lab(self):
        """A chapter referencing an existing lab should be fine."""
        config_path = self._make_project(
            {"title": "T", "chapters": [
                {"id": "ch1", "title": "Ch1", "labs": ["test_lab"]}
            ]},
            code_content="line1\n",
        )
        self._run_build(config_path)  # Should not raise

    def test_chapter_missing_comparison_diagram(self):
        """A chapter with a comparison_diagram that does not exist should error."""
        config_path = self._make_project(
            {"title": "T", "chapters": [
                {"id": "ch1", "title": "Ch1", "labs": ["test_lab"],
                 "comparison_diagram": "missing_diag"}
            ]},
            code_content="line1\n",
        )
        exit_code = self._run_build(config_path, expect_exit=True)
        self.assertEqual(exit_code, 1)

    def test_chapter_valid_comparison_diagram(self):
        config_path = self._make_project(
            {"title": "T", "chapters": [
                {"id": "ch1", "title": "Ch1", "labs": ["test_lab"],
                 "comparison_diagram": "comp"}
            ]},
            code_content="line1\n",
            diagrams={"comp": "graph TD\n  A-->B"},
        )
        self._run_build(config_path)  # Should not raise


class TestBuilderEdgeCases(unittest.TestCase):
    """Edge case tests for the builder."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_config(self, data):
        config_dir = self.tmpdir / "proj"
        config_dir.mkdir(parents=True, exist_ok=True)
        path = config_dir / "config.json"
        path.write_text(json.dumps(data))
        return path

    def test_empty_labs_list(self):
        """Config with no labs should build successfully."""
        config_path = self._make_config({"title": "Empty", "labs": []})
        with patch.object(sys, "argv", ["wtc-build", str(config_path)]):
            from walk_the_code.builder import build
            build()
        output = self.tmpdir / "proj" / "data" / "labs.json"
        self.assertTrue(output.exists())
        bundle = json.loads(output.read_text())
        self.assertEqual(bundle["labs"], [])
        self.assertEqual(bundle["diagrams"], {})

    def test_no_labs_key(self):
        """Config with no labs key should default to empty."""
        config_path = self._make_config({"title": "NoLabs"})
        with patch.object(sys, "argv", ["wtc-build", str(config_path)]):
            from walk_the_code.builder import build
            build()
        output = self.tmpdir / "proj" / "data" / "labs.json"
        bundle = json.loads(output.read_text())
        self.assertEqual(bundle["labs"], [])

    def test_missing_code_file(self):
        """When the code file does not exist, code should be empty string."""
        config_dir = self.tmpdir / "proj"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_data = {
            "title": "T",
            "labs": [{"id": "ghost", "file": "missing.py", "title": "Ghost"}],
        }
        config_path = config_dir / "config.json"
        config_path.write_text(json.dumps(config_data))

        with patch.object(sys, "argv", ["wtc-build", str(config_path)]):
            from walk_the_code.builder import build
            build()

        bundle = json.loads((config_dir / "data" / "labs.json").read_text())
        self.assertEqual(bundle["labs"][0]["code"], "")

    def test_lab_with_no_annotations(self):
        """A lab with no comments file should have empty explanations."""
        config_dir = self.tmpdir / "proj"
        config_dir.mkdir(parents=True, exist_ok=True)
        code_dir = config_dir / "bare_lab"
        code_dir.mkdir()
        (code_dir / "test.py").write_text("print('hi')\n")

        config_data = {
            "title": "T",
            "labs": [{"id": "bare_lab", "file": "test.py", "title": "Bare"}],
        }
        config_path = config_dir / "config.json"
        config_path.write_text(json.dumps(config_data))

        with patch.object(sys, "argv", ["wtc-build", str(config_path)]):
            from walk_the_code.builder import build
            build()

        bundle = json.loads((config_dir / "data" / "labs.json").read_text())
        self.assertEqual(bundle["labs"][0]["explanations"], {})

    def test_no_diagrams_directory(self):
        """Build should work fine when there is no diagrams/ directory."""
        config_dir = self.tmpdir / "proj"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_data = {"title": "T", "labs": []}
        config_path = config_dir / "config.json"
        config_path.write_text(json.dumps(config_data))

        with patch.object(sys, "argv", ["wtc-build", str(config_path)]):
            from walk_the_code.builder import build
            build()

        bundle = json.loads((config_dir / "data" / "labs.json").read_text())
        self.assertEqual(bundle["diagrams"], {})


# ---------------------------------------------------------------------------
# Server edge-case tests with custom configs
# ---------------------------------------------------------------------------
class TestServerEmptyConfig(unittest.TestCase):
    """Server tests with a minimal/empty configuration."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = Path(tempfile.mkdtemp())
        config_dir = cls.tmpdir / "empty_proj"
        config_dir.mkdir()
        config_path = config_dir / "config.json"
        config_path.write_text(json.dumps({"title": "Empty"}))
        cfg = load_config(config_path)

        # Create a separate handler class so we don't pollute the other tests
        cls.HandlerClass = type("EmptyHandler", (WTCHandler,), {"config": cfg})

        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), cls.HandlerClass)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def _get_json(self, path):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode()
        conn.close()
        return resp.status, json.loads(body)

    def test_empty_labs(self):
        status, data = self._get_json("/api/labs")
        self.assertEqual(status, 200)
        self.assertEqual(data, [])

    def test_empty_chapters(self):
        status, data = self._get_json("/api/chapters")
        self.assertEqual(status, 200)
        self.assertEqual(data, [])

    def test_config_title(self):
        status, data = self._get_json("/api/config")
        self.assertEqual(status, 200)
        self.assertEqual(data["title"], "Empty")

    def test_code_for_nonexistent_lab(self):
        status, data = self._get_json("/api/code/nope")
        self.assertEqual(status, 404)

    def test_explanations_for_nonexistent_lab(self):
        status, data = self._get_json("/api/explanations/nope")
        self.assertEqual(status, 200)
        self.assertEqual(data, {})


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------
class TestValidator(unittest.TestCase):
    """Tests for the validate() function in validator.py."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_project(self, config_data, code_content="line1\nline2\nline3\n",
                      explanations=None, diagrams=None, comment_raw=None):
        """Create a minimal project structure and return config path."""
        config_dir = self.tmpdir / "project"
        config_dir.mkdir(parents=True, exist_ok=True)

        lab_id = "test_lab"
        filename = "main.py"

        if "labs" not in config_data:
            config_data["labs"] = [{"id": lab_id, "file": filename, "title": "Test"}]

        # Resolve code_dir
        code_dir_name = config_data.get("code_dir", ".")
        code_base = config_dir / code_dir_name
        code_path = code_base / lab_id
        code_path.mkdir(parents=True, exist_ok=True)
        (code_path / filename).write_text(code_content)

        # Explanations (as dict to be serialized, or raw string)
        if explanations is not None or comment_raw is not None:
            exp_dir = config_dir / "comments" / lab_id
            exp_dir.mkdir(parents=True, exist_ok=True)
            if comment_raw is not None:
                (exp_dir / "main.json").write_text(comment_raw)
            else:
                (exp_dir / "main.json").write_text(json.dumps(explanations))

        # Diagrams
        if diagrams:
            diag_dir = config_dir / "diagrams"
            diag_dir.mkdir(parents=True, exist_ok=True)
            for name, content in diagrams.items():
                (diag_dir / f"{name}.mmd").write_text(content)

        config_path = config_dir / "config.json"
        config_path.write_text(json.dumps(config_data))
        return config_path

    def _run_validate(self, config_path):
        """Run validate() with sys.argv patched, capturing stdout."""
        from walk_the_code.validator import validate
        with patch.object(sys, "argv", ["wtc-validate", str(config_path)]):
            from io import StringIO
            with patch("sys.stdout", new_callable=StringIO) as mock_out:
                try:
                    validate()
                except SystemExit as e:
                    return e.code, mock_out.getvalue()
                return 0, mock_out.getvalue()

    def test_valid_config(self):
        """A valid project should exit with code 0."""
        config_path = self._make_project({"title": "Valid Project"})
        exit_code, output = self._run_validate(config_path)
        self.assertEqual(exit_code, 0)
        self.assertIn("PASS", output)

    def test_missing_config_file(self):
        """A non-existent config file should exit with code 1."""
        from walk_the_code.validator import validate
        with patch.object(sys, "argv", ["wtc-validate", "/nonexistent/config.json"]):
            with self.assertRaises(SystemExit) as ctx:
                validate()
            self.assertEqual(ctx.exception.code, 1)

    def test_invalid_json(self):
        """Invalid JSON in config should exit with code 1."""
        config_path = self.tmpdir / "bad.json"
        config_path.write_text("{not valid json!!!")
        from walk_the_code.validator import validate
        with patch.object(sys, "argv", ["wtc-validate", str(config_path)]):
            with self.assertRaises(SystemExit) as ctx:
                validate()
            self.assertEqual(ctx.exception.code, 1)

    def test_missing_title(self):
        """Missing title should produce a warning (not an error)."""
        config_path = self._make_project({"labs": [{"id": "test_lab", "file": "main.py", "title": "T"}]})
        exit_code, output = self._run_validate(config_path)
        self.assertEqual(exit_code, 0)
        self.assertIn("No top-level 'title' field", output)

    def test_missing_labs(self):
        """Missing labs should produce an error."""
        config_dir = self.tmpdir / "project"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.json"
        config_path.write_text(json.dumps({"title": "No Labs"}))
        exit_code, output = self._run_validate(config_path)
        self.assertEqual(exit_code, 1)
        self.assertIn("Missing required top-level field: labs", output)

    def test_missing_lab_required_fields(self):
        """Labs missing id, file, or title should produce errors."""
        config_dir = self.tmpdir / "project"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.json"
        config_path.write_text(json.dumps({"title": "T", "labs": [{}]}))
        exit_code, output = self._run_validate(config_path)
        self.assertEqual(exit_code, 1)
        self.assertIn("missing required field 'id'", output)
        self.assertIn("missing required field 'file'", output)
        self.assertIn("missing required field 'title'", output)

    def test_code_file_not_found(self):
        """A lab referencing a non-existent code file should produce an error."""
        config_dir = self.tmpdir / "project"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.json"
        config_path.write_text(json.dumps({
            "title": "T",
            "labs": [{"id": "ghost", "file": "missing.py", "title": "Ghost"}]
        }))
        exit_code, output = self._run_validate(config_path)
        self.assertEqual(exit_code, 1)
        self.assertIn("code file not found", output)

    def test_valid_comment_file(self):
        """A valid comment file should not cause errors."""
        config_path = self._make_project(
            {"title": "T"},
            code_content="line1\nline2\nline3\n",
            explanations={"1": {"text": "good comment", "hash": _line_hash("line1")}},
        )
        exit_code, output = self._run_validate(config_path)
        self.assertEqual(exit_code, 0)
        self.assertIn("PASS", output)

    def test_invalid_comment_json(self):
        """Invalid JSON in a comment file should produce an error."""
        config_path = self._make_project(
            {"title": "T"},
            code_content="line1\nline2\nline3\n",
            comment_raw="{not valid json!!!",
        )
        exit_code, output = self._run_validate(config_path)
        self.assertEqual(exit_code, 1)
        self.assertIn("invalid JSON", output)

    def test_out_of_range_line_numbers(self):
        """Annotations for lines beyond file length should produce errors."""
        config_path = self._make_project(
            {"title": "T"},
            code_content="line1\nline2\n",
            explanations={"99": {"text": "beyond", "hash": ""}},
        )
        exit_code, output = self._run_validate(config_path)
        self.assertEqual(exit_code, 1)
        self.assertIn("annotation for line 99", output)

    def test_missing_diagram_references(self):
        """Annotation referencing a non-existent diagram should produce an error."""
        config_path = self._make_project(
            {"title": "T"},
            code_content="line1\nline2\nline3\n",
            explanations={"1": {"text": "uses diagram", "hash": "", "diagram": "nonexistent"}},
        )
        exit_code, output = self._run_validate(config_path)
        self.assertEqual(exit_code, 1)
        self.assertIn("nonexistent", output)
        self.assertIn("not found", output)

    def test_stale_hashes_warning(self):
        """Stale hashes should produce a warning but still pass."""
        config_path = self._make_project(
            {"title": "T"},
            code_content="current code\n",
            explanations={"1": {"text": "explanation", "hash": "deadbeef"}},
        )
        exit_code, output = self._run_validate(config_path)
        self.assertEqual(exit_code, 0)
        self.assertIn("hash mismatch", output)
        self.assertIn("PASS", output)

    def test_chapter_referencing_invalid_lab(self):
        """A chapter referencing a non-existent lab should produce an error."""
        config_path = self._make_project(
            {"title": "T", "chapters": [
                {"id": "ch1", "title": "Ch1", "labs": ["nonexistent_lab"]}
            ]},
            code_content="line1\n",
        )
        exit_code, output = self._run_validate(config_path)
        self.assertEqual(exit_code, 1)
        self.assertIn("nonexistent_lab", output)
        self.assertIn("not defined", output)

    def test_missing_learning_objectives_warning(self):
        """Missing learning_objectives should produce a warning but still pass."""
        config_path = self._make_project({"title": "T"})
        exit_code, output = self._run_validate(config_path)
        self.assertEqual(exit_code, 0)
        self.assertIn("no learning_objectives defined", output)

    def test_missing_exercises_warning(self):
        """Missing exercises should produce a warning but still pass."""
        config_path = self._make_project({"title": "T"})
        exit_code, output = self._run_validate(config_path)
        self.assertEqual(exit_code, 0)
        self.assertIn("no exercises defined", output)

    def test_valid_exercises_format(self):
        """Valid exercises should not produce errors or warnings about exercises."""
        config_path = self._make_project({
            "title": "T",
            "labs": [{
                "id": "test_lab", "file": "main.py", "title": "Test",
                "learning_objectives": ["Learn X"],
                "exercises": [{"prompt": "Do something"}],
            }],
        })
        exit_code, output = self._run_validate(config_path)
        self.assertEqual(exit_code, 0)
        self.assertNotIn("no exercises defined", output)
        self.assertNotIn("no learning_objectives defined", output)


# ---------------------------------------------------------------------------
# Init tests
# ---------------------------------------------------------------------------
class TestInit(unittest.TestCase):
    """Tests for the init() function in init.py."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self._orig_cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._orig_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_creates_expected_directory_structure(self):
        """init() should create samples/, comments/, diagrams/ directories."""
        os.chdir(self.tmpdir)
        with patch("builtins.input", side_effect=["My Project", "A tagline", "https://github.com/test/repo"]):
            from walk_the_code.init import init
            init()
        for d in ["samples", "comments", "diagrams"]:
            self.assertTrue((self.tmpdir / d).is_dir(), f"{d}/ should exist")

    def test_creates_valid_config_json(self):
        """init() should create a valid config.json with the provided values."""
        os.chdir(self.tmpdir)
        with patch("builtins.input", side_effect=["Test Title", "Test Tagline", "https://example.com"]):
            from walk_the_code.init import init
            init()
        config_path = self.tmpdir / "config.json"
        self.assertTrue(config_path.exists())
        config = json.loads(config_path.read_text())
        self.assertEqual(config["title"], "Test Title")
        self.assertEqual(config["tagline"], "Test Tagline")
        self.assertEqual(config["repo_url"], "https://example.com")
        self.assertEqual(config["code_dir"], "samples")
        self.assertIsInstance(config["labs"], list)
        self.assertIsInstance(config["chapters"], list)

    def test_handles_empty_inputs_uses_defaults(self):
        """Empty inputs should use default values."""
        os.chdir(self.tmpdir)
        with patch("builtins.input", side_effect=["", "", ""]):
            from walk_the_code.init import init
            init()
        config = json.loads((self.tmpdir / "config.json").read_text())
        self.assertEqual(config["title"], "My Tutorial")
        self.assertEqual(config["tagline"], "An interactive code walkthrough")
        self.assertEqual(config["repo_url"], "https://github.com/user/repo")

    def test_doesnt_overwrite_existing_config(self):
        """init() should exit with code 1 if config.json already exists."""
        os.chdir(self.tmpdir)
        (self.tmpdir / "config.json").write_text("{}")
        with patch("builtins.input", side_effect=["Title", "Tag", "URL"]):
            from walk_the_code.init import init
            with self.assertRaises(SystemExit) as ctx:
                init()
            self.assertEqual(ctx.exception.code, 1)

    def test_created_directories_exist(self):
        """All expected directories should exist after init()."""
        os.chdir(self.tmpdir)
        with patch("builtins.input", side_effect=["P", "T", "U"]):
            from walk_the_code.init import init
            init()
        self.assertTrue((self.tmpdir / "samples").exists())
        self.assertTrue((self.tmpdir / "comments").exists())
        self.assertTrue((self.tmpdir / "diagrams").exists())
        self.assertTrue((self.tmpdir / "config.json").exists())


if __name__ == "__main__":
    unittest.main()
