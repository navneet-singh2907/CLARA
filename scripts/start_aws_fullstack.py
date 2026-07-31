"""Run the CLARA API and Next.js UI in one Elastic Beanstalk container."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
NEXT_SERVER = APP_ROOT / "web" / "server.js"
API_PORT = "8001"
WEB_PORT = "8000"


def _terminate(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()

    for process in processes:
        if process.poll() is None:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> int:
    if not NEXT_SERVER.is_file():
        raise FileNotFoundError(f"Next.js standalone server is missing: {NEXT_SERVER}")

    api_environment = os.environ.copy()
    web_environment = os.environ.copy()
    web_environment.update({"HOSTNAME": "0.0.0.0", "PORT": WEB_PORT})

    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "loan_pipeline.api.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                API_PORT,
            ],
            cwd=APP_ROOT,
            env=api_environment,
        ),
        subprocess.Popen(
            ["node", str(NEXT_SERVER)],
            cwd=NEXT_SERVER.parent,
            env=web_environment,
        ),
    ]

    def handle_shutdown(_signum: int, _frame: object) -> None:
        _terminate(processes)

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    try:
        while True:
            for process in processes:
                return_code = process.poll()
                if return_code is not None:
                    return return_code
            time.sleep(0.5)
    finally:
        _terminate(processes)


if __name__ == "__main__":
    raise SystemExit(main())
