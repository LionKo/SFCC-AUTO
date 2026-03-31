from __future__ import annotations

import argparse
import ctypes
import logging
import os
import subprocess
import sys
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import cv2
import mss
import numpy as np
import psutil
import win32api
import win32con
import win32gui
import win32process
from ctypes import wintypes

from flows import BootstrapFlow, CommonFlow, MainFlow, NewSeasonFlow, RecoveryFlow
from templates import FLOW_TEMPLATE_GROUPS, TEMPLATE_PATHS, get_required_templates

try:
    from rapidocr import RapidOCR
except ImportError:
    RapidOCR = None  # type: ignore[assignment]


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
LOG_DIR = BASE_DIR / "logs"
PROCESS_NAME = "FootballClubChampions.exe"
DEFAULT_STEAM_GAME_ID = "3271000"
DEFAULT_STEAM_LAUNCH_URL = ""
LOOP_EXCEPTION_RESTART_THRESHOLD = 5
BOOTSTRAP_TO_MAIN_FASTLANE_SECONDS = 12.0
POST_SAVE_SELECTION_ENTRY_FASTLANE_SECONDS = 20.0
NEW_SEASON_FASTLANE_SECONDS = 18.0
SP_JOIN_POST_CONFIRM_FASTLANE_SECONDS = 90.0
POST_SCHEDULE_EXCEPTION_FASTLANE_SECONDS = 90.0
EMERGENCY_PRIORITY_BUTTONS = ["close_button", "login_retry"]
CONFIRM_BUTTONS = ["ok_button", "ok_button2", "ok_button3", "ok_chs_button"]
CONTINUE_BUTTONS = ["continue_button", "continue_button2", "continue_button3"]
STORY_SKIP_BUTTONS = ["skip_button", "skip_button2"]
LIGHT_COMMON_BUTTONS = [*CONFIRM_BUTTONS, *CONTINUE_BUTTONS, *STORY_SKIP_BUTTONS]
EXCEPTION_CONFIRM_BUTTONS = ["final_confirm_ok_button", "final_confirm_ok_button2"]
PRIORITY_BUTTONS = EMERGENCY_PRIORITY_BUTTONS + LIGHT_COMMON_BUTTONS + EXCEPTION_CONFIRM_BUTTONS
EVENT_DIALOG_MARKERS = ["assistant", "log"]
EVENT_LOG_CHOOSE_MARKERS = ["event_choose_mark"]
CONNECTING_MARKERS: list[str] = []
CONNECTING_THRESHOLD = 0.68
LEAGUE_RESULT_TITLES: list[str] = []
LEAGUE_RESULT_CONTINUE_BUTTONS = ["league_result_continue_button", *CONTINUE_BUTTONS]
MATCH_REWARD_TITLES: list[str] = []
MATCH_REWARD_MARKERS: list[str] = []
MATCH_REWARD_SCREENS: list[str] = []
SKIP_BUTTONS = STORY_SKIP_BUTTONS
SKIP_THRESHOLD = 0.60
MAIN_SCREEN_BUTTONS = [
    "creative_mode_advance_schedule_button_small",
    "creative_mode_advance_schedule_button",
]
MAIN_SCREEN_EXTRA_MARKERS = [
    "creative_mode_special_training_button",
    "creative_mode_special_training_button3",
]
STARTUP_RECOVERY_SECONDS = 60.0
SPEED_ALREADY_THREE_MARKERS = ["creative_mode_speed3"]
SPEED_SWITCH_TRIGGER_BUTTONS = ["creative_mode_speed1"]
MATCH_REWARD_SPEED_SWITCH_MARKERS = ["match_reward_speed1"]
SPEED_THREE_BUTTONS = ["creative_mode_speed3"]
SPEED_POPUP_MARKERS = ["creative_mode_speed_popup"]
SPEED_ONE_THRESHOLD = 0.70
SPEED_THREE_CONFIRM_THRESHOLD = 0.90
SPECIAL_TRAINING_ENTRY_BUTTONS = [
    "creative_mode_special_training_button",
    "creative_mode_special_training_button3",
]
SPECIAL_TRAINING_RESET_BUTTONS = ["special_training_reset_all_button", "special_training_reset_all_button2"]
SPECIAL_TRAINING_RECOMMEND_BUTTONS = ["special_training_recommend_button", "special_training_recommend_button2"]
SPECIAL_TRAINING_EXECUTE_BUTTONS = ["special_training_execute_button", "special_training_execute_button2"]
BACK_BUTTONS = ["back_button"]
CLUB_TRANSFERS_TITLES: list[str] = []
CLUB_TRANSFERS_RENEWAL_BUTTONS = ["club_transfers_renewal_button", "club_transfers_renewal_button_2"]
CLUB_TRANSFERS_LEVEL_TITLES: list[str] = []
CLUB_TRANSFERS_SCREEN_MARKERS: list[str] = []
CLUB_TRANSFERS_THRESHOLD = 0.30
SP_JOIN_TITLES: list[str] = []
SP_JOIN_FILTER_ENTRANCES = ["sp_join_filter_entrance"]
SP_JOIN_FILTER_POPUPS: list[str] = []
SP_JOIN_BUTTONS = ["sp_join_button1", "sp_join_button2", "sp_join_button3", "sp_join_button4"]
SP_JOIN_BELONG_MARKERS = ["sp_belong"]
SP_JOIN_SCREEN_MARKERS = ["sp_belong"]
SP_JOIN_THRESHOLD = 0.40
SP_BELONG_THRESHOLD = 0.72
SP_JOIN_SCROLL_RATIO = (0.82, 0.52)
SP_JOIN_SCROLL_STEPS_TO_BOTTOM = 7
SP_JOIN_SCROLL_DELTA = -120
FINAL_CONFIRM_TITLES: list[str] = []
FINAL_CONFIRM_BUTTONS = ["final_confirm_ok_button", "final_confirm_ok_button2"]
LOGIN_SCREEN_LOGO_MARKERS = ["login_mark"]
NON_RESIZABLE_TEMPLATES = {"login_mark"}
GAME_MAIN_SCREEN_MARKERS: list[str] = []
GAME_MAIN_MARKERS = ["game_main_mark"]
GAME_MAIN_MARK_THRESHOLD = 0.65
SAVE_SELECTION_MARKERS: list[str] = []
SAVE_SELECTION_TITLE_MARKERS: list[str] = []
SAVE_SLOT_THIRD_RATIO = (0.80, 0.45)
MAIN_SCREEN_SPECIAL_TRAINING_RATIO = (0.503, 0.931)
MAIN_SCREEN_SCHEDULE_RATIOS = [
    (0.885, 0.900),
    (0.930, 0.945),
    (0.835, 0.855),
]
STORY_PROGRESS_HOTSPOT_RATIO = (0.498, 0.388)
CLUB_TRANSFERS_MIN_RATIO = (0.334, 0.642)
EXPECTED_CLIENT_WIDTH = 1920
EXPECTED_CLIENT_HEIGHT = 1080
CLIENT_SIZE_TOLERANCE_PIXELS = 6
SCREEN_STUCK_TIMEOUT_SECONDS = 120.0
NO_SCHEDULE_TIMEOUT_SECONDS = 900.0
BOOTSTRAP_TIMEOUT_SECONDS = 180.0
BOOTSTRAP_POST_LOGIN_GAME_MAIN_SECONDS = 20.0
VISUAL_STALL_TIMEOUT_SECONDS = 120.0
VISUAL_STALL_CHECK_INTERVAL_SECONDS = 5.0
VISUAL_STALL_DIFF_THRESHOLD = 1.2
RECOVERY_STORY_STREAK_RESET_SECONDS = 8.0
RECOVERY_STORY_STREAK_THRESHOLD = 3
STAGE_STUCK_RESTART_FLOWS = {"generic", "main"}
STAGE_STUCK_RESTART_STAGES = {
    "creative_mode_main",
    "special_training",
    "match_reward",
    "league_result",
    "connecting",
    "event_dialog",
}
LOGIN_SCREEN_THRESHOLD = 0.55
STAGE_SCAN_BASE_INTERVAL_SECONDS = 4.0
STAGE_SCAN_UNKNOWN_INTERVAL_SECONDS = 1.5
FULL_STAGE_SCAN_INTERVAL_SECONDS = 10.0
STAGE_STICKY_SECONDS = 6.0
SPECIAL_TRAINING_RETRY_COOLDOWN_SECONDS = 30.0
CLUB_TRANSFERS_MIN_CLICK_COOLDOWN_SECONDS = 4.0
SP_JOIN_SLOT_CENTERS = [
    (558, 338),
    (815, 338),
    (1073, 338),
    (1330, 338),
    (1588, 338),
    (558, 620),
    (815, 620),
    (1073, 620),
    (1330, 620),
    (1588, 620),
    (558, 903),
]

ACTIONABLE_OPERATION_MARKERS = [
    "close_button",
    "match_result_button",
    "continue_button",
    "continue_button2",
    "continue_button3",
    "assistant",
    "log",
    "event_choose_mark",
    "skip_button",
    "skip_button2",
    "login_retry",
    "match_reward_speed1",
    "club_transfers_renewal_button",
    "club_transfers_renewal_button_2",
    "club_transfers_min_button",
    "sp_join_filter_entrance",
    "sp_belong",
    "sp_join_button1",
    "sp_join_button2",
    "sp_join_button3",
    "sp_join_button4",
    "final_confirm_ok_button",
    "final_confirm_ok_button2",
    "login_mark",
    "game_main_mark",
    "creative_mode_advance_schedule_button",
    "creative_mode_advance_schedule_button_small",
    "creative_mode_speed1",
    "match_reward_speed1",
    "creative_mode_speed_popup",
    "creative_mode_special_training_button",
    "creative_mode_special_training_button3",
    "special_training_reset_all_button",
    "special_training_reset_all_button2",
    "special_training_recommend_button",
    "special_training_recommend_button2",
    "special_training_execute_button",
    "special_training_execute_button2",
    "ok_button",
    "ok_button2",
    "ok_button3",
    "ok_chs_button",
    "back_button",
]

OCR_TEXT_LEAGUE_RESULT = ("联赛结果",)
OCR_TEXT_MATCH_REWARD = ("收支球迷", "收支·球迷")
OCR_TEXT_CLUB_TRANSFERS = ("俱乐部转会",)
OCR_TEXT_CLUB_TRANSFERS_LEVEL = ("选择联赛等级",)
OCR_TEXT_SPONSOR_SELECTION = ("选择赞助商",)
OCR_TEXT_SP_JOIN = ("特殊球员加盟",)
OCR_TEXT_FINAL_CONFIRM = ("最终确认",)
OCR_TEXT_SAVE_SELECTION = ("保存数据一览",)
OCR_TEXT_SPECIAL_TRAINING_SETTINGS = ("特别训练设置",)
OCR_TEXT_SPECIAL_TRAINING_RESULT = ("特别训练结果",)


@dataclass(frozen=True)
class MatchResult:
    name: str
    score: float
    left: int
    top: int
    width: int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        return (self.left + self.width // 2, self.top + self.height // 2)


@dataclass(frozen=True)
class ScreenRegion:
    left_ratio: float
    top_ratio: float
    right_ratio: float
    bottom_ratio: float


@dataclass(frozen=True)
class ScreenProbe:
    names: tuple[str, ...]
    threshold: float
    region: ScreenRegion | None = None
    allow_fullscreen_fallback: bool = False


REGION_FULL = ScreenRegion(0.0, 0.0, 1.0, 1.0)
REGION_WIDE_TOP = ScreenRegion(0.0, 0.0, 1.0, 0.32)
REGION_TOP_LEFT = ScreenRegion(0.0, 0.0, 0.38, 0.30)
REGION_LOGIN_TOP_LEFT = ScreenRegion(0.0, 0.0, 0.45, 0.45)
REGION_TOP_CENTER = ScreenRegion(0.22, 0.0, 0.78, 0.30)
REGION_TOP_RIGHT = ScreenRegion(0.58, 0.0, 1.0, 0.28)
REGION_LEFT_PANEL = ScreenRegion(0.0, 0.08, 0.34, 0.95)
REGION_CENTER = ScreenRegion(0.18, 0.12, 0.82, 0.88)
REGION_CENTER_RIGHT = ScreenRegion(0.50, 0.10, 1.0, 0.92)
REGION_BOTTOM_HALF = ScreenRegion(0.0, 0.55, 1.0, 1.0)
REGION_BOTTOM_LEFT = ScreenRegion(0.0, 0.50, 0.22, 1.0)
REGION_BOTTOM_RIGHT = ScreenRegion(0.56, 0.56, 1.0, 1.0)
REGION_SCHEDULE_BUTTON = ScreenRegion(0.76, 0.74, 0.99, 0.99)
SPECIAL_TRAINING_ACTION_REGION = ScreenRegion(0.24, 0.52, 0.86, 0.94)

INPUT_MOUSE = 0

try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.WPARAM),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


class TemplateStore:
    def __init__(self, directory: Path, template_paths: dict[str, str] | None = None) -> None:
        self.directory = directory
        self.template_paths = template_paths or {}
        self.templates: dict[str, np.ndarray] = {}

    def _template_path(self, name: str) -> Path:
        relative = self.template_paths.get(name, name)
        path = Path(relative)
        if path.suffix.lower() != ".png":
            path = path.with_suffix(".png")
        return self.directory / path

    def load(self, names: Iterable[str]) -> None:
        for name in names:
            if name in self.templates:
                continue
            path = self._template_path(name)
            if not path.exists():
                logging.debug("Template file missing, skipping: %s", path)
                continue
            image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                raise FileNotFoundError(f"Unable to load template: {path}")
            self.templates[name] = image

    def get(self, name: str) -> np.ndarray:
        return self.templates[name]


class GameWindow:
    def __init__(self, process_name: str) -> None:
        self.process_name = process_name.lower()
        self.hwnd: int | None = None
        self.last_click_time = time.time()

    def find_process_pids(self) -> list[int]:
        return [
            proc.info["pid"]
            for proc in psutil.process_iter(["pid", "name"])
            if (proc.info["name"] or "").lower() == self.process_name
        ]

    def is_process_running(self) -> bool:
        return bool(self.find_process_pids())

    def kill_processes(self) -> int:
        killed = 0
        for proc in psutil.process_iter(["pid", "name"]):
            if (proc.info["name"] or "").lower() != self.process_name:
                continue
            try:
                proc.kill()
                killed += 1
            except Exception:
                logging.exception("Failed to kill process pid=%s", proc.info["pid"])
        self.hwnd = None
        return killed

    def attach(self) -> int:
        target_pids = set(self.find_process_pids())
        if not target_pids:
            raise RuntimeError(f"Process not found: {self.process_name}")

        matched_hwnds: list[int] = []

        def enum_handler(hwnd: int, _: int) -> None:
            if not win32gui.IsWindowVisible(hwnd):
                return
            if win32gui.GetParent(hwnd) != 0:
                return
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid not in target_pids:
                return
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return
            matched_hwnds.append(hwnd)

        win32gui.EnumWindows(enum_handler, 0)

        if not matched_hwnds:
            raise RuntimeError("Game process found, but no visible top-level window was found")

        self.hwnd = matched_hwnds[0]
        logging.info("Attached game window hwnd=%s title=%s", self.hwnd, win32gui.GetWindowText(self.hwnd))
        return self.hwnd

    def ensure_foreground(self) -> None:
        if self.hwnd is None:
            self.attach()
        assert self.hwnd is not None
        if win32gui.IsIconic(self.hwnd):
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            time.sleep(0.5)
        try:
            win32gui.SetForegroundWindow(self.hwnd)
        except Exception:
            logging.debug("SetForegroundWindow failed, continuing anyway")
        time.sleep(0.3)

    def client_rect_screen(self) -> dict[str, int]:
        if self.hwnd is None:
            self.attach()
        assert self.hwnd is not None
        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        screen_left, screen_top = win32gui.ClientToScreen(self.hwnd, (left, top))
        screen_right, screen_bottom = win32gui.ClientToScreen(self.hwnd, (right, bottom))
        return {
            "left": screen_left,
            "top": screen_top,
            "width": screen_right - screen_left,
            "height": screen_bottom - screen_top,
        }

    def _send_mouse_button(self, flag: int) -> None:
        mouse_input = MOUSEINPUT(0, 0, 0, flag, 0, 0)
        command = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mouse_input))
        sent = ctypes.windll.user32.SendInput(1, ctypes.byref(command), ctypes.sizeof(INPUT))
        if sent != 1:
            raise RuntimeError(f"SendInput failed for mouse flag {flag}")

    def scroll_client(self, x: int, y: int, delta: int, settle: float = 0.25) -> None:
        if self.hwnd is None:
            self.attach()
        assert self.hwnd is not None
        screen_x, screen_y = win32gui.ClientToScreen(self.hwnd, (x, y))
        self.ensure_foreground()
        win32api.SetCursorPos((screen_x, screen_y))
        time.sleep(0.08)
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
        time.sleep(0.08)
        avoid_x, avoid_y = win32gui.ClientToScreen(
            self.hwnd,
            (EXPECTED_CLIENT_WIDTH // 2, int(EXPECTED_CLIENT_HEIGHT * 0.18)),
        )
        win32api.SetCursorPos((avoid_x, avoid_y))
        logging.info("Scrolled client at (%s, %s) with delta %s", x, y, delta)
        time.sleep(settle)

    def click_client(self, x: int, y: int, settle: float = 0.8) -> None:
        if self.hwnd is None:
            self.attach()
        assert self.hwnd is not None
        screen_x, screen_y = win32gui.ClientToScreen(self.hwnd, (x, y))
        self.ensure_foreground()
        win32api.SetCursorPos((screen_x, screen_y))
        time.sleep(0.12)
        self._send_mouse_button(win32con.MOUSEEVENTF_LEFTDOWN)
        time.sleep(0.06)
        self._send_mouse_button(win32con.MOUSEEVENTF_LEFTUP)
        time.sleep(0.12)
        avoid_x, avoid_y = win32gui.ClientToScreen(
            self.hwnd,
            (EXPECTED_CLIENT_WIDTH // 2, int(EXPECTED_CLIENT_HEIGHT * 0.18)),
        )
        win32api.SetCursorPos((avoid_x, avoid_y))
        self.last_click_time = time.time()
        logging.info("Clicked client position (%s, %s)", x, y)
        time.sleep(settle)

    def click_client_center(self, settle: float = 0.5) -> None:
        rect = self.client_rect_screen()
        center_x = rect["width"] // 2
        center_y = rect["height"] // 2
        self.click_client(center_x, center_y, settle=settle)

    def click_client_bottom_right(self, x_ratio: float = 0.9, y_ratio: float = 0.9, settle: float = 0.35) -> None:
        rect = self.client_rect_screen()
        x = max(1, min(rect["width"] - 1, int(rect["width"] * x_ratio)))
        y = max(1, min(rect["height"] - 1, int(rect["height"] * y_ratio)))
        self.click_client(x, y, settle=settle)

    def move_cursor_client(self, x_ratio: float = 0.9, y_ratio: float = 0.9) -> None:
        if self.hwnd is None:
            self.attach()
        assert self.hwnd is not None
        rect = self.client_rect_screen()
        x = max(1, min(rect["width"] - 1, int(rect["width"] * x_ratio)))
        y = max(1, min(rect["height"] - 1, int(rect["height"] * y_ratio)))
        screen_x, screen_y = win32gui.ClientToScreen(self.hwnd, (x, y))
        self.ensure_foreground()
        try:
            win32api.SetCursorPos((screen_x, screen_y))
        except Exception as exc:
            logging.warning("Failed to move cursor to client position (%s, %s): %s", x, y, exc)
            return
        logging.debug("Moved cursor to client position (%s, %s)", x, y)
        time.sleep(0.2)


class Vision:
    def __init__(self, window: GameWindow, templates: TemplateStore) -> None:
        self.window = window
        self.templates = templates
        self.sct = mss.mss()
        self._resized_template_cache: dict[tuple[str, int, int], np.ndarray] = {}
        if RapidOCR is None:
            raise RuntimeError(
                "RapidOCR is not installed. Run `pip install -r requirements.txt` in sfcc_CM before starting the bot."
            )
        self.ocr = RapidOCR()

    def capture(self) -> np.ndarray:
        rect = self.window.client_rect_screen()
        shot = self.sct.grab(rect)
        frame = np.array(shot)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    def crop_to_region(self, screenshot: np.ndarray, region: ScreenRegion) -> tuple[np.ndarray, int, int]:
        height, width = screenshot.shape[:2]
        left = max(0, min(width - 1, int(width * region.left_ratio)))
        top = max(0, min(height - 1, int(height * region.top_ratio)))
        right = max(left + 1, min(width, int(width * region.right_ratio)))
        bottom = max(top + 1, min(height, int(height * region.bottom_ratio)))
        return screenshot[top:bottom, left:right], left, top

    def _fit_template_to_screenshot(
        self,
        template: np.ndarray,
        screenshot: np.ndarray,
        name: str,
    ) -> np.ndarray | None:
        if template.shape[0] <= screenshot.shape[0] and template.shape[1] <= screenshot.shape[1]:
            return template

        if name in NON_RESIZABLE_TEMPLATES:
            logging.debug(
                "Skipping resize for non-resizable template %s because it is larger than the current search area (%sx%s > %sx%s)",
                name,
                template.shape[1],
                template.shape[0],
                screenshot.shape[1],
                screenshot.shape[0],
            )
            return None

        # Allow oversized templates to be scaled down to the current client area.
        # This keeps whole-screen/page markers usable when the game window is slightly shorter.
        if template.shape[0] == 0 or template.shape[1] == 0:
            return None

        cache_key = (name, screenshot.shape[1], screenshot.shape[0])
        cached = self._resized_template_cache.get(cache_key)
        if cached is not None:
            return cached

        scale = min(
            screenshot.shape[1] / float(template.shape[1]),
            screenshot.shape[0] / float(template.shape[0]),
        )
        if scale <= 0:
            return None

        new_width = max(1, int(round(template.shape[1] * scale)))
        new_height = max(1, int(round(template.shape[0] * scale)))
        resized = cv2.resize(
            template,
            (new_width, new_height),
            interpolation=cv2.INTER_AREA,
        )
        logging.debug(
            "Resized oversized template %s proportionally from %sx%s to %sx%s",
            name,
            template.shape[1],
            template.shape[0],
            resized.shape[1],
            resized.shape[0],
        )
        self._resized_template_cache[cache_key] = resized
        return resized

    def match_best(self, screenshot: np.ndarray, names: Iterable[str], threshold: float) -> MatchResult | None:
        best: MatchResult | None = None
        for name in names:
            if name not in self.templates.templates:
                continue
            original_template = self.templates.get(name)
            template = self._fit_template_to_screenshot(original_template, screenshot, name)
            if template is None:
                continue
            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            _, score, _, location = cv2.minMaxLoc(result)
            if score < threshold:
                continue
            candidate = MatchResult(
                name=name,
                score=float(score),
                left=int(location[0]),
                top=int(location[1]),
                width=int(template.shape[1]),
                height=int(template.shape[0]),
            )
            if best is None or candidate.score > best.score:
                best = candidate
        return best

    def match_best_in_region(
        self,
        screenshot: np.ndarray,
        names: Iterable[str],
        threshold: float,
        region: ScreenRegion,
    ) -> MatchResult | None:
        if region == REGION_FULL:
            return self.match_best(screenshot, names, threshold)
        cropped, offset_x, offset_y = self.crop_to_region(screenshot, region)
        match = self.match_best(cropped, names, threshold)
        if not match:
            return None
        return MatchResult(
            name=match.name,
            score=match.score,
            left=match.left + offset_x,
            top=match.top + offset_y,
            width=match.width,
            height=match.height,
        )

    def match_best_multiscale_in_region(
        self,
        screenshot: np.ndarray,
        names: Iterable[str],
        threshold: float,
        region: ScreenRegion,
        scales: Iterable[float],
    ) -> MatchResult | None:
        cropped, offset_x, offset_y = self.crop_to_region(screenshot, region)
        best: MatchResult | None = None
        for name in names:
            if name not in self.templates.templates:
                continue
            original_template = self.templates.get(name)
            for scale in scales:
                if scale <= 0:
                    continue
                if abs(scale - 1.0) < 0.01:
                    template = original_template
                else:
                    new_width = max(1, int(round(original_template.shape[1] * scale)))
                    new_height = max(1, int(round(original_template.shape[0] * scale)))
                    template = cv2.resize(original_template, (new_width, new_height), interpolation=cv2.INTER_AREA)
                if template.shape[0] > cropped.shape[0] or template.shape[1] > cropped.shape[1]:
                    continue
                result = cv2.matchTemplate(cropped, template, cv2.TM_CCOEFF_NORMED)
                _, score, _, location = cv2.minMaxLoc(result)
                if score < threshold:
                    continue
                candidate = MatchResult(
                    name=name,
                    score=float(score),
                    left=int(location[0]) + offset_x,
                    top=int(location[1]) + offset_y,
                    width=int(template.shape[1]),
                    height=int(template.shape[0]),
                )
                if best is None or candidate.score > best.score:
                    best = candidate
        return best

    def match_all(
        self,
        screenshot: np.ndarray,
        names: Iterable[str],
        threshold: float,
        max_matches: int = 20,
    ) -> list[MatchResult]:
        matches: list[MatchResult] = []
        for name in names:
            if name not in self.templates.templates:
                continue
            original_template = self.templates.get(name)
            template = self._fit_template_to_screenshot(original_template, screenshot, name)
            if template is None:
                continue
            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            work = result.copy()
            for _ in range(max_matches):
                _, score, _, location = cv2.minMaxLoc(work)
                if score < threshold:
                    break
                matches.append(
                    MatchResult(
                        name=name,
                        score=float(score),
                        left=int(location[0]),
                        top=int(location[1]),
                        width=int(template.shape[1]),
                        height=int(template.shape[0]),
                    )
                )
                x0 = max(0, int(location[0] - template.shape[1] // 2))
                y0 = max(0, int(location[1] - template.shape[0] // 2))
                x1 = min(work.shape[1], int(location[0] + template.shape[1] // 2))
                y1 = min(work.shape[0], int(location[1] + template.shape[0] // 2))
                work[y0:y1, x0:x1] = -1.0
        matches.sort(key=lambda item: item.score, reverse=True)
        return matches

    def match_all_in_region(
        self,
        screenshot: np.ndarray,
        names: Iterable[str],
        threshold: float,
        region: ScreenRegion,
        max_matches: int = 20,
    ) -> list[MatchResult]:
        if region == REGION_FULL:
            return self.match_all(screenshot, names, threshold, max_matches=max_matches)
        cropped, offset_x, offset_y = self.crop_to_region(screenshot, region)
        matches = self.match_all(cropped, names, threshold, max_matches=max_matches)
        return [
            MatchResult(
                name=match.name,
                score=match.score,
                left=match.left + offset_x,
                top=match.top + offset_y,
                width=match.width,
                height=match.height,
            )
            for match in matches
        ]

    def wait_for_any(
        self,
        names: Iterable[str],
        threshold: float,
        timeout: float,
        interval: float = 0.8,
    ) -> MatchResult | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            screenshot = self.capture()
            match = self.match_best(screenshot, names, threshold)
            if match:
                return match
            time.sleep(interval)
        return None

    def save_debug_screenshot(self, prefix: str) -> Path:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = LOG_DIR / f"{prefix}_{timestamp}.png"
        screenshot = self.capture()
        cv2.imwrite(str(path), screenshot)
        logging.info("Saved debug screenshot: %s", path)
        return path

    def _normalize_ocr_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text)
        return "".join(
            char
            for char in normalized
            if unicodedata.category(char)[0] not in {"P", "S", "Z", "C"}
        ).lower()

    def _extract_ocr_lines(self, ocr_result: object) -> list[tuple[np.ndarray, str, float]]:
        lines: list[tuple[np.ndarray, str, float]] = []
        boxes = getattr(ocr_result, "boxes", None)
        txts = getattr(ocr_result, "txts", None)
        scores = getattr(ocr_result, "scores", None)
        if boxes is not None and txts is not None:
            for index, text in enumerate(txts):
                if not text:
                    continue
                try:
                    box = np.asarray(boxes[index], dtype=np.float32)
                except Exception:
                    continue
                score = 1.0
                if scores is not None and index < len(scores):
                    try:
                        score = float(scores[index])
                    except Exception:
                        score = 1.0
                lines.append((box, str(text), score))
            return lines

        if isinstance(ocr_result, tuple) and ocr_result:
            raw_items = ocr_result[0]
            if isinstance(raw_items, list):
                for item in raw_items:
                    if not isinstance(item, (list, tuple)) or len(item) < 2:
                        continue
                    box = np.asarray(item[0], dtype=np.float32)
                    payload = item[1]
                    if isinstance(payload, (list, tuple)) and payload:
                        text = str(payload[0])
                        score = float(payload[1]) if len(payload) > 1 else 1.0
                    else:
                        text = str(payload)
                        score = 1.0
                    if text:
                        lines.append((box, text, score))
        return lines

    def find_text_in_region(
        self,
        screenshot: np.ndarray,
        texts: Iterable[str],
        region: ScreenRegion,
        min_score: float = 0.35,
    ) -> MatchResult | None:
        cropped, offset_x, offset_y = self.crop_to_region(screenshot, region)
        if cropped.size == 0:
            return None

        upscaled = cv2.resize(cropped, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        ocr_result = self.ocr(upscaled)
        if ocr_result is None:
            return None

        target_map = {
            self._normalize_ocr_text(text): text
            for text in texts
            if self._normalize_ocr_text(text)
        }
        if not target_map:
            return None

        best: MatchResult | None = None
        for box, detected_text, score in self._extract_ocr_lines(ocr_result):
            normalized_detected = self._normalize_ocr_text(detected_text)
            if not normalized_detected:
                continue

            matched = False
            for normalized_target in target_map:
                if normalized_target in normalized_detected or normalized_detected in normalized_target:
                    matched = True
                    break
            if not matched:
                continue

            score = float(score)
            if score < min_score:
                continue

            xs = box[:, 0] / 2.0
            ys = box[:, 1] / 2.0
            left = int(max(0.0, np.min(xs))) + offset_x
            top = int(max(0.0, np.min(ys))) + offset_y
            width = max(1, int(np.max(xs) - np.min(xs)))
            height = max(1, int(np.max(ys) - np.min(ys)))
            candidate = MatchResult(
                name=f"ocr:{detected_text}",
                score=score,
                left=left,
                top=top,
                width=width,
                height=height,
            )
            if best is None or candidate.score > best.score:
                best = candidate
        return best


class CreativeModeBot:
    def __init__(
        self,
        vision: Vision,
        window: GameWindow,
        main_threshold: float,
        button_threshold: float,
        dialog_threshold: float,
        steam_game_id: str = "",
        steam_launch_url: str = "",
        game_exe_path: Path | None = None,
    ) -> None:
        self.vision = vision
        self.window = window
        self.main_threshold = main_threshold
        self.button_threshold = button_threshold
        self.dialog_threshold = dialog_threshold
        self.steam_game_id = steam_game_id.strip()
        self.steam_launch_url = steam_launch_url.strip()
        self.game_exe_path = game_exe_path
        now = time.time()
        self.last_advance_schedule_click_time = 0.0
        self.last_stage_signature = "initializing"
        self.last_stage_change_time = now
        self.last_stage_probe_time = 0.0
        self.last_full_stage_scan_time = 0.0
        self.restart_requested = False
        self.restart_reason = ""
        self.awaiting_save_selection = False
        self.awaiting_main_after_save_selection = False
        self.last_bootstrap_to_main_time = 0.0
        self.last_save_selection_click_time = 0.0
        self.last_new_season_activity_time = 0.0
        self.last_final_confirm_time = 0.0
        self.last_generic_confirm_click_time = 0.0
        self.last_special_training_run_time = 0.0
        self.last_club_transfers_min_click_time = 0.0
        self.last_bootstrap_login_click_time = 0.0
        self.special_training_unavailable_until = 0.0
        self.recovery_story_streak = 0
        self.last_recovery_story_seen_time = 0.0
        self.active_flow = "generic"
        self.last_visual_probe_time = 0.0
        self.last_visual_change_time = now
        self.last_visual_signature: np.ndarray | None = None
        self._frame_eval_cache: dict[tuple[int, str, object], object] = {}
        self.common_flow = CommonFlow(self)
        self.bootstrap_flow = BootstrapFlow(self)
        self.main_flow = MainFlow(self)
        self.new_season_flow = NewSeasonFlow(self)
        self.recovery_flow = RecoveryFlow(self)

    def request_restart(self, reason: str) -> None:
        if self.restart_requested:
            return
        self.restart_requested = True
        self.restart_reason = reason
        logging.error("Restart requested: %s", reason)

    def set_active_flow(self, flow_name: str) -> None:
        if flow_name == self.active_flow:
            return
        logging.debug("Active flow changed: %s -> %s", self.active_flow, flow_name)
        self.active_flow = flow_name

    def invalidate_runtime_stage(self, reason: str, new_stage: str = "unknown") -> None:
        now = time.time()
        if self.last_stage_signature != new_stage:
            logging.info("Stage changed: %s -> %s", self.last_stage_signature, new_stage)
        self.last_stage_signature = new_stage
        self.last_stage_change_time = now
        self.last_stage_probe_time = 0.0
        logging.info("Runtime stage invalidated because %s", reason)

    def _pick_best_match(self, *matches: MatchResult | None) -> MatchResult | None:
        available = [match for match in matches if match is not None]
        if not available:
            return None
        return max(available, key=lambda item: item.score)

    def _get_frame_cached(self, screenshot: np.ndarray, tag: str, extra: object = None) -> object | None:
        return self._frame_eval_cache.get((id(screenshot), tag, extra))

    def _has_frame_cached(self, screenshot: np.ndarray, tag: str, extra: object = None) -> bool:
        return (id(screenshot), tag, extra) in self._frame_eval_cache

    def _set_frame_cached(self, screenshot: np.ndarray, tag: str, value: object, extra: object = None) -> object:
        if len(self._frame_eval_cache) >= 512:
            self._frame_eval_cache.clear()
        self._frame_eval_cache[(id(screenshot), tag, extra)] = value
        return value

    def _match_probe(self, screenshot: np.ndarray, probe: ScreenProbe) -> MatchResult | None:
        region = probe.region or REGION_FULL
        match = self.vision.match_best_in_region(screenshot, probe.names, probe.threshold, region)
        if match or not probe.allow_fullscreen_fallback or region == REGION_FULL:
            return match
        return self.vision.match_best(screenshot, probe.names, probe.threshold)

    def _match_screen_profile(
        self,
        screenshot: np.ndarray,
        strong_probes: list[ScreenProbe],
        support_probes: list[ScreenProbe] | None = None,
        min_strong: int = 1,
        min_total: int | None = None,
    ) -> MatchResult | None:
        strong_matches = [self._match_probe(screenshot, probe) for probe in strong_probes]
        present_strong = [match for match in strong_matches if match is not None]
        if len(present_strong) < min_strong:
            return None

        support_matches: list[MatchResult] = []
        if support_probes:
            support_matches = [match for probe in support_probes if (match := self._match_probe(screenshot, probe)) is not None]

        if min_total is not None and len(present_strong) + len(support_matches) < min_total:
            return None

        return self._pick_best_match(*present_strong, *support_matches)

    def _match_ocr_title(
        self,
        screenshot: np.ndarray,
        texts: Iterable[str],
        region: ScreenRegion = REGION_WIDE_TOP,
        min_score: float = 0.35,
    ) -> MatchResult | None:
        text_tuple = tuple(texts)
        cache_key = (text_tuple, region.left_ratio, region.top_ratio, region.right_ratio, region.bottom_ratio, round(min_score, 3))
        if self._has_frame_cached(screenshot, "ocr_title", cache_key):
            return self._get_frame_cached(screenshot, "ocr_title", cache_key)  # type: ignore[return-value]
        result = self.vision.find_text_in_region(screenshot, text_tuple, region, min_score=min_score)
        return self._set_frame_cached(screenshot, "ocr_title", result, cache_key)  # type: ignore[return-value]

    def _candidate_steam_paths(self) -> list[Path]:
        candidates: list[Path] = []
        env_vars = [
            os.environ.get("PROGRAMFILES(X86)"),
            os.environ.get("PROGRAMFILES"),
            os.environ.get("STEAM_PATH"),
        ]
        for base in env_vars:
            if not base:
                continue
            base_path = Path(base)
            if base_path.name.lower() == "steam":
                candidates.append(base_path / "steam.exe")
            else:
                candidates.append(base_path / "Steam" / "steam.exe")
        candidates.extend(
            [
                Path(r"C:\Program Files (x86)\Steam\steam.exe"),
                Path(r"C:\Program Files\Steam\steam.exe"),
            ]
        )
        unique: list[Path] = []
        seen: set[str] = set()
        for path in candidates:
            normalized = str(path).lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            unique.append(path)
        return unique

    def _find_steam_executable(self) -> Path | None:
        for path in self._candidate_steam_paths():
            if path.exists():
                return path
        return None

    def launch_game(self) -> bool:
        launch_target = self.steam_launch_url
        if not launch_target and self.steam_game_id:
            launch_target = f"steam://rungameid/{self.steam_game_id}"

        if launch_target:
            try:
                os.startfile(launch_target)
            except Exception:
                logging.exception("Failed to launch game via Steam URL: %s", launch_target)
            else:
                logging.info("Launched game via Steam URL: %s", launch_target)
                self.window.hwnd = None
                return True

        if self.steam_game_id:
            steam_exe = self._find_steam_executable()
            if steam_exe is not None:
                try:
                    subprocess.Popen([str(steam_exe), "-applaunch", self.steam_game_id], cwd=str(steam_exe.parent))
                except Exception:
                    logging.exception("Failed to launch game via Steam executable: %s -applaunch %s", steam_exe, self.steam_game_id)
                else:
                    logging.info("Launched game via Steam executable: %s -applaunch %s", steam_exe, self.steam_game_id)
                    self.window.hwnd = None
                    return True
            else:
                logging.warning("Steam executable not found in common install paths; skipping -applaunch fallback")

        if self.game_exe_path is not None:
            if not self.game_exe_path.exists():
                logging.error("Configured game executable does not exist: %s", self.game_exe_path)
                return False
            try:
                subprocess.Popen([str(self.game_exe_path)], cwd=str(self.game_exe_path.parent))
            except Exception:
                logging.exception("Failed to launch game executable: %s", self.game_exe_path)
                return False
            logging.info("Launched game executable: %s", self.game_exe_path)
            self.window.hwnd = None
            return True

        logging.error(
            "No launch method configured. Set --steam-game-id, --steam-launch-url, or --game-exe-path."
        )
        return False

    def wait_for_process_window(self, timeout_seconds: float = 60.0) -> bool:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if not self.window.is_process_running():
                time.sleep(1.0)
                continue
            try:
                self.window.attach()
                return True
            except Exception:
                time.sleep(1.0)
        logging.error("Game process/window did not become ready within timeout")
        return False

    def restart_game(self, reason: str) -> bool:
        for attempt in range(1, 4):
            logging.warning("Restarting game because: %s (attempt %s/3)", reason, attempt)
            killed = self.window.kill_processes()
            if killed:
                logging.info("Killed %s game process(es)", killed)
            time.sleep(3.0)
            if not self.launch_game():
                continue
            if not self.wait_for_process_window():
                continue
            self.restart_requested = False
            self.restart_reason = ""
            now = time.time()
            self.last_stage_signature = "restarted"
            self.last_stage_change_time = now
            self.last_stage_probe_time = 0.0
            self.last_full_stage_scan_time = 0.0
            self.last_advance_schedule_click_time = 0.0
            self.window.last_click_time = now
            self.awaiting_save_selection = False
            self.awaiting_main_after_save_selection = False
            self.last_bootstrap_to_main_time = 0.0
            self.last_save_selection_click_time = 0.0
            self.last_new_season_activity_time = 0.0
            self.last_final_confirm_time = 0.0
            self.last_special_training_run_time = 0.0
            self.last_club_transfers_min_click_time = 0.0
            self.last_bootstrap_login_click_time = 0.0
            self.special_training_unavailable_until = 0.0
            self.recovery_story_streak = 0
            self.last_recovery_story_seen_time = 0.0
            self.active_flow = "bootstrap"
            self.last_visual_probe_time = 0.0
            self.last_visual_change_time = now
            self.last_visual_signature = None
            if self.run_bootstrap_flow():
                return True
            logging.warning("Bootstrap flow failed after restart attempt %s, retrying", attempt)
        logging.error("Restart flow failed after repeated attempts")
        return False

    def ensure_attached(self) -> bool:
        try:
            self.window.attach()
            return True
        except Exception as exc:
            logging.warning("Unable to attach game window: %s", exc)
            return False

    def is_main_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_main_screen_in_screenshot(screenshot)

    def wait_for_special_training_title(
        self,
        texts: Iterable[str],
        timeout: float,
        interval: float = 0.2,
    ) -> MatchResult | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            screenshot = self.vision.capture()
            match = self._match_ocr_title(screenshot, texts, REGION_WIDE_TOP, min_score=0.35) or self._match_ocr_title(
                screenshot,
                texts,
                REGION_LOGIN_TOP_LEFT,
                min_score=0.35,
            )
            if match:
                return match
            time.sleep(interval)
        return None

    def find_main_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        if self._has_frame_cached(screenshot, "main_screen"):
            return self._get_frame_cached(screenshot, "main_screen")  # type: ignore[return-value]
        result = self._match_screen_profile(
            screenshot,
            strong_probes=[
                ScreenProbe(tuple(MAIN_SCREEN_BUTTONS), min(self.main_threshold, 0.55), REGION_SCHEDULE_BUTTON),
                ScreenProbe(tuple(MAIN_SCREEN_EXTRA_MARKERS), min(self.button_threshold, 0.85), REGION_BOTTOM_HALF),
                ScreenProbe(tuple(SPEED_SWITCH_TRIGGER_BUTTONS + SPEED_ALREADY_THREE_MARKERS), min(self.button_threshold, 0.72), REGION_TOP_RIGHT),
            ],
            min_strong=1,
        )
        return self._set_frame_cached(screenshot, "main_screen", result)  # type: ignore[return-value]

    def find_special_training_title_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        return self._match_ocr_title(
            screenshot,
            OCR_TEXT_SPECIAL_TRAINING_SETTINGS,
            REGION_WIDE_TOP,
            min_score=0.35,
        ) or self._match_ocr_title(
            screenshot,
            OCR_TEXT_SPECIAL_TRAINING_SETTINGS,
            REGION_LOGIN_TOP_LEFT,
            min_score=0.35,
        )

    def find_special_training_result_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        title = self._match_ocr_title(
            screenshot,
            OCR_TEXT_SPECIAL_TRAINING_RESULT,
            REGION_WIDE_TOP,
            min_score=0.35,
        ) or self._match_ocr_title(
            screenshot,
            OCR_TEXT_SPECIAL_TRAINING_RESULT,
            REGION_LOGIN_TOP_LEFT,
            min_score=0.35,
        )
        if not title:
            return None
        back_button = self.vision.match_best_in_region(
            screenshot,
            BACK_BUTTONS,
            min(self.button_threshold, 0.72),
            REGION_TOP_LEFT,
        )
        confirm_button = self.vision.match_best(
            screenshot,
            CONFIRM_BUTTONS + CONTINUE_BUTTONS,
            min(self.button_threshold, 0.68),
        )
        return self._pick_best_match(title, back_button, confirm_button)

    def find_special_training_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        title = self.find_special_training_title_in_screenshot(screenshot)
        if not title:
            return self.find_special_training_result_screen_in_screenshot(screenshot)

        action = self.vision.match_best(
            screenshot,
            [
                *SPECIAL_TRAINING_RESET_BUTTONS,
                *SPECIAL_TRAINING_RECOMMEND_BUTTONS,
                *SPECIAL_TRAINING_EXECUTE_BUTTONS,
            ],
            min(self.button_threshold, 0.78),
        )
        back_button = self.vision.match_best_in_region(
            screenshot,
            BACK_BUTTONS,
            min(self.button_threshold, 0.72),
            REGION_TOP_LEFT,
        )
        if action or back_button:
            return self._pick_best_match(title, action, back_button)
        return None

    def is_special_training_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_special_training_screen_in_screenshot(screenshot)

    def find_club_transfers_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        if self._has_frame_cached(screenshot, "club_transfers_screen"):
            return self._get_frame_cached(screenshot, "club_transfers_screen")  # type: ignore[return-value]
        renewal_button = self.vision.match_best_in_region(
            screenshot,
            CLUB_TRANSFERS_RENEWAL_BUTTONS,
            min(self.button_threshold, 0.80),
            REGION_BOTTOM_RIGHT,
        )
        if not renewal_button:
            return self._set_frame_cached(screenshot, "club_transfers_screen", None)  # type: ignore[return-value]

        title = self._match_ocr_title(
            screenshot,
            OCR_TEXT_CLUB_TRANSFERS,
            REGION_WIDE_TOP,
            min_score=0.35,
        ) or self._match_ocr_title(
            screenshot,
            OCR_TEXT_CLUB_TRANSFERS,
            REGION_LOGIN_TOP_LEFT,
            min_score=0.35,
        )
        if title:
            return self._set_frame_cached(screenshot, "club_transfers_screen", self._pick_best_match(title, renewal_button))  # type: ignore[return-value]
        return self._set_frame_cached(screenshot, "club_transfers_screen", None)  # type: ignore[return-value]

    def is_club_transfers_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_club_transfers_screen_in_screenshot(screenshot)

    def find_club_transfers_level_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        if self._has_frame_cached(screenshot, "club_transfers_level_screen"):
            return self._get_frame_cached(screenshot, "club_transfers_level_screen")  # type: ignore[return-value]
        title = self.find_club_transfers_level_title_in_screenshot(screenshot)
        min_button = self.vision.match_best_in_region(
            screenshot,
            ["club_transfers_min_button"],
            min(self.button_threshold, 0.72),
            REGION_CENTER_RIGHT,
        )
        confirm_button = self.vision.match_best(
            screenshot,
            EXCEPTION_CONFIRM_BUTTONS + CONFIRM_BUTTONS,
            min(self.button_threshold, 0.68),
        )
        result: MatchResult | None = None
        if title and min_button:
            result = self._pick_best_match(title, min_button, confirm_button)
        elif title and confirm_button:
            result = self._pick_best_match(title, confirm_button)
        elif min_button and confirm_button:
            result = self._pick_best_match(min_button, confirm_button)
        elif title:
            result = title
        elif min_button:
            result = min_button
        return self._set_frame_cached(screenshot, "club_transfers_level_screen", result)  # type: ignore[return-value]

    def is_club_transfers_level_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_club_transfers_level_screen_in_screenshot(screenshot)

    def find_club_transfers_level_title_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        if self._has_frame_cached(screenshot, "club_transfers_level_title"):
            return self._get_frame_cached(screenshot, "club_transfers_level_title")  # type: ignore[return-value]
        result = self._match_ocr_title(
            screenshot,
            OCR_TEXT_CLUB_TRANSFERS_LEVEL,
            REGION_TOP_CENTER,
            min_score=0.35,
        ) or self._match_ocr_title(
            screenshot,
            OCR_TEXT_CLUB_TRANSFERS_LEVEL,
            REGION_WIDE_TOP,
            min_score=0.35,
        )
        return self._set_frame_cached(screenshot, "club_transfers_level_title", result)  # type: ignore[return-value]

    def find_club_transfers_min_button_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        candidates = self.vision.match_all_in_region(
            screenshot,
            ["club_transfers_min_button"],
            threshold=max(min(self.button_threshold, 0.72), 0.70),
            region=REGION_CENTER_RIGHT,
            max_matches=8,
        )
        if not candidates:
            candidates = self.vision.match_all(
                screenshot,
                ["club_transfers_min_button"],
                threshold=max(min(self.button_threshold, 0.72), 0.70),
                max_matches=8,
            )
        if not candidates:
            return None
        # The min-difficulty choice is the left-most matched difficulty button.
        return min(candidates, key=lambda match: (match.left, -match.score))

    def click_club_transfers_min_hotspot(self, settle: float = 0.4) -> None:
        x = int(EXPECTED_CLIENT_WIDTH * CLUB_TRANSFERS_MIN_RATIO[0])
        y = int(EXPECTED_CLIENT_HEIGHT * CLUB_TRANSFERS_MIN_RATIO[1])
        logging.info("Falling back to minimum difficulty hotspot at (%s,%s)", x, y)
        self.window.click_client(x, y, settle=settle)

    def find_sp_join_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        if self._has_frame_cached(screenshot, "sp_join_screen"):
            return self._get_frame_cached(screenshot, "sp_join_screen")  # type: ignore[return-value]
        join_match = self.vision.match_best_in_region(
            screenshot,
            SP_JOIN_BUTTONS,
            min(self.button_threshold, 0.70),
            REGION_CENTER_RIGHT,
        )
        filter_match = self.vision.match_best_in_region(
            screenshot,
            SP_JOIN_FILTER_ENTRANCES,
            min(self.button_threshold, 0.70),
            REGION_CENTER_RIGHT,
        )
        title_match = self._match_ocr_title(screenshot, OCR_TEXT_SP_JOIN, REGION_WIDE_TOP, min_score=0.35)
        belong_matches = self.vision.match_all_in_region(
            screenshot,
            SP_JOIN_BELONG_MARKERS,
            threshold=SP_BELONG_THRESHOLD,
            region=REGION_CENTER,
            max_matches=20,
        )
        result: MatchResult | None = None
        if join_match and title_match:
            result = self._pick_best_match(join_match, title_match)
        elif filter_match and title_match:
            result = self._pick_best_match(filter_match, title_match)
        elif join_match and belong_matches:
            result = join_match
        elif filter_match and belong_matches:
            result = filter_match
        elif title_match and belong_matches:
            result = title_match
        elif join_match and filter_match:
            result = self._pick_best_match(join_match, filter_match)
        return self._set_frame_cached(screenshot, "sp_join_screen", result)  # type: ignore[return-value]

    def is_sp_join_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_sp_join_screen_in_screenshot(screenshot)

    def find_sponsor_selection_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        if self._has_frame_cached(screenshot, "sponsor_selection_screen"):
            return self._get_frame_cached(screenshot, "sponsor_selection_screen")  # type: ignore[return-value]
        title = self._match_ocr_title(
            screenshot,
            OCR_TEXT_SPONSOR_SELECTION,
            REGION_WIDE_TOP,
            min_score=0.35,
        ) or self._match_ocr_title(
            screenshot,
            OCR_TEXT_SPONSOR_SELECTION,
            REGION_TOP_CENTER,
            min_score=0.35,
        )
        confirm = self.vision.match_best_in_region(
            screenshot,
            FINAL_CONFIRM_BUTTONS,
            min(self.button_threshold, 0.72),
            REGION_BOTTOM_RIGHT,
        )
        result = self._pick_best_match(title, confirm) if title and confirm else title
        return self._set_frame_cached(screenshot, "sponsor_selection_screen", result)  # type: ignore[return-value]

    def is_sponsor_selection_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_sponsor_selection_screen_in_screenshot(screenshot)

    def find_final_confirm_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        if self._has_frame_cached(screenshot, "final_confirm_screen"):
            return self._get_frame_cached(screenshot, "final_confirm_screen")  # type: ignore[return-value]
        title = self._match_ocr_title(
            screenshot,
            OCR_TEXT_FINAL_CONFIRM,
            REGION_WIDE_TOP,
            min_score=0.35,
        ) or self._match_ocr_title(
            screenshot,
            OCR_TEXT_FINAL_CONFIRM,
            REGION_TOP_CENTER,
            min_score=0.35,
        )
        button = self.vision.match_best_in_region(
            screenshot,
            FINAL_CONFIRM_BUTTONS,
            min(self.button_threshold, 0.72),
            REGION_BOTTOM_RIGHT,
        )
        result = self._pick_best_match(title, button) if title and button else title
        return self._set_frame_cached(screenshot, "final_confirm_screen", result)  # type: ignore[return-value]

    def is_final_confirm_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_final_confirm_screen_in_screenshot(screenshot)

    def is_login_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_login_screen_in_screenshot(screenshot)

    def find_login_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        if self._has_frame_cached(screenshot, "login_screen"):
            return self._get_frame_cached(screenshot, "login_screen")  # type: ignore[return-value]
        result = self._match_screen_profile(
            screenshot,
            strong_probes=[
                ScreenProbe(tuple(LOGIN_SCREEN_LOGO_MARKERS), LOGIN_SCREEN_THRESHOLD, REGION_BOTTOM_LEFT),
            ],
            min_strong=1,
        )
        return self._set_frame_cached(screenshot, "login_screen", result)  # type: ignore[return-value]

    def is_game_main_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_game_main_screen_in_screenshot(screenshot)

    def find_game_main_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        if self._has_frame_cached(screenshot, "game_main_screen"):
            return self._get_frame_cached(screenshot, "game_main_screen")  # type: ignore[return-value]
        result = self._match_screen_profile(
            screenshot,
            strong_probes=[
                ScreenProbe(tuple(GAME_MAIN_MARKERS), GAME_MAIN_MARK_THRESHOLD, REGION_BOTTOM_RIGHT),
            ],
            min_strong=1,
        )
        return self._set_frame_cached(screenshot, "game_main_screen", result)  # type: ignore[return-value]

    def is_save_selection_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_save_selection_screen_in_screenshot(screenshot)

    def find_save_selection_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        if self._has_frame_cached(screenshot, "save_selection_screen"):
            return self._get_frame_cached(screenshot, "save_selection_screen")  # type: ignore[return-value]
        title = self._match_ocr_title(screenshot, OCR_TEXT_SAVE_SELECTION, REGION_TOP_CENTER, min_score=0.35)
        back_button = self.vision.match_best_in_region(
            screenshot,
            BACK_BUTTONS,
            min(self.button_threshold, 0.72),
            REGION_TOP_LEFT,
        )
        if self.awaiting_save_selection and (title or back_button):
            return self._set_frame_cached(screenshot, "save_selection_screen", title or back_button)  # type: ignore[return-value]
        if title and back_button:
            return self._set_frame_cached(screenshot, "save_selection_screen", title)  # type: ignore[return-value]
        return self._set_frame_cached(screenshot, "save_selection_screen", title)  # type: ignore[return-value]

    def find_any_known_operation(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.vision.match_best(
            screenshot,
            ACTIONABLE_OPERATION_MARKERS,
            min(self.main_threshold, self.button_threshold, self.dialog_threshold),
        )

    def detect_stage_signature(
        self,
        screenshot: np.ndarray | None = None,
        flow_hint: str | None = None,
        allow_broad_fallback: bool = True,
    ) -> str:
        if screenshot is None:
            screenshot = self.vision.capture()
        flow_hint = flow_hint or self.active_flow

        flow_checks: dict[str, list[tuple[str, object]]] = {
            "bootstrap": [
                (
                    "login_screen",
                    lambda shot: None if self.awaiting_main_after_save_selection else self.find_login_screen_in_screenshot(shot),
                ),
                (
                    "game_main",
                    lambda shot: None if self.awaiting_main_after_save_selection else self.find_game_main_screen_in_screenshot(shot),
                ),
                ("save_selection", lambda shot: self.find_save_selection_screen_in_screenshot(shot) if self.awaiting_save_selection else None),
                ("creative_mode_main", lambda shot: self.find_main_screen_in_screenshot(shot) if self.awaiting_main_after_save_selection else None),
            ],
            "main": [
                ("creative_mode_main", self.find_main_screen_in_screenshot),
                ("special_training", self.find_special_training_screen_in_screenshot),
                ("match_reward", self.find_match_reward_screen_in_screenshot),
                ("league_result", lambda shot: self._match_ocr_title(shot, OCR_TEXT_LEAGUE_RESULT, REGION_WIDE_TOP, min_score=0.35)),
                ("connecting", lambda shot: self.vision.match_best(shot, CONNECTING_MARKERS, CONNECTING_THRESHOLD)),
                (
                    "event_dialog",
                    lambda shot: self.vision.match_best_in_region(
                        shot,
                        EVENT_DIALOG_MARKERS,
                        min(self.dialog_threshold, 0.72),
                        REGION_LEFT_PANEL,
                    ),
                ),
            ],
            "new_season": [
                ("club_transfers", self.find_club_transfers_screen_in_screenshot),
                ("club_transfers_level", self.find_club_transfers_level_screen_in_screenshot),
                ("sp_join", self.find_sp_join_screen_in_screenshot),
                ("final_confirm", self.find_final_confirm_screen_in_screenshot),
                ("creative_mode_main", self.find_main_screen_in_screenshot),
            ],
            "recovery": [
                ("creative_mode_main", self.find_main_screen_in_screenshot),
                ("special_training", self.find_special_training_screen_in_screenshot),
                ("club_transfers", self.find_club_transfers_screen_in_screenshot),
                ("club_transfers_level", self.find_club_transfers_level_screen_in_screenshot),
                ("sp_join", self.find_sp_join_screen_in_screenshot),
                ("final_confirm", self.find_final_confirm_screen_in_screenshot),
                ("match_reward", self.find_match_reward_screen_in_screenshot),
                ("login_screen", self.find_login_screen_in_screenshot),
                ("save_selection", self.find_save_selection_screen_in_screenshot),
                ("game_main", self.find_game_main_screen_in_screenshot),
            ],
            "generic": [
                ("creative_mode_main", self.find_main_screen_in_screenshot),
                ("login_screen", self.find_login_screen_in_screenshot),
                ("game_main", self.find_game_main_screen_in_screenshot),
                ("save_selection", self.find_save_selection_screen_in_screenshot),
            ],
        }
        high_confidence_thresholds: dict[str, float] = {
            "creative_mode_main": 0.72,
            "special_training": 0.72,
            "club_transfers": 0.68,
            "club_transfers_level": 0.68,
            "sp_join": 0.68,
            "final_confirm": 0.68,
            "login_screen": 0.60,
            "save_selection": 0.60,
            "game_main": 0.62,
            "match_reward": 0.60,
            "league_result": 0.70,
            "connecting": 0.68,
            "event_dialog": 0.68,
        }

        ordered_checks = flow_checks.get(flow_hint, []).copy()
        if not ordered_checks and self.last_stage_signature in {"initializing", "restarted", "login_screen", "game_main", "save_selection"}:
            ordered_checks = flow_checks["bootstrap"].copy()
        elif not ordered_checks and self.last_stage_signature in {"creative_mode_main", "special_training", "match_reward", "league_result", "connecting", "event_dialog"}:
            ordered_checks = flow_checks["main"].copy()

        seen_stages: set[str] = set()
        best_ordered_stage = "unknown"
        best_ordered_score = -1.0
        for stage_name, detector in ordered_checks:
            if stage_name in seen_stages:
                continue
            seen_stages.add(stage_name)
            match = detector(screenshot)
            if not match:
                continue
            score = getattr(match, "score", 1.0)
            if score > best_ordered_score:
                best_ordered_stage = stage_name
                best_ordered_score = score
            if score >= high_confidence_thresholds.get(stage_name, 0.72):
                return stage_name
            if stage_name == self.last_stage_signature and score >= max(0.55, high_confidence_thresholds.get(stage_name, 0.72) - 0.10):
                return stage_name

        if best_ordered_stage != "unknown":
            return best_ordered_stage

        if not allow_broad_fallback:
            return "unknown"

        broad_checks = [
            ("club_transfers", self.find_club_transfers_screen_in_screenshot),
            ("club_transfers_level", self.find_club_transfers_level_screen_in_screenshot),
            ("sp_join", self.find_sp_join_screen_in_screenshot),
            ("final_confirm", self.find_final_confirm_screen_in_screenshot),
            ("login_screen", self.find_login_screen_in_screenshot),
            ("save_selection", self.find_save_selection_screen_in_screenshot),
            ("game_main", self.find_game_main_screen_in_screenshot),
            ("creative_mode_main", self.find_main_screen_in_screenshot),
            ("special_training", self.find_special_training_screen_in_screenshot),
            ("match_reward", self.find_match_reward_screen_in_screenshot),
        ]
        best_broad_stage = "unknown"
        best_broad_score = -1.0
        for stage_name, detector in broad_checks:
            if stage_name in seen_stages:
                continue
            seen_stages.add(stage_name)
            match = detector(screenshot)
            if not match:
                continue
            score = getattr(match, "score", 1.0)
            if score > best_broad_score:
                best_broad_stage = stage_name
                best_broad_score = score
            if score >= high_confidence_thresholds.get(stage_name, 0.72):
                return stage_name

        if best_broad_stage != "unknown":
            return best_broad_stage

        if self._match_ocr_title(screenshot, OCR_TEXT_LEAGUE_RESULT, REGION_WIDE_TOP, min_score=0.35):
            return "league_result"
        if self.vision.match_best(screenshot, CONNECTING_MARKERS, threshold=CONNECTING_THRESHOLD):
            return "connecting"
        if self.vision.match_best_in_region(
            screenshot,
            EVENT_DIALOG_MARKERS,
            threshold=min(self.dialog_threshold, 0.72),
            region=REGION_LEFT_PANEL,
        ):
            return "event_dialog"
        if self.vision.match_best_in_region(
            screenshot,
            BACK_BUTTONS,
            threshold=min(self.button_threshold, 0.72),
            region=REGION_TOP_LEFT,
        ):
            return "back_only"
        return "unknown"

    def update_runtime_stage(self, force: bool = False) -> str:
        now = time.time()
        cached_stage = self.last_stage_signature
        if not force and cached_stage != "unknown":
            if now - self.last_stage_probe_time < STAGE_SCAN_BASE_INTERVAL_SECONDS:
                return cached_stage

        screenshot = self.vision.capture()
        stage = self.detect_stage_signature(screenshot, flow_hint=self.active_flow, allow_broad_fallback=False)
        self.last_stage_probe_time = now

        if (
            stage == "unknown"
            and not force
            and cached_stage != "unknown"
            and now - self.last_stage_change_time < STAGE_STICKY_SECONDS
        ):
            return cached_stage

        if stage == "unknown":
            allow_full_scan = self.active_flow in {"generic", "recovery"}
            if allow_full_scan and (force or self.active_flow == "recovery" or now - self.last_full_stage_scan_time >= FULL_STAGE_SCAN_INTERVAL_SECONDS):
                stage = self.detect_stage_signature(screenshot, flow_hint=self.active_flow, allow_broad_fallback=True)
                self.last_full_stage_scan_time = now
            elif cached_stage == "unknown" and now - self.last_stage_probe_time < STAGE_SCAN_UNKNOWN_INTERVAL_SECONDS:
                return cached_stage

        now = time.time()
        if stage != self.last_stage_signature:
            logging.info("Stage changed: %s -> %s", self.last_stage_signature, stage)
            self.last_stage_signature = stage
            self.last_stage_change_time = now
        return stage

    def _build_visual_stall_signature(self, screenshot: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        thumb = cv2.resize(gray, (64, 36), interpolation=cv2.INTER_AREA)
        return cv2.GaussianBlur(thumb, (3, 3), 0)

    def check_visual_stall(self) -> bool:
        now = time.time()
        if now - self.last_visual_probe_time < VISUAL_STALL_CHECK_INTERVAL_SECONDS:
            return True

        try:
            screenshot = self.vision.capture()
        except Exception as exc:
            logging.debug("Visual stall capture failed: %s", exc)
            self.last_visual_probe_time = now
            return True

        signature = self._build_visual_stall_signature(screenshot)
        self.last_visual_probe_time = now
        if self.last_visual_signature is None:
            self.last_visual_signature = signature
            self.last_visual_change_time = now
            return True

        diff = float(np.mean(cv2.absdiff(signature, self.last_visual_signature)))
        self.last_visual_signature = signature
        if diff > VISUAL_STALL_DIFF_THRESHOLD:
            self.last_visual_change_time = now
            logging.debug("Visual stall monitor detected frame change (diff=%.2f)", diff)
            return True

        frozen_seconds = now - self.last_visual_change_time
        logging.debug("Visual stall monitor saw no meaningful frame change (diff=%.2f, frozen_for=%.0fs)", diff, frozen_seconds)
        if frozen_seconds >= VISUAL_STALL_TIMEOUT_SECONDS:
            self.vision.save_debug_screenshot("visual_stall_restart")
            self.request_restart(f"screen unchanged for {frozen_seconds:.0f}s")
            return False
        return True

    def check_runtime_health(self) -> bool:
        if self.restart_requested:
            return False

        if not self.window.is_process_running():
            self.request_restart("game process not found")
            return False

        try:
            rect = self.window.client_rect_screen()
            if not self.is_expected_client_size(rect["width"], rect["height"]):
                self.request_restart(
                    f"unexpected resolution {rect['width']}x{rect['height']} (expected {EXPECTED_CLIENT_WIDTH}x{EXPECTED_CLIENT_HEIGHT})"
                )
                return False
        except Exception as exc:
            logging.debug("Resolution check failed during health check: %s", exc)

        if not self.check_visual_stall():
            return False

        try:
            stage = self.update_runtime_stage()
        except Exception as exc:
            logging.debug("Stage detection failed during health check: %s", exc)
            return True

        now = time.time()
        stage_stuck_seconds = now - self.last_stage_change_time
        can_restart_for_stage_stuck = (
            self.active_flow in STAGE_STUCK_RESTART_FLOWS
            and stage in STAGE_STUCK_RESTART_STAGES
        )
        if can_restart_for_stage_stuck and stage_stuck_seconds >= SCREEN_STUCK_TIMEOUT_SECONDS:
            self.request_restart(f"stage '{stage}' stuck for {stage_stuck_seconds:.0f}s")
            return False

        if self.last_advance_schedule_click_time > 0:
            no_schedule_seconds = now - self.last_advance_schedule_click_time
        else:
            no_schedule_seconds = 0.0
        if no_schedule_seconds >= NO_SCHEDULE_TIMEOUT_SECONDS:
            self.request_restart(f"no advance schedule click for {no_schedule_seconds:.0f}s")
            return False

        return True

    def check_runtime_process_only(self) -> bool:
        if self.restart_requested:
            return False
        if not self.window.is_process_running():
            self.request_restart("game process not found")
            return False
        try:
            rect = self.window.client_rect_screen()
            if not self.is_expected_client_size(rect["width"], rect["height"]):
                self.request_restart(
                    f"unexpected resolution {rect['width']}x{rect['height']} (expected {EXPECTED_CLIENT_WIDTH}x{EXPECTED_CLIENT_HEIGHT})"
                )
                return False
        except Exception as exc:
            logging.debug("Resolution check failed during process-only health check: %s", exc)
        return True

    def is_expected_client_size(self, width: int, height: int) -> bool:
        return (
            abs(width - EXPECTED_CLIENT_WIDTH) <= CLIENT_SIZE_TOLERANCE_PIXELS
            and abs(height - EXPECTED_CLIENT_HEIGHT) <= CLIENT_SIZE_TOLERANCE_PIXELS
        )

    def detect_new_season_step_in_screenshot(self, screenshot: np.ndarray) -> str | None:
        if self._has_frame_cached(screenshot, "new_season_step"):
            return self._get_frame_cached(screenshot, "new_season_step")  # type: ignore[return-value]
        level_title = self.find_club_transfers_level_title_in_screenshot(screenshot)
        level_min_button = self.vision.match_best_in_region(
            screenshot,
            ["club_transfers_min_button"],
            min(self.button_threshold, 0.72),
            REGION_CENTER_RIGHT,
        )
        level_confirm = self.vision.match_best(
            screenshot,
            EXCEPTION_CONFIRM_BUTTONS + CONFIRM_BUTTONS,
            min(self.button_threshold, 0.68),
        )
        if level_title or (level_min_button and level_confirm):
            return self._set_frame_cached(screenshot, "new_season_step", "club_transfers_level")  # type: ignore[return-value]
        if self.vision.match_best_in_region(
            screenshot,
            CLUB_TRANSFERS_RENEWAL_BUTTONS,
            min(self.button_threshold, 0.80),
            REGION_BOTTOM_RIGHT,
        ):
            return self._set_frame_cached(screenshot, "new_season_step", "club_transfers")  # type: ignore[return-value]
        if self.find_sponsor_selection_screen_in_screenshot(screenshot):
            return self._set_frame_cached(screenshot, "new_season_step", "sponsor_selection")  # type: ignore[return-value]
        if self.find_sp_join_screen_in_screenshot(screenshot):
            return self._set_frame_cached(screenshot, "new_season_step", "sp_join")  # type: ignore[return-value]
        if self.find_final_confirm_screen_in_screenshot(screenshot):
            return self._set_frame_cached(screenshot, "new_season_step", "final_confirm")  # type: ignore[return-value]
        return self._set_frame_cached(screenshot, "new_season_step", None)  # type: ignore[return-value]

    def is_new_season_context_active_in_screenshot(self, screenshot: np.ndarray) -> bool:
        if self.detect_new_season_step_in_screenshot(screenshot):
            return True
        if self.active_flow == "new_season" and time.time() - self.last_new_season_activity_time <= 60.0:
            return True
        return False

    def _secondary_button_exclusion_reason(self, screenshot: np.ndarray, button_name: str) -> str | None:
        if self.awaiting_save_selection and self.find_save_selection_screen_in_screenshot(screenshot):
            return "save selection screen is active"

        if self.is_new_season_context_active_in_screenshot(screenshot):
            if button_name in BACK_BUTTONS:
                return "new-season flow owns ordered actions"
            if button_name in [*CONFIRM_BUTTONS, *CONTINUE_BUTTONS, *SKIP_BUTTONS]:
                return "new-season flow owns ordered actions"

        if self.find_special_training_screen_in_screenshot(screenshot):
            return "special training flow owns ordered actions"

        if self.find_match_reward_screen_in_screenshot(screenshot) and button_name in [*CONFIRM_BUTTONS, *CONTINUE_BUTTONS]:
            return "match reward flow must switch speed before confirming"

        if self.find_club_transfers_level_screen_in_screenshot(screenshot) and button_name in [*CONFIRM_BUTTONS, *EXCEPTION_CONFIRM_BUTTONS]:
            return "club-transfers level flow must choose min before confirming"

        if self.find_sp_join_screen_in_screenshot(screenshot):
            return "SP join flow owns ordered actions"

        if button_name in BACK_BUTTONS:
            if self.find_save_selection_screen_in_screenshot(screenshot):
                return "save selection forbids back"
            if self.find_special_training_screen_in_screenshot(screenshot):
                return "special training returns only after actions"
            if self.find_main_screen_in_screenshot(screenshot) or self.should_trust_main_screen(screenshot):
                return "main screen back button should not preempt normal flow"
            if self.active_flow not in {"recovery"} and self.last_stage_signature != "back_only":
                return "back button is only treated as generic priority during recovery/back-only states"

        return None

    def _find_allowed_light_common_button(self, screenshot: np.ndarray, priority_threshold: float) -> MatchResult | None:
        candidates = self.vision.match_all(screenshot, LIGHT_COMMON_BUTTONS + BACK_BUTTONS, priority_threshold, max_matches=12)
        for candidate in candidates:
            reason = self._secondary_button_exclusion_reason(screenshot, candidate.name)
            if reason:
                logging.debug("Skipping secondary common button %s because %s", candidate.name, reason)
                continue
            return candidate
        return None

    def _handle_global_priority_buttons_from_screenshot(self, screenshot: np.ndarray, priority_threshold: float) -> bool:
        common_button = self._find_allowed_light_common_button(screenshot, priority_threshold)
        if common_button:
            logging.info(
                "Light common button detected: %s (score=%.3f)",
                common_button.name,
                common_button.score,
            )
            self.click_match(common_button, settle=0.2)
            return True

        if self._handle_emergency_buttons_from_screenshot(screenshot, priority_threshold):
            return True
        return False

    def _handle_exception_layer_from_screenshot(self, screenshot: np.ndarray, priority_threshold: float) -> bool:
        confirm_button = self.vision.match_best(screenshot, EXCEPTION_CONFIRM_BUTTONS, priority_threshold)
        if confirm_button:
            level_screen = self._match_ocr_title(
                screenshot,
                OCR_TEXT_CLUB_TRANSFERS_LEVEL,
                REGION_WIDE_TOP,
                min_score=0.35,
            )
            min_button = self.vision.match_best(
                screenshot,
                ["club_transfers_min_button"],
                max(min(self.button_threshold, 0.72), 0.82),
            )
            if level_screen and min_button:
                logging.info(
                    "Exception layer detected club-transfers level confirm %s, selecting minimum difficulty first",
                    confirm_button.name,
                )
                self.click_match(min_button, settle=0.3)
                screenshot = self.vision.capture()
                refreshed_confirm = self.vision.match_best(screenshot, EXCEPTION_CONFIRM_BUTTONS, priority_threshold)
                if not refreshed_confirm:
                    logging.warning("Exception-layer confirm button disappeared after selecting minimum difficulty")
                    return True
                confirm_button = refreshed_confirm

            logging.info("Exception-layer confirm button detected: %s (score=%.3f)", confirm_button.name, confirm_button.score)
            self.click_match(confirm_button, settle=0.2)
            return True

        new_season_step = self.detect_new_season_step_in_screenshot(screenshot)
        if new_season_step:
            if new_season_step == "sp_join":
                logging.info("Exception layer detected new-season step sp_join, dispatching immediately to staged flow handling")
                self.set_active_flow("new_season")
                return self.new_season_flow.run(screenshot, fast_dispatch=True)
            logging.info("Exception layer detected new-season step %s, deferring to staged flow handling", new_season_step)
            return False

        # Avoid story/event-choice false positives on obvious main screens.
        if self.find_main_screen_in_screenshot(screenshot) or self.should_trust_main_screen(screenshot):
            return False

        event_choice = self.find_event_choice_in_screenshot(screenshot)
        if event_choice:
            logging.info(
                "Exception layer detected event choice via %s (score=%.3f), selecting the first option",
                event_choice.name,
                event_choice.score,
            )
            self.click_event_log_first_option(settle=0.15)
            self.rapidly_advance_event_story(attempts=4, settle=0.08)
            return True

        return False

    def _handle_emergency_buttons_from_screenshot(self, screenshot: np.ndarray, priority_threshold: float) -> bool:
        if self.is_new_season_context_active_in_screenshot(screenshot):
            logging.info("Deferring emergency buttons because new-season flow owns the current screen")
            return False

        level_title = self.find_club_transfers_level_title_in_screenshot(screenshot)
        level_min_button = self.vision.match_best_in_region(
            screenshot,
            ["club_transfers_min_button"],
            min(self.button_threshold, 0.72),
            REGION_CENTER_RIGHT,
        )
        level_confirm = self.vision.match_best(
            screenshot,
            EXCEPTION_CONFIRM_BUTTONS + CONFIRM_BUTTONS,
            min(self.button_threshold, 0.68),
        )
        if level_title or level_min_button or level_confirm:
            if level_title or (level_min_button and level_confirm):
                logging.info(
                    "Deferring emergency buttons because club-transfers level page signals are present and normal min->confirm handling should take precedence"
                )
                return False

        emergency_button = self.vision.match_best(screenshot, EMERGENCY_PRIORITY_BUTTONS, priority_threshold)
        if not emergency_button:
            return False
        logging.info(
            "Emergency priority button detected and handled immediately: %s (score=%.3f)",
            emergency_button.name,
            emergency_button.score,
        )
        self.click_match(emergency_button, settle=0.2)
        return True

    def handle_emergency_buttons(self, max_clicks: int = 2, initial_screenshot: np.ndarray | None = None) -> bool:
        handled_any = False
        priority_threshold = min(self.button_threshold, 0.72)
        screenshot = initial_screenshot
        for attempt in range(max_clicks):
            self.window.move_cursor_client(x_ratio=0.08, y_ratio=0.08)
            if screenshot is None or attempt > 0:
                screenshot = self.vision.capture()
            if not self._handle_emergency_buttons_from_screenshot(screenshot, priority_threshold):
                break
            handled_any = True
            screenshot = None
        return handled_any

    def handle_global_priority_buttons(self, max_clicks: int = 4, initial_screenshot: np.ndarray | None = None) -> bool:
        handled_any = False
        priority_threshold = min(self.button_threshold, 0.72)
        screenshot = initial_screenshot
        for attempt in range(max_clicks):
            self.window.move_cursor_client(x_ratio=0.08, y_ratio=0.08)
            if screenshot is None or attempt > 0:
                screenshot = self.vision.capture()
            if not self._handle_global_priority_buttons_from_screenshot(screenshot, priority_threshold):
                break
            handled_any = True
            screenshot = None
        return handled_any

    def handle_exception_layer(self, max_clicks: int = 2, initial_screenshot: np.ndarray | None = None) -> bool:
        handled_any = False
        priority_threshold = min(self.button_threshold, 0.72)
        screenshot = initial_screenshot
        for attempt in range(max_clicks):
            self.window.move_cursor_client(x_ratio=0.08, y_ratio=0.08)
            if screenshot is None or attempt > 0:
                screenshot = self.vision.capture()
            if not self._handle_exception_layer_from_screenshot(screenshot, priority_threshold):
                break
            handled_any = True
            screenshot = None
        return handled_any

    def handle_common_layers_once(self, screenshot: np.ndarray | None = None, max_clicks: int = 1) -> bool:
        handled_any = False
        priority_threshold = min(self.button_threshold, 0.72)
        current_screenshot = screenshot
        for attempt in range(max_clicks):
            self.window.move_cursor_client(x_ratio=0.08, y_ratio=0.08)
            if current_screenshot is None or attempt > 0:
                current_screenshot = self.vision.capture()
            if self._handle_emergency_buttons_from_screenshot(current_screenshot, priority_threshold):
                handled_any = True
                current_screenshot = None
                continue
            if self._handle_exception_layer_from_screenshot(current_screenshot, priority_threshold):
                handled_any = True
                current_screenshot = None
                continue
            if self._handle_global_priority_buttons_from_screenshot(current_screenshot, priority_threshold):
                handled_any = True
                current_screenshot = None
                continue
            break
        return handled_any

    def has_priority_button_visible(self) -> bool:
        self.window.move_cursor_client(x_ratio=0.08, y_ratio=0.08)
        screenshot = self.vision.capture()
        priority_threshold = min(self.button_threshold, 0.72)
        return self.vision.match_best(screenshot, PRIORITY_BUTTONS, priority_threshold) is not None

    def fallback_click_when_no_operation_found(self) -> bool:
        match = self.find_any_known_operation()
        if match:
            logging.info("Known operation area still exists: %s (score=%.3f)", match.name, match.score)
            return False
        logging.warning("No known operation area found, performing one fallback click at bottom-right")
        self.window.click_client_bottom_right(settle=1.0)
        return True

    def handle_generic_confirm_fallback(self, min_interval: float = 1.0) -> bool:
        if time.time() - self.last_generic_confirm_click_time < min_interval:
            return False

        if self.is_main_screen():
            return False
        if self.is_special_training_screen():
            return False
        if self.is_club_transfers_screen():
            return False
        if self.is_club_transfers_level_screen():
            return False
        if self.is_sp_join_screen():
            return False
        if self.is_final_confirm_screen():
            return False
        if self.is_login_screen() or self.is_game_main_screen() or self.is_save_selection_screen():
            return False

        logging.info("No special flow matched; clicking bottom-right as a generic confirm fallback")
        self.window.click_client_bottom_right(settle=0.25)
        self.last_generic_confirm_click_time = time.time()
        return True

    def click_match(self, match: MatchResult, settle: float = 0.8) -> None:
        x, y = match.center
        self.window.click_client(x, y, settle=settle)

    def click_skip_hotspot(self, settle: float = 0.1) -> None:
        logging.info("Clicking skip hotspot near the top-right corner")
        self.window.click_client(
            int(EXPECTED_CLIENT_WIDTH * 0.91),
            int(EXPECTED_CLIENT_HEIGHT * 0.08),
            settle=settle,
        )

    def click_event_log_first_option(self, settle: float = 0.2) -> None:
        logging.info("Clicking the first option on the event-choice screen")
        self.window.click_client(
            int(EXPECTED_CLIENT_WIDTH * 0.34),
            int(EXPECTED_CLIENT_HEIGHT * 0.27),
            settle=settle,
        )

    def click_story_progress_hotspot(self, settle: float = 0.12) -> None:
        x = int(EXPECTED_CLIENT_WIDTH * STORY_PROGRESS_HOTSPOT_RATIO[0])
        y = int(EXPECTED_CLIENT_HEIGHT * STORY_PROGRESS_HOTSPOT_RATIO[1])
        logging.info("Clicking story progress hotspot at (%s, %s)", x, y)
        self.window.click_client(x, y, settle=settle)

    def rapidly_advance_event_story(self, attempts: int = 5, settle: float = 0.1) -> bool:
        for rapid_click in range(1, attempts + 1):
            if self.is_main_screen():
                logging.info("Event flow finished and main screen returned")
                return True
            screenshot = self.vision.capture()
            if self._handle_fast_story_transition_from_screenshot(screenshot):
                return True
            logging.info("Rapid story left click %s/%s", rapid_click, attempts)
            self.window.click_client_center(settle=settle)
            screenshot = self.vision.capture()
            if self._handle_fast_story_transition_from_screenshot(screenshot):
                return True
        if self.is_main_screen():
            logging.info("Event flow finished and main screen returned")
            return True
        return False

    def note_recovery_story_presence(self, screenshot: np.ndarray | None = None) -> bool:
        screenshot = screenshot if screenshot is not None else self.vision.capture()
        now = time.time()
        if now - self.last_recovery_story_seen_time > RECOVERY_STORY_STREAK_RESET_SECONDS:
            self.recovery_story_streak = 0

        log_match = self.vision.match_best_in_region(
            screenshot,
            ["log", "log2"],
            min(self.button_threshold, 0.72),
            REGION_TOP_RIGHT,
        )
        skip_match = self.vision.match_best(
            screenshot,
            SKIP_BUTTONS,
            min(self.button_threshold, SKIP_THRESHOLD),
        )
        event_choice = self.find_event_choice_in_screenshot(screenshot)
        story_visible = bool(log_match or skip_match or event_choice)
        if story_visible:
            self.recovery_story_streak += 1
            self.last_recovery_story_seen_time = now
        elif now - self.last_recovery_story_seen_time > RECOVERY_STORY_STREAK_RESET_SECONDS:
            self.recovery_story_streak = 0
        return story_visible

    def clear_recovery_story_presence(self) -> None:
        self.recovery_story_streak = 0
        self.last_recovery_story_seen_time = 0.0

    def handle_recovery_story_stall(self, screenshot: np.ndarray | None = None) -> bool:
        screenshot = screenshot if screenshot is not None else self.vision.capture()
        story_visible = self.note_recovery_story_presence(screenshot)
        if not story_visible:
            return False

        if self.recovery_story_streak < RECOVERY_STORY_STREAK_THRESHOLD:
            return False

        logging.info(
            "Recovery detected persistent story/skip chain (streak=%s), prioritizing aggressive story cleanup",
            self.recovery_story_streak,
        )
        handled = False
        if self.handle_story_dialog_fast(screenshot=screenshot, attempts=6):
            handled = True
        if self.handle_post_schedule_events(max_clicks=10):
            handled = True
        if not handled:
            self.click_skip_hotspot(settle=0.08)
            handled = True
        if self.rapidly_advance_event_story(attempts=8, settle=0.08):
            self.clear_recovery_story_presence()
            return True
        return handled

    def handle_story_dialog_fast(self, screenshot: np.ndarray | None = None, attempts: int = 4) -> bool:
        screenshot = screenshot if screenshot is not None else self.vision.capture()
        log_match = self.vision.match_best_in_region(
            screenshot,
            ["log", "log2"],
            min(self.button_threshold, 0.72),
            REGION_TOP_RIGHT,
        )
        if not log_match:
            return False

        logging.info("Story dialog detected via %s (score=%.3f)", log_match.name, log_match.score)

        skip_button = self.vision.match_best(
            screenshot,
            SKIP_BUTTONS,
            min(self.button_threshold, SKIP_THRESHOLD),
        )
        if skip_button:
            logging.info("Story dialog skip detected: %s (score=%.3f)", skip_button.name, skip_button.score)
            self.click_match(skip_button, settle=0.08)
            screenshot = self.vision.capture()
            if self._handle_fast_story_transition_from_screenshot(screenshot):
                return True

        for attempt in range(1, attempts + 1):
            screenshot = self.vision.capture()
            if self._handle_fast_story_transition_from_screenshot(screenshot):
                return True

            still_story = self.vision.match_best_in_region(
                screenshot,
                ["log", "log2"],
                min(self.button_threshold, 0.72),
                REGION_TOP_RIGHT,
            )
            if not still_story:
                return True

            logging.info("Story dialog progress click %s/%s", attempt, attempts)
            self.click_story_progress_hotspot(settle=0.08)

        return True

    def _handle_fast_story_transition_from_screenshot(self, screenshot: np.ndarray) -> bool:
        if self.is_main_screen_returned_quickly(screenshot) or self.should_trust_main_screen(screenshot):
            logging.info("Event flow finished and creative mode main screen is already visible")
            return True

        confirm_button = self.vision.match_best(screenshot, CONFIRM_BUTTONS, min(self.button_threshold, 0.72))
        if confirm_button:
            logging.info(
                "Fast story transition matched confirm button: %s (score=%.3f)",
                confirm_button.name,
                confirm_button.score,
            )
            self.click_match(confirm_button, settle=0.15)
            return True

        final_confirm = self.vision.match_best(screenshot, EXCEPTION_CONFIRM_BUTTONS, min(self.button_threshold, 0.72))
        if final_confirm:
            logging.info(
                "Fast story transition matched priority-2 button: %s (score=%.3f)",
                final_confirm.name,
                final_confirm.score,
            )
            self.click_match(final_confirm, settle=0.15)
            return True

        continue_button = self.vision.match_best(screenshot, CONTINUE_BUTTONS, min(self.button_threshold, 0.72))
        if continue_button:
            logging.info(
                "Fast story transition matched follow-up button: %s (score=%.3f)",
                continue_button.name,
                continue_button.score,
            )
            self.click_match(continue_button, settle=0.15)
            return True

        return False

    def click_main_screen_special_training_hotspot(self, settle: float = 0.5) -> None:
        x = int(EXPECTED_CLIENT_WIDTH * MAIN_SCREEN_SPECIAL_TRAINING_RATIO[0])
        y = int(EXPECTED_CLIENT_HEIGHT * MAIN_SCREEN_SPECIAL_TRAINING_RATIO[1])
        logging.info("Clicking main-screen special training hotspot at (%s, %s)", x, y)
        self.window.click_client(x, y, settle=settle)

    def click_special_training_back_hotspot(self, settle: float = 0.35) -> None:
        x = max(1, int(EXPECTED_CLIENT_WIDTH * 0.036))
        y = max(1, int(EXPECTED_CLIENT_HEIGHT * 0.050))
        logging.info("Clicking special-training back hotspot at (%s, %s)", x, y)
        self.window.click_client(x, y, settle=settle)

    def click_main_screen_schedule_hotspot(self, variant: int = 0, settle: float = 0.5) -> None:
        x_ratio, y_ratio = MAIN_SCREEN_SCHEDULE_RATIOS[min(max(variant, 0), len(MAIN_SCREEN_SCHEDULE_RATIOS) - 1)]
        x = int(EXPECTED_CLIENT_WIDTH * x_ratio)
        y = int(EXPECTED_CLIENT_HEIGHT * y_ratio)
        logging.info("Clicking main-screen schedule-card hotspot #%s at (%s, %s)", variant + 1, x, y)
        self.window.click_client(x, y, settle=settle)

    def dismiss_main_screen_overlay_if_present(self) -> bool:
        screenshot = self.vision.capture()
        popup = self.vision.match_best(
            screenshot,
            SPEED_POPUP_MARKERS,
            min(self.dialog_threshold, 0.68),
        )
        if popup:
            logging.info("Speed popup is still visible, dismissing it with an outside click")
            self.window.click_client(
                int(EXPECTED_CLIENT_WIDTH * 0.78),
                int(EXPECTED_CLIENT_HEIGHT * 0.18),
                settle=0.15,
            )
            return True

        confirm = self.vision.match_best(
            screenshot,
            CONFIRM_BUTTONS,
            min(self.button_threshold, 0.72),
        )
        if confirm:
            logging.info("Dismissing overlay via confirm button %s (score=%.3f)", confirm.name, confirm.score)
            self.click_match(confirm, settle=0.2)
            return True

        if self.find_main_screen_in_screenshot(screenshot) or self.find_match_reward_screen_in_screenshot(screenshot):
            logging.info("No popup marker detected after speed click, nudging an outside click to clear any overlay")
            self.window.click_client(
                int(EXPECTED_CLIENT_WIDTH * 0.78),
                int(EXPECTED_CLIENT_HEIGHT * 0.18),
                settle=0.15,
            )
            return True

        return False

    def find_special_training_entry_on_main_screen(self, screenshot: np.ndarray) -> MatchResult | None:
        return self.vision.match_best_in_region(
            screenshot,
            SPECIAL_TRAINING_ENTRY_BUTTONS,
            min(self.button_threshold, 0.72),
            REGION_BOTTOM_HALF,
        )

    def is_confirmed_main_screen(self, screenshot: np.ndarray | None = None) -> bool:
        screenshot = screenshot if screenshot is not None else self.vision.capture()
        if self.should_trust_main_screen(screenshot):
            return True
        if self.find_special_training_screen_in_screenshot(screenshot):
            return False
        if self.find_match_reward_screen_in_screenshot(screenshot):
            return False
        if self.find_club_transfers_screen_in_screenshot(screenshot):
            return False
        if self.find_club_transfers_level_screen_in_screenshot(screenshot):
            return False
        if self.find_sp_join_screen_in_screenshot(screenshot):
            return False
        if self.find_final_confirm_screen_in_screenshot(screenshot):
            return False
        if self.find_login_screen_in_screenshot(screenshot):
            return False
        if self.find_game_main_screen_in_screenshot(screenshot):
            return False
        if self.find_save_selection_screen_in_screenshot(screenshot):
            return False
        return self.find_main_screen_in_screenshot(screenshot) is not None

    def has_returned_to_main_from_special_training(self, screenshot: np.ndarray | None = None) -> bool:
        screenshot = screenshot if screenshot is not None else self.vision.capture()
        if self.find_special_training_screen_in_screenshot(screenshot):
            return False

        main_screen = self.find_main_screen_in_screenshot(screenshot)
        if not main_screen:
            return False

        speed_marker = self.vision.match_best_in_region(
            screenshot,
            SPEED_SWITCH_TRIGGER_BUTTONS + SPEED_ALREADY_THREE_MARKERS,
            min(self.button_threshold, 0.68),
            REGION_TOP_RIGHT,
        )
        extra_marker = self.vision.match_best_in_region(
            screenshot,
            MAIN_SCREEN_EXTRA_MARKERS,
            min(self.button_threshold, 0.78),
            REGION_BOTTOM_HALF,
        )
        return speed_marker is not None or extra_marker is not None

    def find_event_choice_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        choice = self.vision.match_best(
            screenshot,
            EVENT_LOG_CHOOSE_MARKERS,
            max(min(self.dialog_threshold, 0.62), 0.62),
        )
        if not choice:
            return None

        dialog = self.vision.match_best_in_region(
            screenshot,
            EVENT_DIALOG_MARKERS,
            max(min(self.dialog_threshold, 0.68), 0.68),
            REGION_LEFT_PANEL,
        )
        skip = self.vision.match_best(
            screenshot,
            SKIP_BUTTONS,
            max(min(self.button_threshold, SKIP_THRESHOLD), 0.72),
        )

        if dialog or skip:
            return self._pick_best_match(choice, dialog, skip)

        logging.debug(
            "Ignoring event-choice match %s (score=%.3f) because no event-dialog context was found",
            choice.name,
            choice.score,
        )
        return None

    def click_named_button(self, names: list[str], timeout: float = 5.0, settle: float = 0.8) -> MatchResult | None:
        match = self.vision.wait_for_any(names, self.button_threshold, timeout)
        if not match:
            return None
        logging.debug("Matched button %s with score %.3f", match.name, match.score)
        self.click_match(match, settle=settle)
        return match

    def click_named_button_in_region(
        self,
        names: list[str],
        threshold: float,
        region: ScreenRegion,
        timeout: float = 3.0,
        interval: float = 0.2,
        settle: float = 0.8,
    ) -> MatchResult | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            screenshot = self.vision.capture()
            match = self.vision.match_best_in_region(screenshot, names, threshold, region)
            if match:
                logging.debug("Matched regional button %s with score %.3f", match.name, match.score)
                self.click_match(match, settle=settle)
                return match
            time.sleep(interval)
        return None

    def find_advance_schedule_button_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        height, width = screenshot.shape[:2]
        width_scale = width / EXPECTED_CLIENT_WIDTH
        height_scale = height / EXPECTED_CLIENT_HEIGHT
        base_scale = min(width_scale, height_scale)
        scales = [
            round(base_scale, 3),
            round(base_scale * 0.96, 3),
            round(base_scale * 1.04, 3),
            1.0,
        ]
        match = self.vision.match_best_multiscale_in_region(
            screenshot,
            MAIN_SCREEN_BUTTONS,
            min(self.main_threshold, 0.45),
            REGION_SCHEDULE_BUTTON,
            scales=scales,
        )
        if match:
            logging.info("Advance schedule matched in dedicated ROI via %s (score=%.3f)", match.name, match.score)
            return match
        fallback = self.vision.match_best_multiscale_in_region(
            screenshot,
            MAIN_SCREEN_BUTTONS,
            min(self.main_threshold, 0.42),
            REGION_BOTTOM_RIGHT,
            scales=scales,
        )
        if fallback:
            logging.info("Advance schedule matched in bottom-right fallback via %s (score=%.3f)", fallback.name, fallback.score)
        return fallback

    def wait_for_any_in_region(
        self,
        names: list[str],
        threshold: float,
        region: ScreenRegion,
        timeout: float = 1.0,
        interval: float = 0.15,
    ) -> MatchResult | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            screenshot = self.vision.capture()
            match = self.vision.match_best_in_region(screenshot, names, threshold, region)
            if match:
                return match
            time.sleep(interval)
        return None

    def wait_for_ocr_text_in_region(
        self,
        texts: Iterable[str],
        region: ScreenRegion,
        timeout: float = 1.0,
        interval: float = 0.15,
        min_score: float = 0.35,
    ) -> MatchResult | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            screenshot = self.vision.capture()
            match = self._match_ocr_title(screenshot, texts, region, min_score=min_score)
            if match:
                return match
            time.sleep(interval)
        return None

    def click_special_training_action_fast(
        self,
        names: list[str],
        region: ScreenRegion = SPECIAL_TRAINING_ACTION_REGION,
        timeout: float = 0.8,
        settle: float = 0.35,
    ) -> MatchResult | None:
        match = self.click_named_button_in_region(
            names,
            min(self.button_threshold, 0.72),
            region,
            timeout=timeout,
            interval=0.12,
            settle=settle,
        )
        if match:
            return match
        return self.click_named_button(names, timeout=1.0, settle=settle)

    def detect_speed_state(
        self,
        screenshot: np.ndarray | None = None,
        prefer_reward_context: bool = False,
        speed_one_threshold: float = SPEED_ONE_THRESHOLD,
        speed_three_threshold: float = SPEED_THREE_CONFIRM_THRESHOLD,
    ) -> tuple[str, MatchResult | None]:
        if screenshot is None:
            screenshot = self.vision.capture()

        speed_one: MatchResult | None = None
        if prefer_reward_context:
            reward_speed_one_threshold = min(speed_one_threshold, 0.62)
            speed_one = self.vision.match_best_in_region(
                screenshot,
                MATCH_REWARD_SPEED_SWITCH_MARKERS,
                reward_speed_one_threshold,
                REGION_TOP_RIGHT,
            )

        if not speed_one:
            speed_one = self.vision.match_best(
                screenshot,
                SPEED_SWITCH_TRIGGER_BUTTONS + MATCH_REWARD_SPEED_SWITCH_MARKERS,
                speed_one_threshold,
            )

        speed_three = self.vision.match_best(screenshot, SPEED_ALREADY_THREE_MARKERS, speed_three_threshold)

        if speed_one:
            return "one", speed_one
        if speed_three:
            return "three", speed_three
        return "unknown", None

    def ensure_speed_three(
        self,
        screenshot: np.ndarray | None = None,
        prefer_reward_context: bool = False,
    ) -> bool:
        screenshot = screenshot if screenshot is not None else self.vision.capture()
        speed_state, speed_marker = self.detect_speed_state(
            screenshot,
            prefer_reward_context=prefer_reward_context,
        )
        if speed_state == "three":
            logging.info("3x speed already active via %s (score=%.3f)", speed_marker.name, speed_marker.score)
            return True

        if speed_state != "one" or not speed_marker:
            loose_speed_one_threshold = min(SPEED_ONE_THRESHOLD, 0.55 if prefer_reward_context else 0.50)
            speed_state_loose, speed_marker_loose = self.detect_speed_state(
                screenshot,
                prefer_reward_context=prefer_reward_context,
                speed_one_threshold=loose_speed_one_threshold,
                speed_three_threshold=min(SPEED_THREE_CONFIRM_THRESHOLD, 0.50),
            )
            speed_one_loose = speed_marker_loose if speed_state_loose == "one" else None
            speed_three_loose = speed_marker_loose if speed_state_loose == "three" else None
            if speed_one_loose:
                speed_marker = speed_one_loose
            if speed_one_loose:
                logging.info(
                    "Speed switch skipped: speed1-like marker %s seen but below confident threshold (score=%.3f, required=%.3f)",
                    speed_one_loose.name,
                    speed_one_loose.score,
                    SPEED_ONE_THRESHOLD,
                )
            elif speed_three_loose:
                logging.info(
                    "Speed switch skipped: speed3-like marker %s seen but below confident threshold (score=%.3f, required=%.3f)",
                    speed_three_loose.name,
                    speed_three_loose.score,
                    SPEED_THREE_CONFIRM_THRESHOLD,
                )
            else:
                logging.info("Speed switch skipped: no speed1/speed3 marker was confidently detected on the current screen")
            if not speed_one_loose:
                return False

        for attempt in range(1, 2):
            logging.info("Switching speed to 3x, attempt %s", attempt)
            self.click_match(speed_marker, settle=0.5)

            speed_state_after_click, _ = self.detect_speed_state(prefer_reward_context=prefer_reward_context)
            if speed_state_after_click == "three":
                logging.info("3x speed confirmed immediately after clicking the speed control")
                return True

            popup = self.vision.wait_for_any(SPEED_POPUP_MARKERS, self.dialog_threshold, timeout=1.0, interval=0.2)
            if not popup:
                self.dismiss_main_screen_overlay_if_present()
                logging.warning("Speed popup not detected after clicking 1x button")
                return False

            speed_three_choice = self.vision.wait_for_any(SPEED_THREE_BUTTONS, self.button_threshold, timeout=1.0, interval=0.2)
            if not speed_three_choice:
                logging.warning("3x speed option not found in speed popup")
                return False

            self.click_match(speed_three_choice, settle=0.6)
            popup_after = self.vision.wait_for_any(SPEED_POPUP_MARKERS, self.dialog_threshold, timeout=0.6, interval=0.2)
            if not popup_after:
                logging.info("3x speed assumed active because speed popup closed")
                return True

            speed_state_after_popup, _ = self.detect_speed_state(prefer_reward_context=prefer_reward_context)
            if speed_state_after_popup == "three":
                logging.info("3x speed confirmed")
                return True

        logging.warning("Failed to confirm 3x speed quickly, continuing")
        return False

    def find_main_screen_recovery_hint(self, screenshot: np.ndarray) -> MatchResult | None:
        main_button = self.vision.match_best_in_region(
            screenshot,
            MAIN_SCREEN_BUTTONS,
            min(self.main_threshold, 0.60),
            REGION_BOTTOM_RIGHT,
        )
        extra_marker = self.vision.match_best_in_region(
            screenshot,
            MAIN_SCREEN_EXTRA_MARKERS,
            min(self.button_threshold, 0.78),
            REGION_BOTTOM_HALF,
        )
        speed_marker = self.vision.match_best_in_region(
            screenshot,
            SPEED_SWITCH_TRIGGER_BUTTONS + SPEED_ALREADY_THREE_MARKERS,
            min(self.button_threshold, 0.66),
            REGION_TOP_RIGHT,
        )

        if main_button:
            return self._pick_best_match(main_button, extra_marker, speed_marker)
        if extra_marker and speed_marker:
            return self._pick_best_match(extra_marker, speed_marker)
        return None

    def handle_speed_one_anywhere(self) -> bool:
        screenshot = self.vision.capture()
        priority_match = self.vision.match_best(screenshot, PRIORITY_BUTTONS, min(self.button_threshold, 0.72))
        if priority_match:
            logging.debug(
                "Deferring speed switch because priority button %s is visible (score=%.3f)",
                priority_match.name,
                priority_match.score,
            )
            return False

        speed_state, speed_marker = self.detect_speed_state(screenshot)
        if speed_state == "three" and speed_marker:
            logging.debug(
                "Skipping speed switch because 3x speed is already active via %s (score=%.3f)",
                speed_marker.name,
                speed_marker.score,
            )
            return False

        if speed_state != "one" or not speed_marker:
            speed_one_loose = self.vision.match_best(
                screenshot,
                SPEED_SWITCH_TRIGGER_BUTTONS + MATCH_REWARD_SPEED_SWITCH_MARKERS,
                min(SPEED_ONE_THRESHOLD, 0.50),
            )
            speed_three_loose = self.vision.match_best(screenshot, SPEED_ALREADY_THREE_MARKERS, min(SPEED_THREE_CONFIRM_THRESHOLD, 0.50))
            if speed_one_loose:
                logging.debug(
                    "Skipping speed switch because speed1-like marker %s is below threshold (score=%.3f, required=%.3f)",
                    speed_one_loose.name,
                    speed_one_loose.score,
                    SPEED_ONE_THRESHOLD,
                )
            elif speed_three_loose:
                logging.debug(
                    "Skipping speed switch because speed3-like marker %s is below threshold (score=%.3f, required=%.3f)",
                    speed_three_loose.name,
                    speed_three_loose.score,
                    SPEED_THREE_CONFIRM_THRESHOLD,
                )
            else:
                logging.debug("Skipping speed switch because no speed marker is visible on the current screen")
            return False

        logging.info("Speed control %s indicates 3x is not active yet, switching now", speed_marker.name)
        self.ensure_speed_three()
        return True

    def handle_fast_main_screen_interrupts(self, screenshot: np.ndarray | None = None) -> bool:
        if screenshot is None:
            screenshot = self.vision.capture()
        priority_threshold = min(self.button_threshold, 0.72)

        emergency = self.vision.match_best(screenshot, EMERGENCY_PRIORITY_BUTTONS, priority_threshold)
        if emergency:
            logging.info("Fast main-screen interrupt detected: %s (score=%.3f)", emergency.name, emergency.score)
            self.click_match(emergency, settle=0.2)
            return True

        confirm = self.vision.match_best(screenshot, CONFIRM_BUTTONS, priority_threshold)
        if confirm:
            logging.info("Fast main-screen confirm detected: %s (score=%.3f)", confirm.name, confirm.score)
            self.click_match(confirm, settle=0.2)
            return True

        return False

    def is_main_screen_visible(self, screenshot: np.ndarray | None = None) -> bool:
        if screenshot is None:
            screenshot = self.vision.capture()
        return self.find_main_screen_in_screenshot(screenshot) is not None

    def should_trust_main_screen(self, screenshot: np.ndarray | None = None) -> bool:
        if self.last_stage_signature != "creative_mode_main":
            return False
        if time.time() - self.last_stage_change_time > STAGE_STICKY_SECONDS:
            return False

        if screenshot is None:
            screenshot = self.vision.capture()

        if self.find_main_screen_in_screenshot(screenshot):
            return True

        disruptive_stage = any(
            detector(screenshot)
            for detector in (
                self.find_special_training_screen_in_screenshot,
                self.find_club_transfers_screen_in_screenshot,
                self.find_club_transfers_level_screen_in_screenshot,
                self.find_sp_join_screen_in_screenshot,
                self.find_final_confirm_screen_in_screenshot,
                self.find_login_screen_in_screenshot,
                self.find_save_selection_screen_in_screenshot,
                self.find_game_main_screen_in_screenshot,
                self.find_match_reward_screen_in_screenshot,
            )
        )
        if disruptive_stage:
            return False

        return True

    def is_main_screen_returned_quickly(self, screenshot: np.ndarray | None = None) -> bool:
        if screenshot is None:
            screenshot = self.vision.capture()

        if self.find_main_screen_in_screenshot(screenshot):
            return True

        main_marker = self.vision.match_best_in_region(
            screenshot,
            MAIN_SCREEN_EXTRA_MARKERS,
            min(self.button_threshold, 0.72),
            REGION_BOTTOM_HALF,
        )
        speed_marker = self.vision.match_best_in_region(
            screenshot,
            SPEED_SWITCH_TRIGGER_BUTTONS + SPEED_ALREADY_THREE_MARKERS,
            min(self.button_threshold, 0.68),
            REGION_TOP_RIGHT,
        )
        if not (main_marker or speed_marker):
            return False

        disruptive_stage = any(
            detector(screenshot)
            for detector in (
                self.find_special_training_screen_in_screenshot,
                self.find_club_transfers_screen_in_screenshot,
                self.find_club_transfers_level_screen_in_screenshot,
                self.find_sp_join_screen_in_screenshot,
                self.find_final_confirm_screen_in_screenshot,
                self.find_login_screen_in_screenshot,
                self.find_save_selection_screen_in_screenshot,
                self.find_game_main_screen_in_screenshot,
                self.find_match_reward_screen_in_screenshot,
            )
        )
        return not disruptive_stage

    def click_advance_schedule_action(
        self,
        match: MatchResult | None = None,
        hotspot_variant: int = 0,
        settle_between: float = 0.18,
        assume_main_visible: bool = False,
    ) -> bool:
        if not assume_main_visible:
            screenshot = self.vision.capture()
            if not self.is_confirmed_main_screen(screenshot):
                logging.warning("Skipping advance schedule action because the current screen is not a confirmed creative mode main screen")
                return False
        else:
            logging.info("Advance schedule action is trusting the caller-confirmed creative mode main screen")

        if match:
            logging.info(
                "Executing advance schedule action with a single click on matched target %s at (%s,%s)",
                match.name,
                match.center[0],
                match.center[1],
            )
            self.click_match(match, settle=settle_between)
            return True

        if not assume_main_visible:
            screenshot = self.vision.capture()
            if not self.is_confirmed_main_screen(screenshot):
                logging.warning("Skipping advance schedule hotspot action because the current screen is not a confirmed creative mode main screen")
                return False

        logging.info("Executing advance schedule action with a single click on schedule-card hotspot #%s", hotspot_variant + 1)
        self.click_main_screen_schedule_hotspot(variant=hotspot_variant, settle=settle_between)
        return True

    def poll_until_main_screen_returns(self, max_wait_seconds: float) -> bool:
        return self.main_flow.wait_for_main_screen_return(max_wait_seconds)

    def handle_post_schedule_events(self, max_clicks: int = 20) -> bool:
        event_threshold = min(self.dialog_threshold, 0.72)
        handled = False
        for attempt in range(1, max_clicks + 1):
            if not self.check_runtime_process_only():
                return handled

            self.window.move_cursor_client(x_ratio=0.08, y_ratio=0.08)
            screenshot = self.vision.capture()
            confirm_button = self.vision.match_best(screenshot, CONFIRM_BUTTONS, min(self.button_threshold, 0.72))
            if confirm_button:
                handled = True
                logging.info(
                    "Post-schedule confirm button detected: %s (score=%.3f), clicking it on attempt %s",
                    confirm_button.name,
                    confirm_button.score,
                    attempt,
                )
                self.click_match(confirm_button, settle=0.2)
                continue

            event_choice = self.find_event_choice_in_screenshot(screenshot)
            if event_choice:
                handled = True
                logging.info("Event-choice marker detected, selecting the first option on attempt %s", attempt)
                self.click_event_log_first_option(settle=0.15)
                continue

            skip_button = self.vision.wait_for_any(
                SKIP_BUTTONS,
                threshold=min(self.button_threshold, SKIP_THRESHOLD),
                timeout=0.12,
                interval=0.04,
            )
            if skip_button:
                handled = True
                logging.info("Post-schedule skip button detected, clicking skip on attempt %s", attempt)
                self.click_match(skip_button, settle=0.1)
                if self.rapidly_advance_event_story(attempts=4, settle=0.08):
                    return True

            event = self.vision.wait_for_any(EVENT_DIALOG_MARKERS, event_threshold, timeout=0.12, interval=0.05)
            if not event and not skip_button:
                return handled

            handled = True
            if event:
                logging.info(
                    "Post-schedule event detected: %s (score=%.3f), rapidly clicking left through attempt %s",
                    event.name,
                    event.score,
                    attempt,
                )
                if not skip_button:
                    self.click_skip_hotspot(settle=0.08)
            else:
                logging.info("Skip button clicked, rapidly advancing story with left clicks on attempt %s", attempt)

            if self.rapidly_advance_event_story(attempts=5, settle=0.1):
                return True

        logging.warning("Event markers remained visible after repeated click-through attempts")
        return handled

    def handle_connecting_screen(self, max_clicks: int = 20) -> bool:
        if not CONNECTING_MARKERS:
            return False
        handled = False
        for attempt in range(1, max_clicks + 1):
            if not self.check_runtime_process_only():
                return handled

            connecting = self.vision.wait_for_any(
                CONNECTING_MARKERS,
                threshold=CONNECTING_THRESHOLD,
                timeout=0.25,
                interval=0.1,
            )
            if not connecting:
                return handled

            handled = True
            logging.info("CONNECTING screen detected, clicking through attempt %s", attempt)
            self.window.click_client_bottom_right(settle=0.2)

            if self.is_main_screen():
                logging.info("CONNECTING screen cleared and creative mode main screen returned")
                return True

        logging.warning("CONNECTING screen remained visible after repeated click-through attempts")
        return handled

    def handle_league_result_screen(self, max_clicks: int = 6) -> bool:
        handled = False
        threshold = 0.70
        for attempt in range(1, max_clicks + 1):
            if not self.check_runtime_process_only():
                return handled

            title = self.wait_for_ocr_text_in_region(
                OCR_TEXT_LEAGUE_RESULT,
                REGION_WIDE_TOP,
                timeout=0.25,
                interval=0.1,
                min_score=0.35,
            )
            if not title:
                return handled

            handled = True
            button = self.vision.wait_for_any(
                LEAGUE_RESULT_CONTINUE_BUTTONS,
                threshold=min(self.button_threshold, 0.55),
                timeout=0.35,
                interval=0.1,
            )
            if button:
                logging.info("League result screen detected, clicking continue on attempt %s", attempt)
                self.click_match(button, settle=0.25)
            else:
                logging.info("League result screen detected, continue button not matched, using bottom-right click attempt %s", attempt)
                self.window.click_client_bottom_right(settle=0.2)

            if self.is_main_screen():
                logging.info("League result screen cleared and creative mode main screen returned")
                return True

        logging.warning("League result screen remained visible after repeated continue attempts")
        return handled

    def find_match_reward_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        if self._has_frame_cached(screenshot, "match_reward_screen"):
            return self._get_frame_cached(screenshot, "match_reward_screen")  # type: ignore[return-value]
        title = self._match_ocr_title(screenshot, OCR_TEXT_MATCH_REWARD, REGION_WIDE_TOP, min_score=0.35)
        marker = self.vision.match_best_in_region(
            screenshot,
            MATCH_REWARD_MARKERS + MATCH_REWARD_SPEED_SWITCH_MARKERS,
            min(self.dialog_threshold, 0.60),
            REGION_CENTER,
        )
        return self._set_frame_cached(screenshot, "match_reward_screen", self._pick_best_match(title, marker))  # type: ignore[return-value]

    def is_match_reward_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_match_reward_screen_in_screenshot(screenshot)

    def handle_match_reward_screen(self) -> bool:
        match_reward = self.is_match_reward_screen()
        if not match_reward:
            return False

        logging.info("Match reward screen detected, ensuring 3x speed before continuing")
        screenshot = self.vision.capture()
        reward_speed_state, reward_speed_marker = self.detect_speed_state(
            screenshot,
            prefer_reward_context=True,
        )
        reward_speed_one_loose = None
        if reward_speed_state == "unknown":
            reward_speed_one_loose = self.vision.match_best_in_region(
                screenshot,
                MATCH_REWARD_SPEED_SWITCH_MARKERS,
                min(SPEED_ONE_THRESHOLD, 0.55),
                REGION_TOP_RIGHT,
            )

        if reward_speed_state == "one" or reward_speed_one_loose:
            marker = reward_speed_marker if reward_speed_state == "one" else reward_speed_one_loose
            assert marker is not None
            logging.info("Match reward screen shows 1x speed via %s, switching to 3x", marker.name)
            if self.ensure_speed_three(screenshot=screenshot, prefer_reward_context=True):
                return True
            logging.info("3x speed switch was not confirmed, continuing with reward-screen dismissal")
        elif reward_speed_state == "three" and reward_speed_marker:
            logging.info(
                "Match reward screen already appears to be at 3x speed via %s (score=%.3f)",
                reward_speed_marker.name,
                reward_speed_marker.score,
            )
        else:
            logging.info("Match reward screen does not currently show a usable speed marker")

        screenshot = self.vision.capture()
        button = self.vision.match_best(
            screenshot,
            [*CONTINUE_BUTTONS, *CONFIRM_BUTTONS],
            min(self.button_threshold, 0.55),
        )
        if button:
            logging.info("Match reward screen dismiss button detected: %s (score=%.3f)", button.name, button.score)
            self.click_match(button, settle=0.2)
        else:
            logging.info("Match reward screen dismiss button not matched, using bottom-right click fallback")
            self.window.click_client_bottom_right(settle=0.2)
        return True

    def choose_third_save_slot(self) -> bool:
        rect = self.window.client_rect_screen()
        x = max(1, min(rect["width"] - 1, int(rect["width"] * SAVE_SLOT_THIRD_RATIO[0])))
        y = max(1, min(rect["height"] - 1, int(rect["height"] * SAVE_SLOT_THIRD_RATIO[1])))
        logging.info("Selecting third save slot at (%s, %s)", x, y)
        self.window.click_client(x, y, settle=0.8)
        self.awaiting_save_selection = False
        self.awaiting_main_after_save_selection = True
        self.last_save_selection_click_time = time.time()
        self.last_bootstrap_login_click_time = 0.0
        return True

    def run_bootstrap_flow(
        self,
        timeout_seconds: float = BOOTSTRAP_TIMEOUT_SECONDS,
        handoff_main_wait_seconds: float | None = None,
    ) -> bool:
        return self.bootstrap_flow.run(
            timeout_seconds=timeout_seconds,
            post_login_cooldown_seconds=BOOTSTRAP_POST_LOGIN_GAME_MAIN_SECONDS,
            handoff_main_wait_seconds=handoff_main_wait_seconds,
        )

    def run_club_transfers_flow(self, assume_detected: bool = False) -> bool:
        return self.new_season_flow.run_club_transfers(assume_detected=assume_detected)

    def run_club_transfers_level_flow(self, screenshot: np.ndarray | None = None, assume_detected: bool = False) -> bool:
        return self.new_season_flow.run_club_transfers_level(screenshot=screenshot, assume_detected=assume_detected)

    def select_sp_join_candidates(self, screenshot: np.ndarray, max_select: int = 3) -> int:
        return self.new_season_flow.select_sp_join_candidates(screenshot, max_select=max_select)

    def scroll_sp_join_list_to_bottom(self) -> None:
        self.new_season_flow.scroll_sp_join_list_to_bottom()

    def apply_sp_join_filter(self) -> bool:
        return self.new_season_flow.apply_sp_join_filter()

    def run_sp_join_flow(self, screenshot: np.ndarray | None = None, assume_detected: bool = False) -> bool:
        return self.new_season_flow.run_sp_join(screenshot=screenshot, assume_detected=assume_detected)

    def run_final_confirm_flow(self, assume_detected: bool = False) -> bool:
        return self.new_season_flow.run_final_confirm(assume_detected=assume_detected)

    def run_back_recovery_flow(self) -> bool:
        if self.has_priority_button_visible():
            return False
        if (
            self.is_club_transfers_screen()
            or self.is_club_transfers_level_screen()
            or self.is_sp_join_screen()
            or self.is_final_confirm_screen()
        ):
            return False

        screenshot = self.vision.capture()
        if not self.is_confirmed_main_screen(screenshot):
            logging.info("Recovery is on a non-main screen without a higher-priority flow, clicking top-left back hotspot first")
            self.click_special_training_back_hotspot(settle=0.35)
            return True

        self.window.move_cursor_client(x_ratio=0.92, y_ratio=0.92)
        back_button = self.vision.wait_for_any(BACK_BUTTONS, self.button_threshold, timeout=1.5, interval=0.2)
        if not back_button:
            logging.info("Back-button template was not detected during recovery, clicking top-left back hotspot")
            self.click_special_training_back_hotspot(settle=0.35)
            return True

        logging.info("Back-button recovery detected, clicking return")
        self.click_match(back_button, settle=1.0)
        self.window.move_cursor_client(x_ratio=0.92, y_ratio=0.92)
        return True

    def run_new_season_flow(self, screenshot: np.ndarray | None = None) -> bool:
        return self.new_season_flow.run(screenshot)

    def recover_to_main_screen(self, timeout_seconds: float = STARTUP_RECOVERY_SECONDS) -> bool:
        return self.recovery_flow.run(timeout_seconds)

    def try_enter_special_training(self) -> bool:
        for attempt in range(1, 3):
            if not self.check_runtime_health():
                return False
            screenshot = self.vision.capture()
            if not self.is_confirmed_main_screen(screenshot):
                logging.info("Skipping special training entry because the current screen is not a confirmed creative mode main screen")
                return False
            match = self.find_special_training_entry_on_main_screen(screenshot)
            if not match:
                logging.info("Special training template not found, using hotspot fallback on attempt %s", attempt)
                self.click_main_screen_special_training_hotspot(settle=0.5)
            else:
                logging.info("Trying to enter special training, attempt %s", attempt)
                self.click_match(match, settle=0.6)
            title = self.wait_for_special_training_title(
                OCR_TEXT_SPECIAL_TRAINING_SETTINGS + OCR_TEXT_SPECIAL_TRAINING_RESULT,
                timeout=1.5,
                interval=0.2,
            )
            if title:
                logging.info("Entered special training page via %s", title.name)
                return True
        logging.info("No settings screen after two clicks, treating this as no-op")
        return False

    def try_enter_special_training_fast(self) -> bool:
        transition_settle_seconds = 1.0
        transition_wait_seconds = 2.4
        quick_main_return_fail_seconds = 0.45
        if time.time() < self.special_training_unavailable_until:
            logging.info("Fast path is skipping special training because it was recently confirmed unavailable")
            return False
        for attempt in range(1, 3):
            if not self.check_runtime_process_only():
                return False
            screenshot = self.vision.capture()
            title = self.find_special_training_title_in_screenshot(screenshot)
            if title:
                self.special_training_unavailable_until = 0.0
                logging.info("Entered special training page via fast path: %s", title.name)
                return True
            special_training_screen = self.find_special_training_screen_in_screenshot(screenshot)
            if special_training_screen:
                self.special_training_unavailable_until = 0.0
                logging.info(
                    "Entered special training page via fast path screen markers: %s (score=%.3f)",
                    special_training_screen.name,
                    special_training_screen.score,
                )
                return True

            main_visible = self.find_main_screen_in_screenshot(screenshot)
            trusted_main = self.should_trust_main_screen(screenshot)
            confirmed_main = False
            if not main_visible and not trusted_main:
                confirmed_main = self.is_confirmed_main_screen(screenshot)

            if not main_visible and not trusted_main and not confirmed_main:
                logging.info("Fast path skipped special training entry because the current screen is not a confirmed creative mode main screen")
                return False
            elif trusted_main and not main_visible:
                logging.info("Fast path trusted recent creative mode main-screen confirmation before special training entry")

            if not (main_visible or trusted_main or confirmed_main):
                continue

            match = self.find_special_training_entry_on_main_screen(screenshot)
            if not match:
                logging.info("Fast path using special training hotspot fallback on attempt %s", attempt)
                self.click_main_screen_special_training_hotspot(settle=0.5)
            else:
                logging.info("Fast path entering special training, attempt %s", attempt)
                self.click_match(match, settle=0.5)

            settle_deadline = time.time() + transition_settle_seconds
            while time.time() < settle_deadline:
                if not self.check_runtime_process_only():
                    return False
                time.sleep(0.1)

            handoff_deadline = time.time() + transition_wait_seconds
            handoff_started_at = time.time()
            while time.time() < handoff_deadline:
                if not self.check_runtime_process_only():
                    return False
                handoff_screenshot = self.vision.capture()
                title = self.find_special_training_title_in_screenshot(handoff_screenshot)
                if title:
                    self.special_training_unavailable_until = 0.0
                    logging.info("Entered special training page via fast path: %s", title.name)
                    return True

                special_training_screen = self.find_special_training_screen_in_screenshot(handoff_screenshot)
                if special_training_screen:
                    self.special_training_unavailable_until = 0.0
                    logging.info(
                        "Entered special training page via fast path screen markers: %s (score=%.3f)",
                        special_training_screen.name,
                        special_training_screen.score,
                    )
                    return True

                if self.find_main_screen_in_screenshot(handoff_screenshot):
                    elapsed = time.time() - handoff_started_at
                    logging.info(
                        "Fast path special training handoff returned to creative mode main screen after attempt %s (elapsed=%.2fs)",
                        attempt,
                        elapsed,
                    )
                    if elapsed < quick_main_return_fail_seconds:
                        self.special_training_unavailable_until = time.time() + SPECIAL_TRAINING_RETRY_COOLDOWN_SECONDS
                        logging.info(
                            "Fast path is treating special training as unavailable after a quick return to main; cooling down for %.0fs",
                            SPECIAL_TRAINING_RETRY_COOLDOWN_SECONDS,
                        )
                        return False
                    self.special_training_unavailable_until = time.time() + SPECIAL_TRAINING_RETRY_COOLDOWN_SECONDS
                    logging.info(
                        "Fast path is treating special training as unavailable after a return to main without opening settings; cooling down for %.0fs",
                        SPECIAL_TRAINING_RETRY_COOLDOWN_SECONDS,
                    )
                    return False

                time.sleep(0.12)
        self.special_training_unavailable_until = time.time() + SPECIAL_TRAINING_RETRY_COOLDOWN_SECONDS
        logging.info("Fast path did not confirm special training settings after two attempts")
        return False

    def handle_confirm_dialog(self, dialog_name: str | None = None) -> bool:
        confirm_threshold = min(self.dialog_threshold, self.button_threshold, 0.72)
        trigger_names = [*CONFIRM_BUTTONS]
        if dialog_name:
            trigger_names.insert(0, dialog_name)
        trigger = self.vision.wait_for_any(trigger_names, confirm_threshold, timeout=4.0, interval=0.3)
        if not trigger:
            logging.warning("Neither confirm dialog nor Ok button was detected: %s", dialog_name or "generic_confirm")
            return False
        logging.info("Confirm trigger detected: %s (score=%.3f)", trigger.name, trigger.score)
        ok = self.vision.wait_for_any(CONFIRM_BUTTONS, confirm_threshold, timeout=4.0, interval=0.3)
        if not ok:
            logging.warning("Confirm dialog detected, but Ok button was not found")
            return False
        self.click_match(ok, settle=1.0)
        return True

    def handle_optional_confirm_dialog(self, dialog_name: str | None = None) -> bool:
        confirm_threshold = min(self.dialog_threshold, self.button_threshold, 0.72)
        trigger_names = [*CONFIRM_BUTTONS]
        if dialog_name:
            trigger_names.insert(0, dialog_name)
        trigger = self.vision.wait_for_any(trigger_names, confirm_threshold, timeout=2.0, interval=0.3)
        if not trigger:
            logging.debug("Optional confirm dialog not detected: %s", dialog_name or "generic_confirm")
            return False
        logging.info("Optional confirm trigger detected: %s (score=%.3f)", trigger.name, trigger.score)
        ok = self.vision.wait_for_any(CONFIRM_BUTTONS, confirm_threshold, timeout=3.0, interval=0.3)
        if not ok:
            logging.warning("Optional confirm dialog detected, but Ok button was not found")
            return False
        self.click_match(ok, settle=1.0)
        return True

    def handle_confirm_dialog_fast(self, dialog_name: str | None = None) -> bool:
        confirm_threshold = min(self.dialog_threshold, self.button_threshold, 0.72)
        trigger_names = [*CONFIRM_BUTTONS]
        if dialog_name:
            trigger_names.insert(0, dialog_name)
        trigger = self.vision.wait_for_any(trigger_names, confirm_threshold, timeout=1.2, interval=0.12)
        if not trigger:
            logging.debug("Fast confirm dialog not detected: %s", dialog_name or "generic_confirm")
            return False
        ok = self.vision.wait_for_any(CONFIRM_BUTTONS, confirm_threshold, timeout=1.2, interval=0.12)
        if not ok:
            logging.warning("Fast confirm dialog detected, but Ok button was not found: %s", dialog_name)
            return False
        self.click_match(ok, settle=0.4)
        return True

    def handle_optional_confirm_dialog_fast(self, dialog_name: str | None = None) -> bool:
        confirm_threshold = min(self.dialog_threshold, self.button_threshold, 0.72)
        trigger_names = [*CONFIRM_BUTTONS]
        if dialog_name:
            trigger_names.insert(0, dialog_name)
        trigger = self.vision.wait_for_any(trigger_names, confirm_threshold, timeout=0.9, interval=0.12)
        if not trigger:
            return False
        ok = self.vision.wait_for_any(CONFIRM_BUTTONS, confirm_threshold, timeout=0.9, interval=0.12)
        if not ok:
            logging.warning("Fast optional confirm dialog detected, but Ok button was not found: %s", dialog_name)
            return False
        self.click_match(ok, settle=0.4)
        return True

    def leave_special_training(self) -> bool:
        for attempt in range(1, 7):
            if not self.check_runtime_health():
                return False
            self.window.move_cursor_client(x_ratio=0.92, y_ratio=0.92)
            back_button = self.vision.wait_for_any(BACK_BUTTONS, self.button_threshold, timeout=1.0, interval=0.2)
            if not back_button:
                screenshot = self.vision.capture()
                if self.has_returned_to_main_from_special_training(screenshot):
                    logging.info("Returned from special training to main screen")
                    return True
                if self.find_special_training_screen_in_screenshot(screenshot):
                    logging.info("Back button not detected on special training screen, clicking top-left back hotspot")
                    self.click_special_training_back_hotspot(settle=0.45)
                    continue
                if self.handle_global_priority_buttons(max_clicks=1):
                    return True
                logging.warning("Back button disappeared, but main screen could not be confirmed")
                return False

            logging.info("Clicking back button, attempt %s", attempt)
            self.click_match(back_button, settle=0.5)
            self.handle_optional_confirm_dialog()
            self.handle_optional_confirm_dialog()

            self.window.move_cursor_client(x_ratio=0.92, y_ratio=0.92)
            screenshot = self.vision.capture()
            if self.find_special_training_screen_in_screenshot(screenshot):
                if self.vision.wait_for_any(BACK_BUTTONS, self.button_threshold, timeout=0.6, interval=0.2):
                    logging.warning("Back button still visible after click, retrying")
                    continue
                logging.info("Special training still visible after back click, clicking top-left back hotspot")
                self.click_special_training_back_hotspot(settle=0.45)
                continue

            if self.handle_global_priority_buttons(max_clicks=1):
                return True

            screenshot = self.vision.capture()
            if self.has_returned_to_main_from_special_training(screenshot):
                logging.info("Returned from special training to main screen")
                return True

            if self.vision.wait_for_any(BACK_BUTTONS, self.button_threshold, timeout=0.6, interval=0.2):
                logging.warning("Back button still visible after click, retrying")
                continue

            logging.warning("Back button click completed, but return to main screen is still unconfirmed")

        logging.warning("Back button remained visible after repeated clicks")
        return False

    def leave_special_training_fast(self) -> bool:
        for attempt in range(1, 7):
            if not self.check_runtime_process_only():
                return False
            self.window.move_cursor_client(x_ratio=0.92, y_ratio=0.92)
            back_button = self.wait_for_any_in_region(
                BACK_BUTTONS,
                self.button_threshold,
                REGION_TOP_LEFT,
                timeout=0.45,
                interval=0.12,
            )
            if not back_button:
                screenshot = self.vision.capture()
                if self.has_returned_to_main_from_special_training(screenshot):
                    logging.info("Fast path returned from special training to main screen")
                    return True
                if self.find_special_training_screen_in_screenshot(screenshot):
                    logging.info("Fast path could not detect back button, clicking top-left back hotspot")
                    self.click_special_training_back_hotspot(settle=0.25)
                    continue
                return False

            logging.info("Fast path clicking back button from special training, attempt %s", attempt)
            self.click_match(back_button, settle=0.25)
            self.handle_optional_confirm_dialog_fast()
            self.handle_optional_confirm_dialog_fast()

            deadline = time.time() + 1.2
            while time.time() < deadline:
                screenshot = self.vision.capture()
                if self.has_returned_to_main_from_special_training(screenshot):
                    logging.info("Fast path returned from special training to main screen")
                    return True
                if not self.find_special_training_screen_in_screenshot(screenshot):
                    if self.handle_global_priority_buttons(max_clicks=1, initial_screenshot=screenshot):
                        continue
                    time.sleep(0.12)
                    continue
                break

            if self.find_special_training_screen_in_screenshot(self.vision.capture()):
                logging.info("Fast path still sees special training after back click, clicking top-left back hotspot")
                self.click_special_training_back_hotspot(settle=0.25)
                continue

            if self.wait_for_any_in_region(
                MAIN_SCREEN_BUTTONS,
                min(self.main_threshold, 0.75),
                REGION_BOTTOM_RIGHT,
                timeout=0.9,
                interval=0.12,
            ):
                logging.info("Fast path returned from special training to main screen")
                return True

        logging.warning("Fast path could not leave special training quickly")
        return False

    def run_special_training_flow(self) -> bool:
        return self.main_flow.run_special_training()

    def run_special_training_flow_fast(self) -> bool:
        return self.main_flow.run_special_training_fast()

    def advance_schedule(self, max_wait_seconds: float) -> bool:
        return self.main_flow.advance_schedule(max_wait_seconds)

    def handle_post_schedule_events_fast(self, max_clicks: int = 6) -> bool:
        handled = False
        for attempt in range(1, max_clicks + 1):
            if not self.check_runtime_process_only():
                return handled

            screenshot = self.vision.capture()
            if self.handle_story_dialog_fast(screenshot=screenshot, attempts=3):
                handled = True
                continue

            confirm_button = self.vision.match_best(screenshot, CONFIRM_BUTTONS, min(self.button_threshold, 0.72))
            if confirm_button:
                handled = True
                logging.info("Fast post-schedule confirm detected on attempt %s", attempt)
                self.click_match(confirm_button, settle=0.2)
                continue

            continue_button = self.vision.match_best(screenshot, CONTINUE_BUTTONS, min(self.button_threshold, 0.72))
            if continue_button:
                handled = True
                logging.info("Fast post-schedule continue detected on attempt %s", attempt)
                self.click_match(continue_button, settle=0.2)
                continue

            event_choice = self.find_event_choice_in_screenshot(screenshot)
            if event_choice:
                handled = True
                logging.info("Fast post-schedule event choice detected on attempt %s", attempt)
                self.click_event_log_first_option(settle=0.15)
                continue

            skip_button = self.vision.match_best(screenshot, SKIP_BUTTONS, min(self.button_threshold, SKIP_THRESHOLD))
            if skip_button:
                handled = True
                logging.info("Fast post-schedule skip detected on attempt %s", attempt)
                self.click_match(skip_button, settle=0.1)
                followup_screenshot = self.vision.capture()
                if self.handle_story_dialog_fast(screenshot=followup_screenshot, attempts=3):
                    continue
                if self._handle_fast_story_transition_from_screenshot(followup_screenshot):
                    continue
                continue

            return handled

        return handled

    def advance_schedule_fast(self, max_wait_seconds: float) -> bool:
        return self.main_flow.advance_schedule_fast(max_wait_seconds)

    def fast_main_screen_flow(
        self,
        max_wait_seconds: float,
        screenshot: np.ndarray | None = None,
        assume_main_visible: bool = False,
    ) -> bool:
        return self.main_flow.fast_path(
            max_wait_seconds,
            screenshot=screenshot,
            assume_main_visible=assume_main_visible,
        )

    def _is_in_post_schedule_exception_fastlane(self) -> bool:
        return (
            self.last_advance_schedule_click_time > 0
            and time.time() - self.last_advance_schedule_click_time <= POST_SCHEDULE_EXCEPTION_FASTLANE_SECONDS
        )

    def _dispatch_loop_start_fastlane(self, screenshot: np.ndarray, max_wait_seconds: float) -> bool | None:
        in_post_schedule_exception_fastlane = self._is_in_post_schedule_exception_fastlane()

        if time.time() - self.last_save_selection_click_time <= POST_SAVE_SELECTION_ENTRY_FASTLANE_SECONDS:
            if self.handle_emergency_buttons(max_clicks=1, initial_screenshot=screenshot):
                return True
            if self.bootstrap_flow.matches(screenshot):
                logging.info("Loop start is within the post-save-selection fast lane, continuing bootstrap handling")
                return self.run_bootstrap_flow(handoff_main_wait_seconds=max_wait_seconds)
            if self.main_flow.matches(screenshot):
                logging.info("Loop start is within the post-save-selection fast lane, dispatching directly to main flow")
                return self.main_flow.run(max_wait_seconds, screenshot=screenshot, assume_main_visible=True)
            if self.new_season_flow.matches(screenshot):
                self.set_active_flow("new_season")
                logging.info("Loop start is within the post-save-selection fast lane, dispatching directly to new-season flow")
                return self.new_season_flow.run(screenshot)

        if time.time() - self.last_new_season_activity_time <= NEW_SEASON_FASTLANE_SECONDS:
            sp_join_screen = self.find_sp_join_screen_in_screenshot(screenshot)
            if sp_join_screen:
                self.set_active_flow("new_season")
                logging.info("Loop start is within the new-season fast lane and SP join is visible, dispatching immediately")
                return self.new_season_flow.run(screenshot, fast_dispatch=True)
            if self.new_season_flow.matches(screenshot):
                self.set_active_flow("new_season")
                logging.info("Loop start is within the new-season fast lane, dispatching directly to new-season flow")
                return self.new_season_flow.run(screenshot)
            if self.handle_emergency_buttons(max_clicks=1, initial_screenshot=screenshot):
                return True

        if time.time() - self.last_final_confirm_time <= SP_JOIN_POST_CONFIRM_FASTLANE_SECONDS:
            sp_join_screen = self.find_sp_join_screen_in_screenshot(screenshot)
            if sp_join_screen:
                self.set_active_flow("new_season")
                logging.info("Loop start is within the post-final-confirm SP join fast lane, dispatching immediately")
                return self.new_season_flow.run(screenshot, fast_dispatch=True)

        sp_join_screen = self.find_sp_join_screen_in_screenshot(screenshot)
        if sp_join_screen:
            self.set_active_flow("new_season")
            logging.info("Loop start visibly shows SP join, dispatching before common flow")
            return self.new_season_flow.run(screenshot, fast_dispatch=True)

        if in_post_schedule_exception_fastlane:
            if self.handle_post_schedule_events_fast(max_clicks=4):
                return True
            if self.find_match_reward_screen_in_screenshot(screenshot):
                logging.info("Loop start is within the post-schedule exception fast lane and match reward is visible")
                return self.handle_match_reward_screen()

        return None

    def _dispatch_stage(
        self,
        screenshot: np.ndarray,
        max_wait_seconds: float,
        *,
        stage_prefix: str,
        allow_bootstrap_to_main_fastlane: bool,
        allow_post_schedule_main_guard: bool,
    ) -> bool | None:
        in_post_schedule_exception_fastlane = self._is_in_post_schedule_exception_fastlane()

        if self.is_new_season_context_active_in_screenshot(screenshot):
            sp_join_screen = self.find_sp_join_screen_in_screenshot(screenshot)
            self.set_active_flow("new_season")
            if sp_join_screen:
                logging.info("%s is inside the active new-season context and SP join is visible, dispatching immediately", stage_prefix)
                return self.new_season_flow.run(screenshot, fast_dispatch=True)
            logging.info("%s is inside the active new-season context, dispatching directly to new-season flow", stage_prefix)
            return self.new_season_flow.run(screenshot, fast_dispatch=True)

        if allow_bootstrap_to_main_fastlane and time.time() - self.last_bootstrap_to_main_time <= BOOTSTRAP_TO_MAIN_FASTLANE_SECONDS:
            main_visible = self.find_main_screen_in_screenshot(screenshot)
            special_training_visible = self.find_special_training_screen_in_screenshot(screenshot)
            confirmed_main = self.is_confirmed_main_screen(screenshot)
            if (special_training_visible or confirmed_main) and (main_visible or not in_post_schedule_exception_fastlane):
                logging.info("%s is within the bootstrap-to-main fast lane, dispatching directly to main flow", stage_prefix)
                return self.main_flow.run(
                    max_wait_seconds,
                    screenshot=screenshot,
                    assume_main_visible=confirmed_main and not special_training_visible,
                )

        if self.bootstrap_flow.matches(screenshot):
            logging.info("%s belongs to the bootstrap layer", stage_prefix)
            return self.run_bootstrap_flow(handoff_main_wait_seconds=max_wait_seconds)

        main_visible = self.find_main_screen_in_screenshot(screenshot)
        special_training_visible = self.find_special_training_screen_in_screenshot(screenshot)
        confirmed_main = self.is_confirmed_main_screen(screenshot)
        allow_main_dispatch = bool(special_training_visible or confirmed_main)
        if allow_post_schedule_main_guard:
            allow_main_dispatch = allow_main_dispatch and (main_visible or not in_post_schedule_exception_fastlane)
        if allow_main_dispatch:
            logging.info("%s belongs to the creative-mode main layer", stage_prefix)
            logging.info("Dispatching %s directly into main_flow.run()", stage_prefix.lower())
            result = self.main_flow.run(
                max_wait_seconds,
                screenshot=screenshot,
                assume_main_visible=confirmed_main and not special_training_visible,
            )
            logging.info("main_flow.run() returned %s for %s", result, stage_prefix.lower())
            return result

        sp_join_screen = self.find_sp_join_screen_in_screenshot(screenshot)
        if sp_join_screen:
            self.set_active_flow("new_season")
            logging.info("%s is visibly SP join, dispatching immediately to new-season flow", stage_prefix)
            return self.new_season_flow.run(screenshot, fast_dispatch=True)

        if self.new_season_flow.matches(screenshot):
            self.set_active_flow("new_season")
            logging.info("%s is already on a new-season step", stage_prefix)
            return self.new_season_flow.run(screenshot)

        if self.find_club_transfers_level_title_in_screenshot(screenshot):
            self.set_active_flow("new_season")
            logging.info("Club transfers level screen detected at %s", stage_prefix.lower())
            return self.run_club_transfers_level_flow()

        return None

    def _dispatch_loop_start_by_stage(self, screenshot: np.ndarray, max_wait_seconds: float) -> bool | None:
        return self._dispatch_stage(
            screenshot,
            max_wait_seconds,
            stage_prefix="Loop start",
            allow_bootstrap_to_main_fastlane=True,
            allow_post_schedule_main_guard=True,
        )

    def _dispatch_current_stage(self, screenshot: np.ndarray, max_wait_seconds: float) -> bool | None:
        return self._dispatch_stage(
            screenshot,
            max_wait_seconds,
            stage_prefix="Current stage",
            allow_bootstrap_to_main_fastlane=False,
            allow_post_schedule_main_guard=False,
        )

    def run_once(self, max_wait_seconds: float) -> bool:
        self.set_active_flow("generic")
        initial_screenshot: np.ndarray | None = None
        if self.check_runtime_process_only():
            initial_screenshot = self.vision.capture()
            fastlane_result = self._dispatch_loop_start_fastlane(initial_screenshot, max_wait_seconds)
            if fastlane_result is not None:
                return fastlane_result
            if self.is_new_season_context_active_in_screenshot(initial_screenshot):
                self.set_active_flow("new_season")
                logging.info("Loop start is already inside the active new-season context, dispatching before common flow")
                return self.new_season_flow.run(initial_screenshot, fast_dispatch=True)
            initial_main_match = self.find_main_screen_in_screenshot(initial_screenshot)
            if initial_main_match and self.is_confirmed_main_screen(initial_screenshot):
                logging.info("Loop start strongly confirms the creative-mode main screen, dispatching before common flow")
                stage_result = self._dispatch_loop_start_by_stage(initial_screenshot, max_wait_seconds)
                if stage_result is not None:
                    return stage_result
            elif initial_main_match:
                logging.info("Loop start saw a weak main-screen match, but confirmation failed; falling back to common/stage handling")
            if self.common_flow.run_once(initial_screenshot, max_clicks=1):
                return True
            stage_result = self._dispatch_loop_start_by_stage(initial_screenshot, max_wait_seconds)
            if stage_result is not None:
                return stage_result
        if not self.check_runtime_health():
            return False
        if self.common_flow.run_once(max_clicks=4):
            return True

        screenshot = self.vision.capture()
        current_stage_result = self._dispatch_current_stage(screenshot, max_wait_seconds)
        if current_stage_result is not None:
            return current_stage_result
        if self.common_flow.handle_exception(screenshot=screenshot, max_clicks=1):
            return True

        if not self.recover_to_main_screen():
            self.fallback_click_when_no_operation_found()
            self.vision.save_debug_screenshot("not_on_main_screen")
            logging.error("Current screen is not the creative mode main screen")
            return False

        logging.info("Dispatching into main_flow.run_after_recovery()")
        result = self.main_flow.run_after_recovery(max_wait_seconds)
        logging.info("main_flow.run_after_recovery() returned %s", result)
        return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Football Club Champions creative mode automation")
    parser.add_argument("--process-name", default=PROCESS_NAME, help="Game process name")
    parser.add_argument(
        "--steam-game-id",
        default=os.environ.get("SFCC_STEAM_GAME_ID", DEFAULT_STEAM_GAME_ID),
        help="Steam app/game id used to build steam://rungameid/<id>",
    )
    parser.add_argument(
        "--steam-launch-url",
        default=os.environ.get("SFCC_STEAM_LAUNCH_URL", DEFAULT_STEAM_LAUNCH_URL),
        help="Explicit Steam launch URL, for example steam://rungameid/<id>",
    )
    parser.add_argument(
        "--game-exe-path",
        default=os.environ.get("SFCC_GAME_EXE_PATH", ""),
        help="Optional fallback path to the game executable when Steam URL launch is unavailable",
    )
    parser.add_argument("--max-wait-after-schedule", type=float, default=180.0, help="Maximum seconds to wait for main screen return")
    parser.add_argument("--loop-interval", type=float, default=2.0, help="Seconds to wait between loop iterations")
    parser.add_argument("--main-threshold", type=float, default=0.82, help="Match threshold for main-screen buttons")
    parser.add_argument("--button-threshold", type=float, default=0.80, help="Match threshold for regular buttons")
    parser.add_argument("--dialog-threshold", type=float, default=0.72, help="Match threshold for titles and dialogs")
    parser.add_argument("--log-level", default="DEBUG", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser


def configure_logging(level: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"cm_bot_{timestamp}.log"

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper()))
    root.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    logging.info("Log file: %s", log_path)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.log_level)
    vision: Vision | None = None
    required_templates = get_required_templates()

    try:
        logging.info(
            "Template groups loaded: %s",
            {group_name: len(group_templates) for group_name, group_templates in FLOW_TEMPLATE_GROUPS.items()},
        )
        templates = TemplateStore(TEMPLATE_DIR, template_paths=TEMPLATE_PATHS)
        templates.load(required_templates)
        window = GameWindow(args.process_name)
        vision = Vision(window, templates)
        game_exe_path = Path(args.game_exe_path).expanduser() if args.game_exe_path else None
        bot = CreativeModeBot(
            vision=vision,
            window=window,
            main_threshold=args.main_threshold,
            button_threshold=args.button_threshold,
            dialog_threshold=args.dialog_threshold,
            steam_game_id=args.steam_game_id,
            steam_launch_url=args.steam_launch_url,
            game_exe_path=game_exe_path,
        )

        if window.is_process_running():
            if not bot.ensure_attached():
                if not bot.restart_game("game window could not be attached at startup"):
                    logging.error("Initial recovery failed; keeping script alive and retrying shortly")
                    time.sleep(10.0)
        else:
            if not bot.restart_game("game process missing at startup"):
                logging.error("Initial game launch failed; keeping script alive and retrying shortly")
                time.sleep(10.0)

        iteration = 1
        consecutive_loop_exceptions = 0
        while True:
            try:
                if bot.restart_requested:
                    if not bot.restart_game(bot.restart_reason or "health check requested restart"):
                        logging.error("Restart request handling failed; will retry after a short pause")
                        time.sleep(10.0)
                        continue

                logging.info("Starting loop iteration %s", iteration)
                success = bot.run_once(args.max_wait_after_schedule)
                if bot.restart_requested:
                    if not bot.restart_game(bot.restart_reason or "health check requested restart"):
                        logging.error("Restart after loop iteration failed; will retry after a short pause")
                        time.sleep(10.0)
                        continue
                    continue

                if success:
                    logging.info("Loop iteration %s completed successfully", iteration)
                else:
                    logging.warning("Loop iteration %s did not complete successfully, continuing", iteration)
                consecutive_loop_exceptions = 0
                iteration += 1
                time.sleep(max(0.5, args.loop_interval))
            except Exception as loop_exc:
                if vision is not None:
                    try:
                        vision.save_debug_screenshot(f"loop_iteration_{iteration}_exception")
                    except Exception:
                        logging.exception("Failed to save screenshot after loop exception")
                logging.exception("Unhandled exception inside loop iteration %s: %s", iteration, loop_exc)
                consecutive_loop_exceptions += 1
                if consecutive_loop_exceptions >= LOOP_EXCEPTION_RESTART_THRESHOLD:
                    reason = f"{consecutive_loop_exceptions} consecutive loop exceptions"
                    logging.error("Restart requested after repeated loop exceptions: %s", reason)
                    bot.request_restart(reason)
                    if not bot.restart_game(bot.restart_reason or reason):
                        logging.error("Restart after repeated loop exceptions failed; will retry after a short pause")
                        time.sleep(10.0)
                    consecutive_loop_exceptions = 0
                iteration += 1
                time.sleep(max(1.0, args.loop_interval))
    except Exception as exc:
        if vision is not None:
            try:
                vision.save_debug_screenshot("unhandled_exception")
            except Exception:
                logging.exception("Failed to save screenshot after exception")
        logging.exception("Script failed: %s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
