"""Process entry for non-reload runs (local or container CMD)."""

from pathlib import Path

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


def main() -> None:
    _load_dotenv_if_present()
    uvicorn.run("api.app:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
