"""Process entry for non-reload runs (local or container CMD)."""

from pathlib import Path

import os
import sys

import uvicorn

_ENV_PATH = Path(__file__).resolve().parent / ".env"


def _load_dotenv_if_present() -> None:
    if not _ENV_PATH.is_file():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(_ENV_PATH)


_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def main() -> None:
    _load_dotenv_if_present()
    host = os.environ.get("ENGINE_HOST", "127.0.0.1")
    port = int(os.environ.get("ENGINE_PORT", "8000"))
    # Refuse to expose an open engine beyond this machine (ADR-0049).
    if host not in _LOOPBACK and not os.environ.get("ENGINE_API_KEY", "").strip():
        sys.exit(f"ENGINE_API_KEY must be set to listen on {host}; refusing to start.")
    uvicorn.run("api.app:app", host=host, port=port)


if __name__ == "__main__":
    main()
