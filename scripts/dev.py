"""Start both development servers. Run with the project's virtualenv Python."""

from pathlib import Path
import argparse
import os
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--ui-port", type=int, default=5173)
    args = parser.parse_args()
    for port in (args.api_port, args.ui_port):
        if not 1 <= port <= 65535:
            parser.error("Ports must be between 1 and 65535")
        try:
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", port))
        except OSError:
            print(f"Port {port} is occupied. Choose another with --api-port or --ui-port.")
            return 1
    if args.api_port == args.ui_port:
        parser.error("API and UI ports must differ")
    node = shutil.which("node")
    if not node:
        print("Node.js 24 is required. Install it, then run pnpm install in frontend.")
        return 1
    if not (ROOT / "frontend/node_modules").exists():
        print("Run 'pnpm install' in frontend before starting development.")
        return 1
    processes = []
    try:
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.api_port),
                ],
                cwd=ROOT / "backend",
            )
        )
        frontend_env = {**os.environ, "RELAYOPS_API_URL": f"http://127.0.0.1:{args.api_port}"}
        # Direct processes avoid orphaning a pnpm/cmd wrapper or API reloader.
        processes.append(
            subprocess.Popen(
                [
                    node,
                    str(ROOT / "frontend/node_modules/vite/bin/vite.js"),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.ui_port),
                    "--strictPort",
                ],
                cwd=ROOT / "frontend",
                env=frontend_env,
            )
        )
        print(
            f"RelayOps: http://localhost:{args.ui_port} | API docs: http://localhost:{args.api_port}/docs",
            flush=True,
        )
        print("Frontend changes reload automatically. Restart after Python changes.", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        return next((process.returncode for process in processes if process.returncode), 0)
    except KeyboardInterrupt:
        return 0
    finally:
        for process in processes:
            if process.poll() is None:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                else:
                    process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
