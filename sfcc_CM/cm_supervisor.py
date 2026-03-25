from __future__ import annotations

import argparse
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
BOT_SCRIPT = BASE_DIR / "cm_bot.py"
PID_FILE = LOG_DIR / "cm_supervisor.pid"
CHILD_PID_FILE = LOG_DIR / "cm_bot_child.pid"
GAME_PROCESS_NAME = "FootballClubChampions.exe"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Supervise cm_bot.py and restart it if it exits.")
    parser.add_argument("--check-interval", type=float, default=3.0, help="Seconds between child health checks.")
    parser.add_argument("--restart-delay", type=float, default=5.0, help="Seconds to wait before restarting cm_bot.py.")
    parser.add_argument("--max-restarts", type=int, default=0, help="0 means unlimited restarts.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Supervisor log level.",
    )
    return parser


def configure_logging(level_name: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"cm_supervisor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level_name.upper(), logging.INFO))

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    logging.info("Supervisor log file: %s", log_path)
    return log_path


class BotSupervisor:
    def __init__(self, check_interval: float, restart_delay: float, max_restarts: int) -> None:
        self.check_interval = max(0.5, check_interval)
        self.restart_delay = max(0.5, restart_delay)
        self.max_restarts = max_restarts
        self.restart_count = 0
        self.child: subprocess.Popen[str] | None = None
        self.stop_requested = False

    def write_supervisor_pid(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(get_current_pid()), encoding="utf-8")

    def launch_bot(self) -> None:
        if not BOT_SCRIPT.exists():
            raise FileNotFoundError(f"Bot script not found: {BOT_SCRIPT}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stdout_path = LOG_DIR / f"cm_bot_stdout_{timestamp}.log"
        stderr_path = LOG_DIR / f"cm_bot_stderr_{timestamp}.log"
        stdout_handle = open(stdout_path, "w", encoding="utf-8", buffering=1)
        stderr_handle = open(stderr_path, "w", encoding="utf-8", buffering=1)

        logging.info("Launching bot with interpreter: %s", sys.executable)
        logging.info("Child stdout: %s", stdout_path)
        logging.info("Child stderr: %s", stderr_path)
        self.child = subprocess.Popen(
            [sys.executable, str(BOT_SCRIPT)],
            cwd=str(BASE_DIR),
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
        )
        CHILD_PID_FILE.write_text(str(self.child.pid), encoding="utf-8")
        logging.info("cm_bot.py started with pid=%s", self.child.pid)

    def stop_child(self) -> None:
        if not self.child:
            return
        if self.child.poll() is not None:
            return
        logging.info("Stopping cm_bot.py pid=%s", self.child.pid)
        try:
            self.child.terminate()
            self.child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            logging.warning("cm_bot.py did not exit in time; killing it")
            self.child.kill()
            self.child.wait(timeout=10)
        except Exception:
            logging.exception("Failed to stop child cleanly")
        finally:
            CHILD_PID_FILE.write_text("", encoding="utf-8")

    def stop_game_processes(self) -> None:
        killed = 0
        current_pid = get_current_pid()
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["pid"] == current_pid:
                    continue
                if proc.info["name"] != GAME_PROCESS_NAME:
                    continue
                logging.warning("Stopping game process pid=%s", proc.info["pid"])
                proc.kill()
                killed += 1
            except Exception:
                logging.exception("Failed to stop game process pid=%s", proc.info.get("pid"))
        if killed:
            logging.info("Stopped %s game process(es)", killed)

    def shutdown_all(self) -> None:
        self.stop_child()
        self.stop_game_processes()

    def run(self) -> int:
        self.write_supervisor_pid()
        self.launch_bot()

        while not self.stop_requested:
            assert self.child is not None
            code = self.child.poll()
            if code is None:
                time.sleep(self.check_interval)
                continue

            logging.warning("cm_bot.py exited with code=%s", code)
            CHILD_PID_FILE.write_text("", encoding="utf-8")
            if self.stop_requested:
                break

            self.restart_count += 1
            if self.max_restarts > 0 and self.restart_count > self.max_restarts:
                logging.error("Restart limit reached (%s); supervisor will exit", self.max_restarts)
                return 2

            logging.info("Restarting cm_bot.py after %.1fs delay (restart #%s)", self.restart_delay, self.restart_count)
            time.sleep(self.restart_delay)
            self.launch_bot()

        self.shutdown_all()
        return 0


def get_current_pid() -> int:
    try:
        return os.getpid()
    except Exception:
        return -1


def _read_pid(path: Path) -> int | None:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _terminate_pid(pid: int, label: str, timeout: float = 10.0) -> None:
    try:
        proc = psutil.Process(pid)
    except psutil.Error:
        return

    try:
        if not proc.is_running():
            return
    except psutil.Error:
        return

    logging.warning("Stopping existing %s pid=%s", label, pid)
    try:
        proc.terminate()
        proc.wait(timeout=timeout)
    except psutil.TimeoutExpired:
        logging.warning("%s pid=%s did not exit in time; killing it", label, pid)
        proc.kill()
        proc.wait(timeout=timeout)
    except psutil.Error:
        logging.exception("Failed to stop %s pid=%s", label, pid)


def ensure_single_instance() -> None:
    current_pid = get_current_pid()
    existing_supervisor_pid = _read_pid(PID_FILE)
    existing_child_pid = _read_pid(CHILD_PID_FILE)

    if existing_supervisor_pid and existing_supervisor_pid != current_pid:
        _terminate_pid(existing_supervisor_pid, "supervisor")

    if existing_child_pid:
        _terminate_pid(existing_child_pid, "cm_bot child")

    try:
        PID_FILE.write_text("", encoding="utf-8")
    except Exception:
        pass
    try:
        CHILD_PID_FILE.write_text("", encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ensure_single_instance()
    configure_logging(args.log_level)

    supervisor = BotSupervisor(
        check_interval=args.check_interval,
        restart_delay=args.restart_delay,
        max_restarts=args.max_restarts,
    )

    def _request_stop(signum: int, _frame: object | None) -> None:
        logging.warning("Received signal %s, stopping supervisor", signum)
        supervisor.stop_requested = True

    for sig_name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            try:
                signal.signal(sig, _request_stop)
            except Exception:
                pass

    try:
        return supervisor.run()
    except KeyboardInterrupt:
        logging.warning("KeyboardInterrupt received, stopping supervisor")
        supervisor.stop_requested = True
        supervisor.shutdown_all()
        return 0
    except Exception:
        logging.exception("Supervisor crashed unexpectedly")
        return 1
    finally:
        try:
            PID_FILE.write_text("", encoding="utf-8")
        except Exception:
            pass
        try:
            CHILD_PID_FILE.write_text("", encoding="utf-8")
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
