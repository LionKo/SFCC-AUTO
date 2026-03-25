from __future__ import annotations

import argparse
import ctypes
import logging
import os
import subprocess
import sys
import time
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


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "CM_PNG"
LOG_DIR = BASE_DIR / "logs"
PROCESS_NAME = "FootballClubChampions.exe"
DEFAULT_STEAM_GAME_ID = ""
DEFAULT_STEAM_LAUNCH_URL = ""
EMERGENCY_PRIORITY_BUTTONS = ["close_button", "login_retry"]
CONFIRM_BUTTONS = ["ok_button", "ok_chs_button"]
PRIORITY1_BUTTONS = [
    "close_button",
    "login_retry",
    "match_result_button",
    "ok_button",
    "skip_button",
    "skip_button2",
]
PRIORITY1_FOLLOWUP_BUTTONS = ["continue_button"]
PRIORITY2_BUTTONS = ["final_confirm_ok_button", "final_confirm_ok_button2", "ok_chs_button"]
PRIORITY_BUTTONS = PRIORITY1_BUTTONS + PRIORITY1_FOLLOWUP_BUTTONS + PRIORITY2_BUTTONS
EVENT_DIALOG_MARKERS = ["assistant", "log"]
EVENT_LOG_CHOOSE_MARKERS = ["event_log_choose", "event_choose_mark"]
CONNECTING_MARKERS = ["connecting_indicator", "connecting_indicator2"]
CONNECTING_THRESHOLD = 0.68
LEAGUE_RESULT_TITLES = ["league_result_title"]
LEAGUE_RESULT_CONTINUE_BUTTONS = ["league_result_continue_button", "continue_button"]
MATCH_REWARD_TITLES = ["match_reward_title"]
MATCH_REWARD_MARKERS = ["match_reward_mark"]
MATCH_REWARD_SCREENS = ["match_reward_screen"]
SKIP_BUTTONS = ["skip_button", "skip_button2"]
SKIP_THRESHOLD = 0.60
MAIN_SCREEN_BUTTONS = [
    "creative_mode_advance_schedule_button_small",
    "creative_mode_advance_schedule_button",
    "creative_mode_advance_schedule_button2",
]
MAIN_SCREEN_EXTRA_MARKERS = [
    "creative_mode_special_training_button",
    "creative_mode_special_training_button2",
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
    "creative_mode_special_training_button2",
    "creative_mode_special_training_button3",
]
SPECIAL_TRAINING_RESET_BUTTONS = ["special_training_reset_all_button", "special_training_reset_all_button2"]
SPECIAL_TRAINING_RECOMMEND_BUTTONS = ["special_training_recommend_button", "special_training_recommend_button2"]
SPECIAL_TRAINING_EXECUTE_BUTTONS = ["special_training_execute_button", "special_training_execute_button2"]
BACK_BUTTONS = ["back_button", "back"]
CLUB_TRANSFERS_TITLES = ["club_transfers_title"]
CLUB_TRANSFERS_RENEWAL_BUTTONS = ["club_transfers_renewal_button", "club_transfers_renewal_button_2"]
CLUB_TRANSFERS_LEVEL_TITLES = ["club_transfers_lv_title", "club_transfers_lv_screen"]
CLUB_TRANSFERS_SCREEN_MARKERS = ["club_transfers_screen", "club_transfers_title"]
CLUB_TRANSFERS_THRESHOLD = 0.30
SP_JOIN_TITLES = ["sp_join_title", "sp_join_screen"]
SP_JOIN_FILTER_ENTRANCES = ["sp_join_filter_entrance"]
SP_JOIN_FILTER_POPUPS = ["sp_join_filter_popup"]
SP_JOIN_BUTTONS = ["sp_join_button1", "sp_join_button2", "sp_join_button3", "sp_join_button4"]
SP_JOIN_BELONG_MARKERS = ["sp_belong"]
SP_JOIN_SCREEN_MARKERS = ["sp_join_title", "sp_belong"]
SP_JOIN_THRESHOLD = 0.40
SP_BELONG_THRESHOLD = 0.72
SP_JOIN_SCROLL_RATIO = (0.82, 0.52)
SP_JOIN_SCROLL_STEPS_TO_BOTTOM = 7
SP_JOIN_SCROLL_DELTA = -120
FINAL_CONFIRM_TITLES = ["final_confirm_title", "final_confirm_screen"]
FINAL_CONFIRM_BUTTONS = ["final_confirm_ok_button", "final_confirm_ok_button2"]
LOGIN_SCREEN_MARKERS = ["login_screen_full", "login_mark"]
LOGIN_SCREEN_FULL_MARKERS = ["login_screen_full"]
LOGIN_SCREEN_LOGO_MARKERS = ["login_mark"]
GAME_MAIN_SCREEN_MARKERS = ["game_main_screen"]
GAME_MAIN_MARKERS = ["game_main_mark"]
GAME_MAIN_CREATE_ENTRANCES = ["game_main_create_entrance", "game_main_create_entrance2"]
GAME_MAIN_MARK_THRESHOLD = 0.65
GAME_MAIN_ENTRANCE_THRESHOLD = 0.68
SAVE_SELECTION_MARKERS = ["save_selection_title", "save_selection"]
SAVE_SELECTION_TITLE_MARKERS = ["save_selection_title"]
SAVE_SLOT_THIRD_RATIO = (0.80, 0.45)
MAIN_SCREEN_SPECIAL_TRAINING_RATIO = (0.503, 0.931)
MAIN_SCREEN_SCHEDULE_RATIOS = [
    (0.885, 0.900),
    (0.930, 0.945),
    (0.835, 0.855),
]
CLUB_TRANSFERS_MIN_RATIO = (0.334, 0.642)
EXPECTED_CLIENT_WIDTH = 1920
EXPECTED_CLIENT_HEIGHT = 1080
SCREEN_STUCK_TIMEOUT_SECONDS = 120.0
NO_SCHEDULE_TIMEOUT_SECONDS = 900.0
BOOTSTRAP_TIMEOUT_SECONDS = 180.0
BOOTSTRAP_POST_LOGIN_GAME_MAIN_SECONDS = 20.0
VISUAL_STALL_TIMEOUT_SECONDS = 120.0
VISUAL_STALL_CHECK_INTERVAL_SECONDS = 5.0
VISUAL_STALL_DIFF_THRESHOLD = 1.2
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
    "assistant",
    "log",
    "event_log_choose",
    "event_choose_mark",
    "skip_button",
    "skip_button2",
    "login_retry",
    "connecting_indicator",
    "connecting_indicator2",
    "league_result_title",
    "league_result_continue_button",
    "match_reward_title",
    "match_reward_mark",
    "match_reward_screen",
    "match_reward_speed1",
    "club_transfers_title",
    "club_transfers_lv_title",
    "club_transfers_lv_screen",
    "club_transfers_renewal_button",
    "club_transfers_renewal_button_2",
    "club_transfers_min_button",
    "sp_join_title",
    "sp_join_screen",
    "sp_join_filter_entrance",
    "sp_join_filter_popup",
    "sp_belong",
    "sp_join_button1",
    "sp_join_button2",
    "sp_join_button3",
    "sp_join_button4",
    "final_confirm_title",
    "final_confirm_screen",
    "final_confirm_ok_button",
    "final_confirm_ok_button2",
    "login_screen_full",
    "login_mark",
    "game_main_screen",
    "game_main_mark",
    "game_main_create_entrance",
    "game_main_create_entrance2",
    "save_selection",
    "save_selection_title",
    "creative_mode_advance_schedule_button",
    "creative_mode_advance_schedule_button2",
    "creative_mode_speed1",
    "match_reward_speed1",
    "creative_mode_speed_popup",
    "creative_mode_special_training_button",
    "creative_mode_special_training_button2",
    "creative_mode_special_training_button3",
    "special_training_settings_title",
    "special_training_reset_all_button",
    "special_training_reset_all_button2",
    "special_training_recommend_button",
    "special_training_recommend_button2",
    "special_training_execute_button",
    "special_training_execute_button2",
    "special_training_reset_all_confirm_dialog",
    "special_training_execute_confirm_dialog",
    "special_training_execute_confirm_next_dialog",
    "ok_button",
    "ok_chs_button",
    "back_button",
    "back",
]


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
REGION_TOP_CENTER = ScreenRegion(0.22, 0.0, 0.78, 0.30)
REGION_TOP_RIGHT = ScreenRegion(0.58, 0.0, 1.0, 0.28)
REGION_LEFT_PANEL = ScreenRegion(0.0, 0.08, 0.34, 0.95)
REGION_CENTER = ScreenRegion(0.18, 0.12, 0.82, 0.88)
REGION_CENTER_RIGHT = ScreenRegion(0.50, 0.10, 1.0, 0.92)
REGION_BOTTOM_HALF = ScreenRegion(0.0, 0.55, 1.0, 1.0)
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
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.templates: dict[str, np.ndarray] = {}

    def load(self, names: Iterable[str]) -> None:
        for name in names:
            if name in self.templates:
                continue
            path = self.directory / f"{name}.png"
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
        win32api.SetCursorPos((screen_x, screen_y))
        logging.debug("Moved cursor to client position (%s, %s)", x, y)
        time.sleep(0.2)


class Vision:
    def __init__(self, window: GameWindow, templates: TemplateStore) -> None:
        self.window = window
        self.templates = templates
        self.sct = mss.mss()
        self._resized_template_cache: dict[tuple[str, int, int], np.ndarray] = {}

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

        # Allow oversized templates to be scaled down to the current client area.
        # This keeps whole-screen/page markers usable when the game window is slightly shorter.
        if template.shape[0] == 0 or template.shape[1] == 0:
            return None

        cache_key = (name, screenshot.shape[1], screenshot.shape[0])
        cached = self._resized_template_cache.get(cache_key)
        if cached is not None:
            return cached

        resized = cv2.resize(
            template,
            (screenshot.shape[1], screenshot.shape[0]),
            interpolation=cv2.INTER_AREA,
        )
        logging.debug(
            "Resized oversized template %s from %sx%s to %sx%s",
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
        self.last_generic_confirm_click_time = 0.0
        self.last_special_training_run_time = 0.0
        self.last_club_transfers_min_click_time = 0.0
        self.last_bootstrap_login_click_time = 0.0
        self.active_flow = "generic"
        self.last_visual_probe_time = 0.0
        self.last_visual_change_time = now
        self.last_visual_signature: np.ndarray | None = None

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

    def _pick_best_match(self, *matches: MatchResult | None) -> MatchResult | None:
        available = [match for match in matches if match is not None]
        if not available:
            return None
        return max(available, key=lambda item: item.score)

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
            self.last_special_training_run_time = 0.0
            self.last_club_transfers_min_click_time = 0.0
            self.last_bootstrap_login_click_time = 0.0
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

    def find_main_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        return self._match_screen_profile(
            screenshot,
            strong_probes=[
                ScreenProbe(tuple(MAIN_SCREEN_BUTTONS), min(self.main_threshold, 0.55), REGION_SCHEDULE_BUTTON),
                ScreenProbe(tuple(MAIN_SCREEN_EXTRA_MARKERS), min(self.button_threshold, 0.85), REGION_BOTTOM_HALF),
                ScreenProbe(tuple(SPEED_SWITCH_TRIGGER_BUTTONS + SPEED_ALREADY_THREE_MARKERS), min(self.button_threshold, 0.72), REGION_TOP_RIGHT),
            ],
            min_strong=1,
        )

    def find_special_training_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        title = self.vision.match_best_in_region(
            screenshot,
            ["special_training_settings_title"],
            self.dialog_threshold,
            REGION_WIDE_TOP,
        )
        if not title:
            return None

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
        return self._match_screen_profile(
            screenshot,
            strong_probes=[
                ScreenProbe(tuple(CLUB_TRANSFERS_SCREEN_MARKERS), CLUB_TRANSFERS_THRESHOLD, REGION_WIDE_TOP, allow_fullscreen_fallback=True),
                ScreenProbe(tuple(CLUB_TRANSFERS_RENEWAL_BUTTONS), min(self.button_threshold, 0.80), REGION_BOTTOM_RIGHT),
            ],
            min_strong=2,
        )

    def is_club_transfers_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_club_transfers_screen_in_screenshot(screenshot)

    def find_club_transfers_level_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        return self._match_screen_profile(
            screenshot,
            strong_probes=[
                ScreenProbe(tuple(CLUB_TRANSFERS_LEVEL_TITLES), self.dialog_threshold, REGION_WIDE_TOP, allow_fullscreen_fallback=True),
                ScreenProbe(("club_transfers_min_button",), min(self.button_threshold, 0.72), REGION_CENTER_RIGHT),
            ],
            min_strong=2,
        )

    def is_club_transfers_level_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_club_transfers_level_screen_in_screenshot(screenshot)

    def find_club_transfers_level_title_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        return self.vision.match_best_in_region(
            screenshot,
            CLUB_TRANSFERS_LEVEL_TITLES,
            min(self.dialog_threshold, 0.60),
            REGION_WIDE_TOP,
        )

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
        title_match = self.vision.match_best_in_region(
            screenshot,
            SP_JOIN_TITLES,
            SP_JOIN_THRESHOLD,
            REGION_WIDE_TOP,
        )
        belong_matches = self.vision.match_all_in_region(
            screenshot,
            SP_JOIN_BELONG_MARKERS,
            threshold=SP_BELONG_THRESHOLD,
            region=REGION_CENTER,
            max_matches=20,
        )
        if join_match and title_match:
            return self._pick_best_match(join_match, title_match)
        if filter_match and title_match:
            return self._pick_best_match(filter_match, title_match)
        if join_match and belong_matches:
            return join_match
        if filter_match and belong_matches:
            return filter_match
        if title_match and belong_matches:
            return title_match
        return None

    def is_sp_join_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_sp_join_screen_in_screenshot(screenshot)

    def find_final_confirm_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        return self._match_screen_profile(
            screenshot,
            strong_probes=[
                ScreenProbe(tuple(FINAL_CONFIRM_TITLES), min(self.dialog_threshold, 0.60), REGION_WIDE_TOP, allow_fullscreen_fallback=True),
                ScreenProbe(tuple(FINAL_CONFIRM_BUTTONS), min(self.button_threshold, 0.72), REGION_BOTTOM_RIGHT),
            ],
            min_strong=2,
        )

    def is_final_confirm_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_final_confirm_screen_in_screenshot(screenshot)

    def is_login_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_login_screen_in_screenshot(screenshot)

    def find_login_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        return self._match_screen_profile(
            screenshot,
            strong_probes=[
                ScreenProbe(tuple(LOGIN_SCREEN_LOGO_MARKERS), LOGIN_SCREEN_THRESHOLD, REGION_TOP_LEFT),
                ScreenProbe(tuple(LOGIN_SCREEN_FULL_MARKERS), min(LOGIN_SCREEN_THRESHOLD, 0.50), REGION_FULL),
            ],
            min_strong=1,
        )

    def is_game_main_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_game_main_screen_in_screenshot(screenshot)

    def find_game_main_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        return self._match_screen_profile(
            screenshot,
            strong_probes=[
                ScreenProbe(tuple(GAME_MAIN_CREATE_ENTRANCES), GAME_MAIN_ENTRANCE_THRESHOLD, REGION_BOTTOM_RIGHT),
                ScreenProbe(tuple(GAME_MAIN_MARKERS), GAME_MAIN_MARK_THRESHOLD, REGION_TOP_LEFT),
            ],
            support_probes=[
                ScreenProbe(tuple(GAME_MAIN_SCREEN_MARKERS), min(self.dialog_threshold, 0.45), REGION_FULL),
            ],
            min_strong=1,
        )

    def find_game_main_entrance_in_screenshot(self, screenshot: np.ndarray, threshold: float | None = None) -> MatchResult | None:
        return self.vision.match_best_in_region(
            screenshot,
            GAME_MAIN_CREATE_ENTRANCES,
            GAME_MAIN_ENTRANCE_THRESHOLD if threshold is None else threshold,
            REGION_BOTTOM_RIGHT,
        )

    def is_save_selection_screen(self) -> MatchResult | None:
        screenshot = self.vision.capture()
        return self.find_save_selection_screen_in_screenshot(screenshot)

    def find_save_selection_screen_in_screenshot(self, screenshot: np.ndarray) -> MatchResult | None:
        title = self.vision.match_best_in_region(
            screenshot,
            SAVE_SELECTION_TITLE_MARKERS,
            min(self.dialog_threshold, 0.58),
            REGION_TOP_CENTER,
        )
        screen = self.vision.match_best(
            screenshot,
            SAVE_SELECTION_MARKERS,
            min(self.dialog_threshold, 0.45),
        )
        back_button = self.vision.match_best_in_region(
            screenshot,
            BACK_BUTTONS,
            min(self.button_threshold, 0.72),
            REGION_TOP_LEFT,
        )
        if title and screen:
            return self._pick_best_match(title, screen)
        if self.awaiting_save_selection and (title or screen or back_button):
            return title or screen or back_button
        if title and back_button:
            return title
        return title or screen

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
                ("login_screen", self.find_login_screen_in_screenshot),
                ("game_main", self.find_game_main_screen_in_screenshot),
                ("save_selection", self.find_save_selection_screen_in_screenshot),
                ("creative_mode_main", self.find_main_screen_in_screenshot),
            ],
            "main": [
                ("creative_mode_main", self.find_main_screen_in_screenshot),
                ("special_training", self.find_special_training_screen_in_screenshot),
                ("match_reward", self.find_match_reward_screen_in_screenshot),
                ("league_result", lambda shot: self.vision.match_best_in_region(shot, LEAGUE_RESULT_TITLES, 0.70, REGION_WIDE_TOP)),
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

        if self.vision.match_best_in_region(screenshot, LEAGUE_RESULT_TITLES, threshold=0.70, region=REGION_WIDE_TOP):
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
            if force or self.active_flow == "recovery" or now - self.last_full_stage_scan_time >= FULL_STAGE_SCAN_INTERVAL_SECONDS:
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
            if rect["width"] != EXPECTED_CLIENT_WIDTH or rect["height"] != EXPECTED_CLIENT_HEIGHT:
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
        if stage != "unknown" and stage_stuck_seconds >= SCREEN_STUCK_TIMEOUT_SECONDS:
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
            if rect["width"] != EXPECTED_CLIENT_WIDTH or rect["height"] != EXPECTED_CLIENT_HEIGHT:
                self.request_restart(
                    f"unexpected resolution {rect['width']}x{rect['height']} (expected {EXPECTED_CLIENT_WIDTH}x{EXPECTED_CLIENT_HEIGHT})"
                )
                return False
        except Exception as exc:
            logging.debug("Resolution check failed during process-only health check: %s", exc)
        return True

    def detect_new_season_step_in_screenshot(self, screenshot: np.ndarray) -> str | None:
        if self.find_club_transfers_level_screen_in_screenshot(screenshot) or self.find_club_transfers_level_title_in_screenshot(screenshot):
            return "club_transfers_level"
        if self.find_club_transfers_screen_in_screenshot(screenshot):
            return "club_transfers"
        if self.find_sp_join_screen_in_screenshot(screenshot):
            return "sp_join"
        if self.find_final_confirm_screen_in_screenshot(screenshot):
            return "final_confirm"
        return None

    def _handle_global_priority_buttons_from_screenshot(self, screenshot: np.ndarray, priority_threshold: float) -> bool:
        new_season_step = self.detect_new_season_step_in_screenshot(screenshot)
        if new_season_step:
            logging.info(
                "New-season step %s detected during global priority handling, deferring confirm buttons to the dedicated flow",
                new_season_step,
            )
            return False

        confirm_button = self.vision.match_best(screenshot, CONFIRM_BUTTONS, priority_threshold)
        if confirm_button:
            logging.info(
                "Confirm button detected before event-choice handling: %s (score=%.3f)",
                confirm_button.name,
                confirm_button.score,
            )
            self.click_match(confirm_button, settle=0.2)
            return True

        event_choice = self.find_event_choice_in_screenshot(screenshot)
        if event_choice:
            logging.info(
                "Event choice screen detected via %s (score=%.3f), selecting the first option before any skip handling",
                event_choice.name,
                event_choice.score,
            )
            self.click_event_log_first_option(settle=0.15)
            self.rapidly_advance_event_story(attempts=4, settle=0.08)
            return True

        match = self.vision.match_best(screenshot, PRIORITY1_BUTTONS, priority_threshold)
        if match:
            logging.info("Priority-1 button detected: %s (score=%.3f)", match.name, match.score)
            settle = 0.2 if match.name in {"login_retry", "match_result_button", "continue_button", "ok_button", "skip_button", "skip_button2"} else 0.4
            self.click_match(match, settle=settle)
            if match.name in {"skip_button", "skip_button2"}:
                logging.info("Skip button came through global priority handling, rapidly advancing the event/story afterwards")
                self.rapidly_advance_event_story(attempts=5, settle=0.08)
            return True

        followup_button = self.vision.match_best(screenshot, PRIORITY1_FOLLOWUP_BUTTONS, priority_threshold)
        if followup_button:
            if self.is_match_reward_screen():
                logging.info("Continue button detected on match reward screen, ensuring 3x speed first")
                if self.ensure_speed_three():
                    return True
            logging.info("Priority-1 follow-up button detected: %s (score=%.3f)", followup_button.name, followup_button.score)
            self.click_match(followup_button, settle=0.2)
            return True

        match = self.vision.match_best(screenshot, PRIORITY2_BUTTONS, priority_threshold)
        if not match:
            return False

        if match.name in {"final_confirm_ok_button", "final_confirm_ok_button2", "ok_chs_button"}:
            level_screen = self.vision.match_best(
                screenshot,
                CLUB_TRANSFERS_LEVEL_TITLES,
                max(min(self.dialog_threshold, 0.72), 0.78),
            )
            min_button = self.vision.match_best(
                screenshot,
                ["club_transfers_min_button"],
                max(min(self.button_threshold, 0.72), 0.82),
            )
            if level_screen and min_button:
                logging.info(
                    "Priority-2 confirm %s detected on club transfers level screen, selecting minimum difficulty first",
                    match.name,
                )
                self.click_match(min_button, settle=0.3)
                screenshot = self.vision.capture()
                refreshed_confirm = self.vision.match_best(screenshot, PRIORITY2_BUTTONS, priority_threshold)
                if not refreshed_confirm:
                    logging.warning("Confirm button disappeared after selecting minimum difficulty")
                    return True
                match = refreshed_confirm

        logging.info("Priority-2 button detected: %s (score=%.3f)", match.name, match.score)
        self.click_match(match, settle=0.2)
        return True

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
        logging.info("Clicking the first option on event_log_choose screen")
        self.window.click_client(
            int(EXPECTED_CLIENT_WIDTH * 0.34),
            int(EXPECTED_CLIENT_HEIGHT * 0.27),
            settle=settle,
        )

    def rapidly_advance_event_story(self, attempts: int = 5, settle: float = 0.1) -> bool:
        for rapid_click in range(1, attempts + 1):
            if self.is_main_screen():
                logging.info("Event flow finished and main screen returned")
                return True
            logging.info("Rapid story left click %s/%s", rapid_click, attempts)
            self.window.click_client_center(settle=settle)
        if self.is_main_screen():
            logging.info("Event flow finished and main screen returned")
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

    def handle_fast_main_screen_interrupts(self) -> bool:
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
    ) -> bool:
        screenshot = self.vision.capture()
        if not self.is_confirmed_main_screen(screenshot):
            logging.warning("Skipping advance schedule action because the current screen is not a confirmed creative mode main screen")
            return False

        if match:
            logging.info(
                "Executing advance schedule action with a single click on matched target %s at (%s,%s)",
                match.name,
                match.center[0],
                match.center[1],
            )
            self.click_match(match, settle=settle_between)
            return True

        logging.info("Executing advance schedule action with a single click on schedule-card hotspot #%s", hotspot_variant + 1)
        self.click_main_screen_schedule_hotspot(variant=hotspot_variant, settle=settle_between)
        return True

    def poll_until_main_screen_returns(self, max_wait_seconds: float) -> bool:
        logging.info("Waiting for creative mode main screen to return")
        deadline = time.time() + max_wait_seconds
        while time.time() < deadline:
            if self.handle_global_priority_buttons():
                continue
            if not self.check_runtime_health():
                return False

            screenshot = self.vision.capture()
            if self.is_main_screen_returned_quickly(screenshot) or self.should_trust_main_screen(screenshot):
                logging.info("Returned to creative mode main screen")
                return True

            if (
                self.find_login_screen_in_screenshot(screenshot)
                or self.find_game_main_screen_in_screenshot(screenshot)
                or self.find_save_selection_screen_in_screenshot(screenshot)
            ):
                logging.info("Wait-for-main detected bootstrap stage, switching to bootstrap flow immediately")
                return self.run_bootstrap_flow()

            if self.handle_global_priority_buttons():
                continue

            if self.handle_post_schedule_events(max_clicks=12):
                continue

            if self.handle_league_result_screen():
                continue

            if self.handle_connecting_screen():
                continue

            if self.handle_speed_one_anywhere():
                continue

            if self.handle_match_reward_screen():
                continue

            if self.run_new_season_flow():
                continue

            if self.handle_generic_confirm_fallback(min_interval=0.8):
                continue

            if not self.find_any_known_operation():
                self.fallback_click_when_no_operation_found()
                continue

            time.sleep(0.2)

        self.vision.save_debug_screenshot("wait_main_screen_timeout")
        logging.warning("Timed out waiting for creative mode main screen to return")
        return False

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
                logging.info("event_log_choose detected, selecting the first option on attempt %s", attempt)
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

            title = self.vision.wait_for_any(LEAGUE_RESULT_TITLES, threshold=threshold, timeout=0.25, interval=0.1)
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
        return self._match_screen_profile(
            screenshot,
            strong_probes=[
                ScreenProbe(tuple(MATCH_REWARD_TITLES), min(self.dialog_threshold, 0.60), REGION_WIDE_TOP),
                ScreenProbe(tuple(MATCH_REWARD_MARKERS), min(self.dialog_threshold, 0.60), REGION_CENTER),
                ScreenProbe(tuple(MATCH_REWARD_SCREENS), min(self.dialog_threshold, 0.45), REGION_FULL),
            ],
            min_strong=1,
        )

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
            ["continue_button", "ok_button", "ok_chs_button"],
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
        self.last_bootstrap_login_click_time = 0.0
        return True

    def run_bootstrap_flow(self, timeout_seconds: float = BOOTSTRAP_TIMEOUT_SECONDS) -> bool:
        self.set_active_flow("bootstrap")
        logging.info("Running bootstrap flow to reach creative mode save entry")
        deadline = time.time() + timeout_seconds
        last_unknown_click_time = 0.0
        while time.time() < deadline:
            if not self.check_runtime_health():
                return False
            screenshot = self.vision.capture()
            post_login_wait = (
                time.time() - self.last_bootstrap_login_click_time
                if self.last_bootstrap_login_click_time > 0
                else 0.0
            )
            login_cooldown_active = 0.0 < post_login_wait < BOOTSTRAP_POST_LOGIN_GAME_MAIN_SECONDS
            if self.handle_global_priority_buttons(max_clicks=1, initial_screenshot=screenshot):
                continue

            if self.find_main_screen_in_screenshot(screenshot):
                self.set_active_flow("main")
                self.awaiting_save_selection = False
                self.last_bootstrap_login_click_time = 0.0
                logging.info("Bootstrap flow reached creative mode main screen")
                return True

            game_main = self.find_game_main_screen_in_screenshot(screenshot)
            if game_main:
                logging.info("Game main screen detected, entering creative mode")
                entrance = self.find_game_main_entrance_in_screenshot(screenshot) or self.vision.wait_for_any(
                    GAME_MAIN_CREATE_ENTRANCES,
                    GAME_MAIN_ENTRANCE_THRESHOLD,
                    timeout=2.0,
                    interval=0.2,
                )
                if not entrance:
                    logging.warning("Creative mode entrance not found on game main screen")
                else:
                    logging.info("Creative mode entrance matched: %s (score=%.3f)", entrance.name, entrance.score)
                    self.click_match(entrance, settle=0.8)
                    self.awaiting_save_selection = True
                    self.last_bootstrap_login_click_time = 0.0
                time.sleep(0.8)
                continue

            if login_cooldown_active:
                entrance = self.find_game_main_entrance_in_screenshot(
                    screenshot,
                    threshold=min(GAME_MAIN_ENTRANCE_THRESHOLD, 0.58),
                )
                if entrance:
                    logging.info(
                        "Within %.0fs post-login cooldown, creative mode entrance matched early: %s (score=%.3f)",
                        post_login_wait,
                        entrance.name,
                        entrance.score,
                    )
                    self.click_match(entrance, settle=0.8)
                    self.awaiting_save_selection = True
                    self.last_bootstrap_login_click_time = 0.0
                    time.sleep(0.8)
                    continue

            if self.find_save_selection_screen_in_screenshot(screenshot):
                logging.info("Save selection screen detected, choosing the third save slot")
                self.choose_third_save_slot()
                time.sleep(1.2)
                continue

            login_screen = self.find_login_screen_in_screenshot(screenshot)
            if login_screen:
                if login_cooldown_active:
                    logging.info(
                        "Login screen still visible %.0fs after the last login click, waiting for game main instead of clicking again",
                        post_login_wait,
                    )
                    time.sleep(0.8)
                    continue
                logging.info("Login screen detected, clicking through to game main screen")
                self.window.click_client_center(settle=0.6)
                self.last_bootstrap_login_click_time = time.time()
                time.sleep(0.8)
                continue

            if post_login_wait >= BOOTSTRAP_POST_LOGIN_GAME_MAIN_SECONDS:
                logging.info(
                    "Login click was %.0fs ago, checking game main immediately and probing creative mode entrance early",
                    post_login_wait,
                )
                entrance = self.find_game_main_entrance_in_screenshot(
                    screenshot,
                    threshold=min(GAME_MAIN_ENTRANCE_THRESHOLD, 0.58),
                )
                if entrance:
                    logging.info(
                        "Game main suspected after login wait, creative mode entrance matched early: %s (score=%.3f)",
                        entrance.name,
                        entrance.score,
                    )
                    self.click_match(entrance, settle=0.8)
                    self.awaiting_save_selection = True
                    self.last_bootstrap_login_click_time = 0.0
                    time.sleep(0.8)
                    continue
                logging.info("Post-login wait window expired without a game-main hit, allowing one remedial center click")
                self.window.click_client_center(settle=0.6)
                self.last_bootstrap_login_click_time = time.time()
                time.sleep(0.8)
                continue

            if login_cooldown_active:
                logging.info(
                    "Within %.0fs post-login cooldown, skipping unrelated bootstrap detections while waiting for game main",
                    post_login_wait,
                )
                time.sleep(0.8)
                continue

            if self.run_new_season_flow(screenshot):
                continue

            if self.handle_connecting_screen(max_clicks=3):
                continue

            if self.handle_post_schedule_events(max_clicks=6):
                continue

            stage = self.update_runtime_stage()
            if stage == "unknown":
                now = time.time()
                if now - last_unknown_click_time >= 3.0:
                    logging.info("Bootstrap stage is still unknown, trying a center click to pass startup/login")
                    self.window.click_client_center(settle=1.0)
                    last_unknown_click_time = now
                    continue

            time.sleep(1.0)

        self.vision.save_debug_screenshot("bootstrap_timeout")
        logging.error("Bootstrap flow timed out before reaching creative mode main screen")
        return False

    def run_club_transfers_flow(self, assume_detected: bool = False) -> bool:
        if not self.check_runtime_health():
            return False
        title = True if assume_detected else self.is_club_transfers_screen()
        if not title:
            return self.run_club_transfers_level_flow()

        logging.info("Club transfers screen detected, starting renewal flow")
        renewal = self.click_named_button(CLUB_TRANSFERS_RENEWAL_BUTTONS, timeout=5.0, settle=1.0)
        if not renewal:
            logging.warning("Club transfers renewal button not found")
            return False

        deadline = time.time() + 6.0
        while time.time() < deadline:
            if not self.check_runtime_health():
                return False
            if self.run_club_transfers_level_flow():
                return True
            self.handle_global_priority_buttons(max_clicks=1)
            time.sleep(0.4)
        return True

    def run_club_transfers_level_flow(self, screenshot: np.ndarray | None = None, assume_detected: bool = False) -> bool:
        if not self.check_runtime_health():
            return False
        screenshot = screenshot if screenshot is not None else self.vision.capture()
        level_screen = True if assume_detected else (
            self.find_club_transfers_level_screen_in_screenshot(screenshot) or self.find_club_transfers_level_title_in_screenshot(screenshot)
        )
        if not level_screen:
            return False

        now = time.time()
        if now - self.last_club_transfers_min_click_time >= CLUB_TRANSFERS_MIN_CLICK_COOLDOWN_SECONDS:
            logging.info("Club transfers level screen detected, selecting minimum difficulty")
            min_button = self.find_club_transfers_min_button_in_screenshot(screenshot)
            if min_button:
                logging.info(
                    "Selecting left-most minimum difficulty button at (%s,%s)",
                    min_button.center[0],
                    min_button.center[1],
                )
                self.click_match(min_button, settle=0.4)
            else:
                logging.warning("Club transfers minimum difficulty button not found, using hotspot fallback")
                self.click_club_transfers_min_hotspot(settle=0.4)
            self.last_club_transfers_min_click_time = time.time()
            time.sleep(0.2)
        else:
            logging.info("Club transfers minimum difficulty was clicked recently, waiting for confirm only")

        ok = self.vision.wait_for_any(CONFIRM_BUTTONS, min(self.button_threshold, 0.72), timeout=1.5, interval=0.15)
        if not ok:
            logging.warning("Confirm button not found on club transfers level screen")
            return False

        self.click_match(ok, settle=0.5)
        return True

    def select_sp_join_candidates(self, screenshot: np.ndarray, max_select: int = 3) -> int:
        belong_matches = self.vision.match_all(
            screenshot,
            SP_JOIN_BELONG_MARKERS,
            threshold=SP_BELONG_THRESHOLD,
            max_matches=20,
        )
        logging.info(
            "Detected %s sp_belong markers: %s",
            len(belong_matches),
            [f"({match.center[0]},{match.center[1]},{match.score:.2f})" for match in belong_matches[:10]],
        )
        selected = 0
        for slot_x, slot_y in SP_JOIN_SLOT_CENTERS:
            has_belong = any(
                abs(match.center[0] - slot_x) <= 95 and abs(match.center[1] - (slot_y - 115)) <= 95
                for match in belong_matches
            )
            if has_belong:
                logging.info("Skipping SP slot at (%s, %s) because sp_belong marker is nearby", slot_x, slot_y)
                continue
            self.window.click_client(slot_x, slot_y, settle=0.8)
            selected += 1
            logging.info("Selected SP player slot at (%s, %s), total=%s", slot_x, slot_y, selected)
            if selected >= max_select:
                break
        return selected

    def scroll_sp_join_list_to_bottom(self) -> None:
        rect = self.window.client_rect_screen()
        x = max(1, min(rect["width"] - 1, int(rect["width"] * SP_JOIN_SCROLL_RATIO[0])))
        y = max(1, min(rect["height"] - 1, int(rect["height"] * SP_JOIN_SCROLL_RATIO[1])))
        logging.info(
            "Scrolling SP join list to bottom with %s wheel steps at (%s, %s)",
            SP_JOIN_SCROLL_STEPS_TO_BOTTOM,
            x,
            y,
        )
        for step in range(1, SP_JOIN_SCROLL_STEPS_TO_BOTTOM + 1):
            logging.info("SP join scroll step %s/%s", step, SP_JOIN_SCROLL_STEPS_TO_BOTTOM)
            self.window.scroll_client(x, y, SP_JOIN_SCROLL_DELTA, settle=0.18)

    def apply_sp_join_filter(self) -> bool:
        logging.info("Applying SP join filter before selecting players")
        entrance = self.click_named_button(SP_JOIN_FILTER_ENTRANCES, timeout=5.0, settle=1.0)
        if not entrance:
            logging.warning("SP join filter entrance not found")
            return False

        popup = self.vision.wait_for_any(
            SP_JOIN_FILTER_POPUPS,
            min(self.dialog_threshold, 0.72),
            timeout=4.0,
            interval=0.3,
        )
        if not popup:
            logging.warning("SP join filter popup not found after clicking filter entrance")
            return False

        ok = self.vision.wait_for_any(CONFIRM_BUTTONS, min(self.button_threshold, 0.72), timeout=4.0, interval=0.3)
        if not ok:
            logging.warning("Confirm button not found on SP join filter popup")
            return False

        self.click_match(ok, settle=1.0)
        return True

    def run_sp_join_flow(self, screenshot: np.ndarray | None = None, assume_detected: bool = False) -> bool:
        if not self.check_runtime_health():
            return False
        if not assume_detected and not self.is_sp_join_screen():
            return False

        logging.info("SP join screen detected, applying filter and selecting up to 3 available SP players")
        self.apply_sp_join_filter()
        screenshot = self.vision.capture()
        selected = self.select_sp_join_candidates(screenshot, max_select=3)
        if selected == 0:
            logging.info("No selectable SP players found in the initial view, scrolling to the bottom and retrying")
            self.scroll_sp_join_list_to_bottom()
            screenshot = self.vision.capture()
            selected = self.select_sp_join_candidates(screenshot, max_select=3)
        logging.info("SP player selection finished, selected=%s", selected)

        join_button = self.click_named_button(SP_JOIN_BUTTONS, timeout=5.0, settle=1.0)
        if not join_button:
            logging.warning("SP join button not found")
            return False

        for _ in range(4):
            if not self.handle_global_priority_buttons(max_clicks=1):
                break
        return True

    def run_final_confirm_flow(self, assume_detected: bool = False) -> bool:
        if not self.check_runtime_health():
            return False
        if not assume_detected and not self.is_final_confirm_screen():
            return False

        logging.info("Final confirm screen detected, confirming new season")
        self.window.move_cursor_client(x_ratio=0.08, y_ratio=0.08)
        button = self.click_named_button(FINAL_CONFIRM_BUTTONS, timeout=5.0, settle=1.0)
        if not button:
            logging.warning("Final confirm button not found, falling back to generic confirm buttons")
            generic_ok = self.vision.wait_for_any(
                CONFIRM_BUTTONS,
                min(self.button_threshold, 0.72),
                timeout=2.5,
                interval=0.2,
            )
            if not generic_ok:
                return False
            self.click_match(generic_ok, settle=0.8)

        self.window.move_cursor_client(x_ratio=0.08, y_ratio=0.08)
        for _ in range(4):
            if not self.handle_global_priority_buttons(max_clicks=1):
                break
        return True

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
        if not self.check_runtime_health():
            return False
        current = screenshot if screenshot is not None else self.vision.capture()
        step = self.detect_new_season_step_in_screenshot(current)
        if step == "club_transfers":
            self.set_active_flow("new_season")
            logging.info("New season flow step: club transfers")
            return self.run_club_transfers_flow(assume_detected=True)

        if step == "club_transfers_level":
            self.set_active_flow("new_season")
            logging.info("New season flow step: club transfers level")
            return self.run_club_transfers_level_flow(screenshot=current, assume_detected=True)

        if step == "sp_join":
            self.set_active_flow("new_season")
            logging.info("New season flow step: SP join")
            return self.run_sp_join_flow(screenshot=current, assume_detected=True)

        if step == "final_confirm":
            self.set_active_flow("new_season")
            logging.info("New season flow step: final confirm")
            return self.run_final_confirm_flow(assume_detected=True)

        return False

    def recover_to_main_screen(self, timeout_seconds: float = STARTUP_RECOVERY_SECONDS) -> bool:
        screenshot = self.vision.capture()
        if self.should_trust_main_screen(screenshot):
            self.set_active_flow("main")
            logging.info("Skipping recovery because creative mode main screen is still within the trust window")
            return True

        self.set_active_flow("recovery")
        logging.info("Current screen is not the creative mode main screen, attempting recovery")
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if not self.check_runtime_health():
                return False
            screenshot = self.vision.capture()
            trusted_main = self.should_trust_main_screen(screenshot)

            if self.handle_global_priority_buttons(max_clicks=1, initial_screenshot=screenshot):
                continue

            if self.find_main_screen_in_screenshot(screenshot) or trusted_main:
                self.set_active_flow("main")
                if trusted_main and not self.find_main_screen_in_screenshot(screenshot):
                    logging.info("Recovery trusted creative mode main screen based on recent stage confirmation")
                else:
                    logging.info("Recovery found creative mode main screen")
                return True

            recovery_main_hint = self.find_main_screen_recovery_hint(screenshot)
            if recovery_main_hint and not (
                self.find_special_training_screen_in_screenshot(screenshot)
                or self.find_match_reward_screen_in_screenshot(screenshot)
                or self.find_club_transfers_screen_in_screenshot(screenshot)
                or self.find_club_transfers_level_screen_in_screenshot(screenshot)
                or self.find_sp_join_screen_in_screenshot(screenshot)
                or self.find_final_confirm_screen_in_screenshot(screenshot)
            ):
                self.set_active_flow("main")
                logging.info(
                    "Recovery accepted creative mode main screen via main-action hint %s (score=%.3f)",
                    recovery_main_hint.name,
                    recovery_main_hint.score,
                )
                return True

            if (
                self.find_login_screen_in_screenshot(screenshot)
                or self.find_game_main_screen_in_screenshot(screenshot)
                or self.find_save_selection_screen_in_screenshot(screenshot)
            ):
                if self.run_bootstrap_flow():
                    return True
                continue

            if self.run_new_season_flow(screenshot):
                logging.info("Handled new season flow during recovery")
                return True

            if self.run_back_recovery_flow():
                if self.is_main_screen():
                    self.set_active_flow("main")
                    logging.info("Recovered to creative mode main screen via back-button recovery")
                    return True
                continue

            if self.handle_global_priority_buttons(max_clicks=3):
                if self.is_main_screen():
                    logging.info("Recovered to creative mode main screen via priority button handling")
                    return True
                continue

            if self.handle_post_schedule_events(max_clicks=6):
                if self.is_main_screen():
                    logging.info("Recovered to creative mode main screen via event handling")
                    return True
                continue

            if self.handle_league_result_screen():
                if self.is_main_screen():
                    logging.info("Recovered to creative mode main screen via league-result handling")
                    return True
                continue

            if self.handle_connecting_screen():
                if self.is_main_screen():
                    logging.info("Recovered to creative mode main screen via CONNECTING handling")
                    return True
                continue

            if self.handle_match_reward_screen():
                continue

            main_after_reward = self.find_main_screen_recovery_hint(self.vision.capture())
            if main_after_reward:
                self.set_active_flow("main")
                logging.info(
                    "Recovery accepted creative mode main screen after reward handling via %s (score=%.3f)",
                    main_after_reward.name,
                    main_after_reward.score,
                )
                return True

            if self.handle_speed_one_anywhere():
                refreshed = self.vision.capture()
                if self.find_main_screen_in_screenshot(refreshed) or self.find_main_screen_recovery_hint(refreshed):
                    self.set_active_flow("main")
                    logging.info("Recovery resumed main flow immediately after speed handling on creative mode main screen")
                    return True
                continue

            if self.handle_generic_confirm_fallback(min_interval=0.8):
                refreshed = self.vision.capture()
                if self.find_main_screen_in_screenshot(refreshed) or self.find_main_screen_recovery_hint(refreshed):
                    logging.info("Recovered to creative mode main screen via generic confirm fallback")
                    return True
                continue

            if self.run_back_recovery_flow():
                if self.is_main_screen():
                    logging.info("Recovered to creative mode main screen via back-button recovery")
                    return True
                continue

            main = self.is_main_screen()
            if main:
                self.set_active_flow("main")
                logging.info("Recovered to creative mode main screen")
                return True

            if not self.find_any_known_operation():
                self.fallback_click_when_no_operation_found()
            else:
                time.sleep(1.0)

        self.vision.save_debug_screenshot("recover_main_screen_timeout")
        logging.error("Failed to recover to creative mode main screen within timeout")
        return False

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
            title = self.vision.wait_for_any(
                ["special_training_settings_title"],
                self.dialog_threshold,
                timeout=1.5,
                interval=0.2,
            )
            if title:
                logging.info("Entered special training settings")
                return True
        logging.info("No settings screen after two clicks, treating this as no-op")
        return False

    def try_enter_special_training_fast(self) -> bool:
        for attempt in range(1, 3):
            if not self.check_runtime_process_only():
                return False
            screenshot = self.vision.capture()
            if not self.is_confirmed_main_screen(screenshot):
                logging.info("Fast path skipped special training entry because the current screen is not a confirmed creative mode main screen")
                return False
            match = self.find_special_training_entry_on_main_screen(screenshot)
            if not match:
                logging.info("Fast path using special training hotspot fallback on attempt %s", attempt)
                self.click_main_screen_special_training_hotspot(settle=0.5)
            else:
                logging.info("Fast path entering special training, attempt %s", attempt)
                self.click_match(match, settle=0.5)
            title = self.wait_for_any_in_region(
                ["special_training_settings_title"],
                self.dialog_threshold,
                REGION_WIDE_TOP,
                timeout=0.7,
                interval=0.12,
            )
            if title:
                logging.info("Entered special training settings via fast path")
                return True
        logging.info("Fast path did not confirm special training settings after two attempts")
        return False

    def handle_confirm_dialog(self, dialog_name: str) -> bool:
        confirm_threshold = min(self.dialog_threshold, self.button_threshold, 0.72)
        trigger = self.vision.wait_for_any([dialog_name, *CONFIRM_BUTTONS], confirm_threshold, timeout=4.0, interval=0.3)
        if not trigger:
            logging.warning("Neither confirm dialog nor Ok button was detected: %s", dialog_name)
            return False
        logging.info("Confirm trigger detected: %s (score=%.3f)", trigger.name, trigger.score)
        ok = self.vision.wait_for_any(CONFIRM_BUTTONS, confirm_threshold, timeout=4.0, interval=0.3)
        if not ok:
            logging.warning("Confirm dialog detected, but Ok button was not found")
            return False
        self.click_match(ok, settle=1.0)
        return True

    def handle_optional_confirm_dialog(self, dialog_name: str) -> bool:
        confirm_threshold = min(self.dialog_threshold, self.button_threshold, 0.72)
        trigger = self.vision.wait_for_any([dialog_name, *CONFIRM_BUTTONS], confirm_threshold, timeout=2.0, interval=0.3)
        if not trigger:
            logging.debug("Optional confirm dialog not detected: %s", dialog_name)
            return False
        logging.info("Optional confirm trigger detected: %s (score=%.3f)", trigger.name, trigger.score)
        ok = self.vision.wait_for_any(CONFIRM_BUTTONS, confirm_threshold, timeout=3.0, interval=0.3)
        if not ok:
            logging.warning("Optional confirm dialog detected, but Ok button was not found")
            return False
        self.click_match(ok, settle=1.0)
        return True

    def handle_confirm_dialog_fast(self, dialog_name: str) -> bool:
        confirm_threshold = min(self.dialog_threshold, self.button_threshold, 0.72)
        trigger = self.vision.wait_for_any([dialog_name, *CONFIRM_BUTTONS], confirm_threshold, timeout=1.2, interval=0.12)
        if not trigger:
            logging.debug("Fast confirm dialog not detected: %s", dialog_name)
            return False
        ok = self.vision.wait_for_any(CONFIRM_BUTTONS, confirm_threshold, timeout=1.2, interval=0.12)
        if not ok:
            logging.warning("Fast confirm dialog detected, but Ok button was not found: %s", dialog_name)
            return False
        self.click_match(ok, settle=0.4)
        return True

    def handle_optional_confirm_dialog_fast(self, dialog_name: str) -> bool:
        confirm_threshold = min(self.dialog_threshold, self.button_threshold, 0.72)
        trigger = self.vision.wait_for_any([dialog_name, *CONFIRM_BUTTONS], confirm_threshold, timeout=0.9, interval=0.12)
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
            self.handle_optional_confirm_dialog("special_training_execute_confirm_next_dialog")
            self.handle_optional_confirm_dialog("special_training_execute_confirm_dialog")

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
            self.handle_optional_confirm_dialog_fast("special_training_execute_confirm_next_dialog")
            self.handle_optional_confirm_dialog_fast("special_training_execute_confirm_dialog")

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
        if not self.check_runtime_health():
            return False
        if not self.is_special_training_screen() and not self.try_enter_special_training():
            return False

        reset_match = self.click_named_button(SPECIAL_TRAINING_RESET_BUTTONS, timeout=5.0, settle=1.0)
        if reset_match:
            self.handle_confirm_dialog("special_training_reset_all_confirm_dialog")
        else:
            logging.info("Reset-all button not found, continuing")

        recommend_match = self.click_named_button(SPECIAL_TRAINING_RECOMMEND_BUTTONS, timeout=5.0, settle=1.0)
        if not recommend_match:
            logging.warning("Recommend button not found")

        execute_match = self.click_named_button(SPECIAL_TRAINING_EXECUTE_BUTTONS, timeout=5.0, settle=1.0)
        if execute_match:
            self.handle_confirm_dialog("special_training_execute_confirm_dialog")
            self.handle_optional_confirm_dialog("special_training_execute_confirm_next_dialog")
        else:
            logging.warning("Execute training button not found")

        self.leave_special_training()
        self.last_special_training_run_time = time.time()
        return True

    def run_special_training_flow_fast(self) -> bool:
        if not self.check_runtime_process_only():
            return False
        if not self.is_special_training_screen() and not self.try_enter_special_training_fast():
            return False

        reset_match = self.click_special_training_action_fast(
            SPECIAL_TRAINING_RESET_BUTTONS,
            timeout=0.9,
            settle=0.35,
        )
        if reset_match:
            self.handle_confirm_dialog_fast("special_training_reset_all_confirm_dialog")

        self.click_special_training_action_fast(
            SPECIAL_TRAINING_RECOMMEND_BUTTONS,
            timeout=0.9,
            settle=0.35,
        )

        execute_match = self.click_special_training_action_fast(
            SPECIAL_TRAINING_EXECUTE_BUTTONS,
            timeout=0.9,
            settle=0.35,
        )
        if execute_match:
            self.handle_confirm_dialog_fast("special_training_execute_confirm_dialog")
            self.handle_optional_confirm_dialog_fast("special_training_execute_confirm_next_dialog")

        self.leave_special_training_fast()
        self.last_special_training_run_time = time.time()
        return True

    def advance_schedule(self, max_wait_seconds: float) -> bool:
        left_main_screen = False
        for attempt in range(1, 9):
            if not self.check_runtime_health():
                return False
            self.handle_global_priority_buttons()
            screenshot = self.vision.capture()
            if not self.is_confirmed_main_screen(screenshot):
                logging.warning("Advance schedule aborted because the current screen is not a confirmed creative mode main screen")
                return False
            match = self.find_advance_schedule_button_in_screenshot(screenshot)
            action_clicked = False
            if not match:
                match = self.click_named_button_in_region(
                    MAIN_SCREEN_BUTTONS,
                    min(self.main_threshold, 0.55),
                    REGION_BOTTOM_RIGHT,
                    timeout=1.5,
                    interval=0.12,
                    settle=0.5,
                )
                if match:
                    action_clicked = True
            if not match:
                logging.warning("Advance schedule button not found in dedicated schedule ROI, using main-screen schedule hotspot fallback")
                action_clicked = self.click_advance_schedule_action(
                    match=None,
                    hotspot_variant=(attempt - 1) % len(MAIN_SCREEN_SCHEDULE_RATIOS),
                    settle_between=0.16,
                )
            else:
                logging.info("Advance schedule matched via template: %s (score=%.3f)", match.name, match.score)
                action_clicked = self.click_advance_schedule_action(match=match, settle_between=0.16)
            if not action_clicked:
                logging.warning("Advance schedule action was skipped, aborting the current advance attempt")
                return False
            self.last_advance_schedule_click_time = time.time()
            time.sleep(0.4)

            self.handle_global_priority_buttons()
            self.handle_post_schedule_events(max_clicks=8)
            if self.is_main_screen():
                logging.warning("Advance schedule click did not leave main screen, retrying (attempt %s)", attempt)
                continue

            logging.info("Advance schedule accepted, main screen has been left")
            left_main_screen = True
            break

        if not left_main_screen:
            self.vision.save_debug_screenshot("advance_schedule_leave_failed")
            logging.error("Advance schedule failed to leave main screen after repeated clicks")
            return False

        return self.poll_until_main_screen_returns(max_wait_seconds)

    def handle_post_schedule_events_fast(self, max_clicks: int = 6) -> bool:
        handled = False
        for attempt in range(1, max_clicks + 1):
            if not self.check_runtime_process_only():
                return handled

            screenshot = self.vision.capture()
            confirm_button = self.vision.match_best(screenshot, CONFIRM_BUTTONS, min(self.button_threshold, 0.72))
            if confirm_button:
                handled = True
                logging.info("Fast post-schedule confirm detected on attempt %s", attempt)
                self.click_match(confirm_button, settle=0.2)
                continue

            continue_button = self.vision.match_best(screenshot, ["continue_button"], min(self.button_threshold, 0.72))
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
                continue

            return handled

        return handled

    def advance_schedule_fast(self, max_wait_seconds: float) -> bool:
        left_main_screen = False
        for attempt in range(1, 5):
            if not self.check_runtime_process_only():
                return False
            if self.handle_fast_main_screen_interrupts():
                continue

            screenshot = self.vision.capture()
            if not self.is_confirmed_main_screen(screenshot):
                logging.warning("Fast advance schedule aborted because the current screen is not a confirmed creative mode main screen")
                return False
            match = self.find_advance_schedule_button_in_screenshot(screenshot)
            action_clicked = False
            if not match:
                match = self.click_named_button_in_region(
                    MAIN_SCREEN_BUTTONS,
                    min(self.main_threshold, 0.55),
                    REGION_BOTTOM_RIGHT,
                    timeout=0.8,
                    interval=0.10,
                    settle=0.45,
                )
                if match:
                    action_clicked = True
                if not match:
                    logging.warning("Fast path could not find advance schedule template in dedicated schedule ROI, using schedule hotspot fallback")
                    action_clicked = self.click_advance_schedule_action(
                        match=None,
                        hotspot_variant=(attempt - 1) % len(MAIN_SCREEN_SCHEDULE_RATIOS),
                        settle_between=0.14,
                    )
                else:
                    logging.info("Fast path matched advance schedule via dedicated ROI template: %s (score=%.3f)", match.name, match.score)
            else:
                logging.info("Fast path matched advance schedule via dedicated ROI template: %s (score=%.3f)", match.name, match.score)
                action_clicked = self.click_advance_schedule_action(match=match, settle_between=0.14)

            if not action_clicked:
                logging.warning("Fast advance schedule action was skipped, aborting the current advance attempt")
                return False

            self.last_advance_schedule_click_time = time.time()
            time.sleep(0.35)

            self.handle_post_schedule_events_fast(max_clicks=4)

            if self.is_main_screen_visible():
                logging.warning("Fast advance schedule click did not leave main screen, retrying (attempt %s)", attempt)
                continue

            logging.info("Fast advance schedule accepted, main screen has been left")
            left_main_screen = True
            break

        if not left_main_screen:
            self.vision.save_debug_screenshot("advance_schedule_fast_leave_failed")
            logging.error("Fast advance schedule failed to leave main screen")
            return False

        return self.poll_until_main_screen_returns(max_wait_seconds)

    def fast_main_screen_flow(self, max_wait_seconds: float, screenshot: np.ndarray | None = None) -> bool:
        self.set_active_flow("main")
        if not self.check_runtime_process_only():
            return False

        screenshot = screenshot if screenshot is not None else self.vision.capture()
        if not self.find_main_screen_in_screenshot(screenshot) and not self.should_trust_main_screen(screenshot):
            return False

        logging.info("Fast main-screen flow engaged")

        if self.handle_fast_main_screen_interrupts():
            return True

        self.ensure_speed_three()
        if not self.run_special_training_flow_fast():
            logging.info("Fast path skipped or missed special training, continuing to schedule advance")
        return self.advance_schedule_fast(max_wait_seconds)

    def run_once(self, max_wait_seconds: float) -> bool:
        self.set_active_flow("generic")
        initial_screenshot: np.ndarray | None = None
        if self.check_runtime_process_only():
            initial_screenshot = self.vision.capture()
            new_season_step = self.detect_new_season_step_in_screenshot(initial_screenshot)
            if new_season_step:
                self.set_active_flow("new_season")
                logging.info("Loop start is already on new-season step: %s", new_season_step)
                return self.run_new_season_flow(initial_screenshot)
            priority_threshold = min(self.button_threshold, 0.72)
            if self._handle_global_priority_buttons_from_screenshot(initial_screenshot, priority_threshold):
                return True
            main = self.find_main_screen_in_screenshot(initial_screenshot)
            if not main and self.should_trust_main_screen(initial_screenshot):
                logging.info("Creative mode main screen trusted at loop start despite a transient detection miss")
                main = MatchResult("creative_mode_main_trusted", 1.0, 0, 0, 1, 1)
            if main:
                logging.info("Current stage: creative mode main screen")
                if self.fast_main_screen_flow(max_wait_seconds, screenshot=initial_screenshot):
                    return True
                logging.info("Fast main-screen flow fell back to the standard main-screen flow")
                self.ensure_speed_three()
                self.run_special_training_flow()
                return self.advance_schedule(max_wait_seconds)
            level_title = self.find_club_transfers_level_title_in_screenshot(initial_screenshot)
            if level_title:
                self.set_active_flow("new_season")
                logging.info("Club transfers level screen detected at loop start, prioritizing dedicated new-season flow")
                return self.run_club_transfers_level_flow()
        if initial_screenshot is None and self.handle_global_priority_buttons(initial_screenshot=initial_screenshot):
            return True
        if not self.check_runtime_health():
            return False
        self.handle_global_priority_buttons()
        self.handle_speed_one_anywhere()

        screenshot = self.vision.capture()
        if (
            self.find_login_screen_in_screenshot(screenshot)
            or self.find_game_main_screen_in_screenshot(screenshot)
            or self.find_save_selection_screen_in_screenshot(screenshot)
        ):
            logging.info("Current stage belongs to bootstrap flow, handling startup navigation immediately")
            return self.run_bootstrap_flow()
        main = self.find_main_screen_in_screenshot(screenshot)
        if not main and self.should_trust_main_screen(screenshot):
            logging.info("Creative mode main screen trusted despite a transient detection miss")
            main = MatchResult("creative_mode_main_trusted", 1.0, 0, 0, 1, 1)
        if main:
            logging.info("Current stage: creative mode main screen")
            if self.fast_main_screen_flow(max_wait_seconds, screenshot=screenshot):
                return True
            logging.info("Fast main-screen flow fell back to the standard main-screen flow")
            self.ensure_speed_three()
            self.run_special_training_flow()
            return self.advance_schedule(max_wait_seconds)

        if self.find_special_training_screen_in_screenshot(screenshot):
            self.set_active_flow("main")
            logging.info("Current stage: special training screen, continuing that flow directly")
            return self.run_special_training_flow_fast()

        if self.run_new_season_flow(screenshot):
            return True

        if not self.recover_to_main_screen():
            self.fallback_click_when_no_operation_found()
            self.vision.save_debug_screenshot("not_on_main_screen")
            logging.error("Current screen is not the creative mode main screen")
            return False

        logging.info("Recovery returned to creative mode main screen, starting season flow")
        if self.fast_main_screen_flow(max_wait_seconds):
            return True
        logging.info("Fast main-screen flow failed after recovery, using the standard main-screen flow")
        self.ensure_speed_three()
        self.run_special_training_flow()
        return self.advance_schedule(max_wait_seconds)


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

    required_templates = [
        "close_button",
        "match_result_button",
        "continue_button",
        "assistant",
        "log",
        "event_log_choose",
        "event_choose_mark",
        "skip_button",
        "skip_button2",
        "login_retry",
        "connecting_indicator",
        "connecting_indicator2",
        "league_result_title",
        "league_result_continue_button",
        "match_reward_title",
        "match_reward_mark",
        "match_reward_screen",
        "match_reward_speed1",
        "login_screen_full",
        "login_mark",
        "game_main_screen",
        "game_main_mark",
        "game_main_create_entrance",
        "game_main_create_entrance2",
        "save_selection",
        "save_selection_title",
        "club_transfers_screen",
        "club_transfers_title",
        "club_transfers_lv_title",
        "club_transfers_lv_screen",
        "club_transfers_renewal_button",
        "club_transfers_renewal_button_2",
        "club_transfers_min_button",
        "sp_join_title",
        "sp_join_screen",
        "sp_join_filter_entrance",
        "sp_join_filter_popup",
        "sp_belong",
        "sp_join_button1",
        "sp_join_button2",
        "sp_join_button3",
        "sp_join_button4",
        "final_confirm_title",
        "final_confirm_screen",
        "final_confirm_ok_button",
        "final_confirm_ok_button2",
        "creative_mode_advance_schedule_button_small",
        "creative_mode_advance_schedule_button",
        "creative_mode_advance_schedule_button2",
        "creative_mode_speed1",
        "creative_mode_speed3",
        "creative_mode_speed_popup",
        "creative_mode_special_training_button",
        "creative_mode_special_training_button2",
        "creative_mode_special_training_button3",
        "special_training_settings_title",
        "special_training_reset_all_button",
        "special_training_reset_all_button2",
        "special_training_reset_all_confirm_dialog",
        "special_training_recommend_button",
        "special_training_recommend_button2",
        "special_training_execute_button",
        "special_training_execute_button2",
        "special_training_execute_confirm_dialog",
        "special_training_execute_confirm_next_dialog",
        "ok_button",
        "ok_chs_button",
        "back_button",
        "back",
    ]

    try:
        templates = TemplateStore(TEMPLATE_DIR)
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
        while True:
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
            iteration += 1
            time.sleep(max(0.5, args.loop_interval))
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
