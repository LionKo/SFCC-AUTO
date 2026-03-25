#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SFCC supervisor script.

Responsibilities:
1. Start the target script.
2. Automatically restart it if it exits.
3. Rate-limit rapid restarts to avoid restart loops.
4. Stop the child process when the supervisor is interrupted.
"""

from __future__ import annotations

import os
import json
import signal
import subprocess
import sys
import time
from pathlib import Path


TARGET_SCRIPT = "sfcc_auto_click_front_v3.py"
RESTART_DELAY_SECONDS = 3
MAX_RAPID_RESTARTS = 10
RAPID_RESTART_WINDOW_SECONDS = 60
PASS_THROUGH_ARGS = True
WORKDIR = Path(__file__).resolve().parent
STATUS_FILE = WORKDIR / "sfcc_status.json"
HEARTBEAT_POLL_SECONDS = 2.0
STATUS_HEARTBEAT_TIMEOUT_SECONDS = 45.0
STATUS_STARTUP_GRACE_SECONDS = 90.0
PRACTICE_STALL_TIMEOUT_SECONDS = 120.0
GAME_PROCESS_NAME = "FootballClubChampions.exe"


child_proc: subprocess.Popen | None = None
SUPERVISOR_PID_FILE = WORKDIR / "sfcc_supervisor.pid"
CHILD_PID_FILE = WORKDIR / "sfcc_child.pid"


def log(msg: str) -> None:
    print(msg, flush=True)


def write_pid(path: Path, pid: int | None) -> None:
    try:
        if pid is None:
            if path.exists():
                path.unlink()
            return
        path.write_text(str(pid), encoding="utf-8")
    except Exception:
        pass


def resolve_python_exe() -> str:
    venv_python = WORKDIR / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def build_command() -> list[str]:
    cmd = [resolve_python_exe(), str((WORKDIR / TARGET_SCRIPT).resolve())]
    if PASS_THROUGH_ARGS and len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    return cmd


def load_status() -> dict | None:
    try:
        if not STATUS_FILE.exists():
            return None
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def start_child() -> subprocess.Popen:
    script_path = (WORKDIR / TARGET_SCRIPT).resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"Target script not found: {script_path}")

    cmd = build_command()
    log(f"[SUP] Starting child script: {script_path.name}")
    log(f"[SUP] Command: {' '.join(cmd)}")

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen(
        cmd,
        cwd=str(WORKDIR),
        creationflags=creationflags,
    )
    write_pid(CHILD_PID_FILE, proc.pid)
    return proc


def terminate_child(proc: subprocess.Popen, timeout: float = 8.0) -> None:
    if proc.poll() is not None:
        return

    log("[SUP] Stopping child script...")

    try:
        if os.name == "nt":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.send_signal(signal.SIGINT)
        proc.wait(timeout=timeout)
        return
    except Exception:
        pass

    try:
        proc.terminate()
        proc.wait(timeout=5)
        return
    except Exception:
        pass

    try:
        proc.kill()
    except Exception:
        pass
    write_pid(CHILD_PID_FILE, None)


def kill_game_process() -> None:
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/IM", GAME_PROCESS_NAME, "/F", "/T"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
    except Exception:
        pass


def main() -> None:
    global child_proc
    write_pid(SUPERVISOR_PID_FILE, os.getpid())

    log("[SUP] SFCC supervisor started.")
    log(f"[SUP] Target: {TARGET_SCRIPT}")
    log("[SUP] The supervisor will automatically restart the child if it exits.")
    log("[SUP] Press Ctrl+C to stop the supervisor.")

    rapid_restart_times: list[float] = []

    while True:
        start_ts = time.time()
        try:
            child_proc = start_child()
        except FileNotFoundError as e:
            log(f"[SUP][ERR] {e}")
            break
        except Exception as e:
            log(f"[SUP][ERR] Failed to start child: {e}")
            log(f"[SUP] Retrying in {RESTART_DELAY_SECONDS} seconds...")
            time.sleep(RESTART_DELAY_SECONDS)
            continue

        last_status_ts = None
        last_status_seen_at = start_ts
        last_practice_count = None
        last_practice_change_at = start_ts
        exit_code = None

        try:
            while True:
                try:
                    exit_code = child_proc.wait(timeout=HEARTBEAT_POLL_SECONDS)
                    write_pid(CHILD_PID_FILE, None)
                    break
                except subprocess.TimeoutExpired:
                    pass

                now = time.time()
                status = load_status()
                if status:
                    status_ts = status.get("ts")
                    if isinstance(status_ts, (int, float)):
                        if last_status_ts is None or status_ts != last_status_ts:
                            last_status_ts = status_ts
                            last_status_seen_at = now

                    practice_count = status.get("practice_click_count")
                    if isinstance(practice_count, int):
                        if last_practice_count is None or practice_count != last_practice_count:
                            last_practice_count = practice_count
                            last_practice_change_at = now

                if (
                    now - start_ts >= STATUS_STARTUP_GRACE_SECONDS
                    and now - last_status_seen_at >= STATUS_HEARTBEAT_TIMEOUT_SECONDS
                ):
                    log(
                        f"[SUP][SAFEGUARD] Status heartbeat stale for "
                        f"{STATUS_HEARTBEAT_TIMEOUT_SECONDS:.0f}s, restarting child and game."
                    )
                    terminate_child(child_proc)
                    kill_game_process()
                    exit_code = -9001
                    write_pid(CHILD_PID_FILE, None)
                    break

                if (
                    last_practice_count is not None
                    and last_practice_count > 0
                    and now - last_practice_change_at >= PRACTICE_STALL_TIMEOUT_SECONDS
                ):
                    log(
                        f"[SUP][SAFEGUARD] Practice counter stalled at #{last_practice_count} for "
                        f"{PRACTICE_STALL_TIMEOUT_SECONDS:.0f}s, restarting child and game."
                    )
                    terminate_child(child_proc)
                    kill_game_process()
                    exit_code = -9002
                    write_pid(CHILD_PID_FILE, None)
                    break
        except KeyboardInterrupt:
            log("[SUP] Ctrl+C received, stopping supervisor.")
            terminate_child(child_proc)
            kill_game_process()
            break

        run_seconds = time.time() - start_ts
        log(f"[SUP] Child exited with code={exit_code} after {run_seconds:.1f}s")

        now = time.time()
        rapid_restart_times.append(now)
        rapid_restart_times = [t for t in rapid_restart_times if now - t <= RAPID_RESTART_WINDOW_SECONDS]

        if run_seconds < 5 and len(rapid_restart_times) >= MAX_RAPID_RESTARTS:
            log("[SUP][ERR] Child exited too many times in a short period.")
            log("[SUP][ERR] Supervisor is stopping to avoid an infinite restart loop.")
            break

        log(f"[SUP] Restarting in {RESTART_DELAY_SECONDS} seconds...")
        time.sleep(RESTART_DELAY_SECONDS)

    log("[SUP] Supervisor stopped.")
    write_pid(CHILD_PID_FILE, None)
    write_pid(SUPERVISOR_PID_FILE, None)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        if child_proc is not None:
            terminate_child(child_proc)
        write_pid(CHILD_PID_FILE, None)
        write_pid(SUPERVISOR_PID_FILE, None)
        log("[SUP] Supervisor stopped.")
