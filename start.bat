@echo off
REM Local reload server. For non-reload runs use: python run_server.py
cd /d "%~dp0"
python -m uvicorn api.app:app --reload --host 127.0.0.1 --port 8000
