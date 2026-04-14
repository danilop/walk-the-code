"""walk-the-code CLI entry points."""

import sys

from .config import load_config
from .server import ThreadedHTTPServer, WTCHandler


def serve():
    """CLI entry point: walk-the-code serve [port] [--config path]"""
    args = sys.argv[1:]
    port = 8000
    config_path = "config.json"
    i = 0
    while i < len(args):
        if args[i] == "--config" and i + 1 < len(args):
            config_path = args[i + 1]
            i += 2
        elif args[i].isdigit():
            port = int(args[i])
            i += 1
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
    print(f"  units: {len(config.get('units', []))}")
    print(f"  groups: {len(config.get('groups', []))}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


def build():
    """CLI entry point: walk-the-code build [config_path]"""
    from .builder import build as _build
    _build()


def init():
    """CLI entry point: wtc-init [--template basic|multilang|group] — scaffold a new project."""
    from .init import init as _init
    _init()  # --template is parsed from sys.argv inside init()


def validate():
    """CLI entry point: wtc-validate [config_path] — validate project."""
    from .validator import validate as _validate
    _validate()


def hash():
    """CLI entry point: wtc-hash [config_path] — add content hashes to comment files."""
    from .hasher import hash as _hash
    _hash()
