"""Start FastAPI + Streamlit together with one command on Windows/macOS/Linux."""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://127.0.0.1:8501"


def wait_for_url(url: str, process: subprocess.Popen, label: str, timeout: int = 45) -> bool:
    """Wait until a child process responds to its local health URL."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            print(f"{label} berhenti sebelum siap (exit code {process.returncode}).")
            return False
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if 200 <= response.status < 300:
                    return True
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(0.5)
    print(f"Timeout: {label} tidak merespons pada {url}")
    return False


def stop_process(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    env = os.environ.copy()
    env["BACKEND_URL"] = BACKEND_URL

    backend_command = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    frontend_command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "frontend/app.py",
        "--server.address",
        "127.0.0.1",
        "--server.port",
        "8501",
        "--server.headless",
        "true",
    ]

    backend = None
    frontend = None
    try:
        print("Menjalankan backend FastAPI...")
        backend = subprocess.Popen(backend_command, cwd=ROOT, env=env)
        if not wait_for_url(f"{BACKEND_URL}/health", backend, "Backend"):
            return 1

        print("Menjalankan frontend Streamlit...")
        frontend = subprocess.Popen(frontend_command, cwd=ROOT, env=env)
        if not wait_for_url(f"{FRONTEND_URL}/_stcore/health", frontend, "Frontend"):
            return 1

        print("\nDashboard aktif:")
        print(f"  UI:  {FRONTEND_URL}")
        print(f"  API: {BACKEND_URL}/docs")
        print("Tekan Ctrl+C untuk menghentikan keduanya.\n")
        webbrowser.open(FRONTEND_URL)

        while backend.poll() is None and frontend.poll() is None:
            time.sleep(0.5)

        if backend.poll() is not None:
            print(f"Backend berhenti (exit code {backend.returncode}).")
        if frontend.poll() is not None:
            print(f"Frontend berhenti (exit code {frontend.returncode}).")
        return 1
    except KeyboardInterrupt:
        print("\nMenghentikan backend dan frontend...")
        return 0
    finally:
        stop_process(frontend)
        stop_process(backend)


if __name__ == "__main__":
    raise SystemExit(main())
