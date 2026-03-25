#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import ctypes
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if os.name == "nt":
    venv_site_packages = BASE_DIR / ".venv" / "Lib" / "site-packages"
    venv_dll_dir = venv_site_packages / "cv2"
    if venv_site_packages.exists() and str(venv_site_packages) not in sys.path:
        sys.path.insert(0, str(venv_site_packages))
    if hasattr(os, "add_dll_directory") and venv_dll_dir.exists():
        os.add_dll_directory(str(venv_dll_dir))

import cv2
import numpy as np
import psutil
import win32api
import win32con
import win32gui
import win32process
import win32ui

# =========================
# 鍩虹閰嶇疆
# =========================
PROCESS_NAME = "FootballClubChampions"
STATUS_FILE = BASE_DIR / "sfcc_status.json"
GAME_EXE_PATH = Path(r"D:\Program Files (x86)\Steam\steamapps\common\SegaFCC\FootballClubChampions.exe")

DEBUG_SAVE = True
DEBUG_ANNOTATE = True
PRINT_BEST_SCORE = True
USE_SCREEN_FALLBACK = True
RESTORE_CURSOR = True
RESTORE_FOREGROUND_WINDOW = False

SCAN_INTERVAL = 0.35
CLICK_COOLDOWN = 1.15
EDGE_CLICK_COOLDOWN = 4.0
POPUP_CLICK_COOLDOWN = 1.5
TEAM_CHANGE_COOLDOWN = 1.8
GAME_LAUNCH_RETRY_SECONDS = 30.0
GAME_STARTUP_WAIT_SECONDS = 25.0
STATUS_WRITE_INTERVAL = 1.0
FLAT_STD_THRESHOLD = 6.0
INVALID_FRAME_RESTART_SECONDS = 8.0
SCALES = [0.72, 0.78, 0.82, 0.88, 0.94, 1.00, 1.06]
ENABLE_EDGE_FALLBACK = False
SCAN_LOG_INTERVAL_SECONDS = 2.0
NO_PROGRESS_RESTART_SECONDS = 30.0
PRACTICE_STALL_RESTART_SECONDS = 120.0

PRACTICE_CLICK_LIMIT = 10000
SHUTDOWN_DELAY_SECONDS = 15
RUNTIME_LOG_DIR = BASE_DIR / "logs"
LOG_CLEANUP_INTERVAL_SECONDS = 3600.0

# =========================
# 瀵艰埅绛栫暐锛堢涓€鎬у師鐞嗭細鐘舵€佹満 + 鍥哄畾鍏ュ彛鐐癸級
# 璇存槑锛氭ā鏉?鏂囧瓧閮戒笉閫傚悎杩欎釜鍔ㄦ€?UI銆傝繘鍏ヨ仈璧涘墠鐨?3 姝ユ湰璐ㄦ槸鏈夐檺鐘舵€佸鑸紝
# 鐩存帴鐐光€滅ǔ瀹氬叆鍙ｅ尯鍩熲€濇瘮缁х画鎶樿吘鏁村崱鐗囨ā鏉挎洿绋炽€?# =========================
BOOT_TEMPLATE_PATH = BASE_DIR / "template_boot_sega2026.png"
WORLD_PREM_TEMPLATE_PATH = BASE_DIR / "template_world_premiership_entry.png"
SAVE_LIST_TEMPLATE_PATH = BASE_DIR / "template_save_list_title.png"
BOOT_THRESHOLD = 0.56
WORLD_PREM_THRESHOLD = 0.56
SAVE_LIST_TITLE_THRESHOLD = 0.62
BOOT_CLICK_RATIO = (0.50, 0.50)
BOOT_WAIT_SECONDS = 30.0
CREATE_CLUB_CLICK_RATIO = (0.955, 0.670)
CREATE_CLUB_CONFIRM_CLICK_RATIO = (0.955, 0.965)
POPUP_ACCEPT_SCORE = 0.52
SAVE_LIST_CARD_CLICK_RATIO = (0.50, 0.42)
SAVE_LIST_CONFIRM_CLICK_RATIO = (0.955, 0.965)
SAVE_LIST_BACK_CLICK_RATIO = (0.03, 0.05)
WORLD_PREM_CLICK_RATIO = (0.455, 0.585)
NAV_CLICK_COOLDOWN = 3.5
NAV_STEP_TIMEOUT = 12.0
DREAM_TEAM_TEMPLATE_PATHS = [
    BASE_DIR / "template_dream_team_mode.png",
    BASE_DIR / "template_dream_team_mode_v2.png",
]
DREAM_TEAM_TEMPLATE_THRESHOLD = 0.58
# Only use the template as a gate inside the upper-card area.
DREAM_TEAM_TEMPLATE_ROI = (0.80, 0.64, 0.99, 0.82)
# Once the upper card is confirmed, click a stable point inside that card
# instead of offsetting from the matched text/logo patch.
DREAM_TEAM_CARD_CLICK_RATIO = (0.955, 0.670)
DREAM_TEAM_SAFE_CLICK_RATIO = DREAM_TEAM_CARD_CLICK_RATIO
DREAM_TEAM_CLICK_RATIO = DREAM_TEAM_SAFE_CLICK_RATIO
HOME_SCENE_DREAM_SCORE = 0.26
ACTION_OVERRIDE_SCORE = 0.68
ACTION_BUTTON_ACCEPT_SCORE = 0.74
LOW_CONF_ACTION_ACCEPT_SCORE = 0.68
BACK_BUTTON_HINT_RATIO = 0.025
HOME_FALLBACK_MAX_ACTION_SCORE = 0.74
HOME_FALLBACK_MAX_BOOT_SCORE = 0.35
SAVE_LIST_ACTION_MAX_SCORE = 0.55

# =========================
# 鍙充笅鍔ㄤ綔鎸夐挳璇嗗埆
# =========================
GLOBAL_ROI = dict(x1=0.60, y1=0.64, x2=1.00, y2=0.98)
BUTTON_CONFIG = {
    "continue": {
        "threshold": 0.66,
        "crop_ratios": [0.70, 0.62, 0.55],
        "zone": (0.78, 0.72, 1.00, 0.98),
        "priority": 1,
        "click_ratio": (0.40, 0.58),
    },
    "practice": {
        "threshold": 0.70,
        "crop_ratios": [0.62, 0.56],
        "zone": (0.78, 0.72, 1.00, 0.98),
        "priority": 2,
        "click_ratio": (0.50, 0.72),
    },
    "view_result": {
        "threshold": 0.66,
        "crop_ratios": [0.62, 0.56],
        "zone": (0.78, 0.72, 1.00, 0.98),
        "priority": 3,
        "click_ratio": (0.50, 0.40),
    },
}

TEMPLATE_PATHS = {
    "continue": BASE_DIR / "template_continue.png",
    "practice": BASE_DIR / "template_practice.png",
    "view_result": BASE_DIR / "template_view_result.png",
}

TEAM_CHANGE_TOP_SCROLL_DRAGS = 3
TEAM_SELECT_FIRST_ROW_CLICK_RATIO = (0.50, 0.36)
TEAM_SELECT_CONFIRM_CLICK_RATIO = (0.92, 0.93)
TEAM_SELECT_OPEN_WAIT_SECONDS = 1.4


class StatusWriter:
    def __init__(self, path: Path):
        self.path = path
        self.last_write = 0.0
        self.data = {
            "ts": time.time(),
            "state": "starting",
            "practice_click_count": 0,
            "last_action": "",
            "last_button": "",
        }

    def update(self, force: bool = False, **kwargs) -> None:
        self.data.update(kwargs)
        self.data["ts"] = time.time()
        now = self.data["ts"]
        if force or now - self.last_write >= STATUS_WRITE_INTERVAL:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)
            self.last_write = now


class RuntimeLogger:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_stamp = stamp
        self.log_path = self.base_dir / f"sfcc_run_{stamp}.log"
        self.latest_path = self.base_dir / "sfcc_latest.log"
        self.snapshot_dir = self.base_dir / f"debug_{stamp}"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.last_cleanup_at = 0.0
        self._write_raw(f"# session_start {stamp}")
        self.maybe_cleanup_old_runs(force=True)

    def _write_raw(self, line: str) -> None:
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        self.latest_path.write_text(self.log_path.name + "\n", encoding="utf-8")

    def log(self, event: str, message: str, **fields) -> None:
        payload = {
            "ts": dt.datetime.now().isoformat(timespec="seconds"),
            "event": event,
            "message": message,
        }
        if fields:
            payload["fields"] = fields
        self._write_raw(json.dumps(payload, ensure_ascii=False))

    def archive_debug_images(self, tag: str) -> None:
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        for src_name in ("last_capture.png", "last_debug.png"):
            src = BASE_DIR / src_name
            if not src.exists():
                continue
            dst = self.snapshot_dir / f"{stamp}_{tag}_{src_name}"
            try:
                dst.write_bytes(src.read_bytes())
            except Exception:
                pass

    def maybe_cleanup_old_runs(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self.last_cleanup_at < LOG_CLEANUP_INTERVAL_SECONDS:
            return

        keep_names = {
            self.log_path.name,
            self.latest_path.name,
            self.snapshot_dir.name,
        }
        for item in self.base_dir.iterdir():
            if item.name in keep_names:
                continue
            try:
                if item.is_dir():
                    for child in item.rglob("*"):
                        if child.is_file():
                            child.unlink(missing_ok=True)
                    for child_dir in sorted((p for p in item.rglob("*") if p.is_dir()), reverse=True):
                        child_dir.rmdir()
                    item.rmdir()
                else:
                    item.unlink(missing_ok=True)
            except Exception:
                pass
        self.last_cleanup_at = now


def enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def find_pid_by_name(process_name: str):
    target = process_name.lower().strip()
    candidates = {target}
    if target.endswith('.exe'):
        candidates.add(target[:-4])
    else:
        candidates.add(target + '.exe')
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            name = (proc.info.get('name') or '').lower().strip()
            if name in candidates:
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None


def kill_process_tree(pid: int) -> None:
    try:
        proc = psutil.Process(pid)
    except psutil.Error:
        return
    children = proc.children(recursive=True)
    for child in children:
        try:
            child.kill()
        except psutil.Error:
            pass
    try:
        proc.kill()
    except psutil.Error:
        pass


def find_main_hwnd_by_pid(pid: int):
    hwnds = []
    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
            return True
        _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
        if window_pid == pid and win32gui.GetWindowText(hwnd).strip():
            hwnds.append(hwnd)
        return True
    win32gui.EnumWindows(callback, None)
    return hwnds[0] if hwnds else None


def bring_window_if_hidden(hwnd: int):
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.3)


def force_foreground_window(hwnd: int):
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.1)
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    except Exception:
        pass

    fg = win32gui.GetForegroundWindow()
    if fg == hwnd:
        return True

    current_tid = win32api.GetCurrentThreadId()
    target_tid = 0
    fg_tid = 0
    try:
        target_tid = win32process.GetWindowThreadProcessId(hwnd)[0]
        fg_tid = win32process.GetWindowThreadProcessId(fg)[0] if fg else 0
        ctypes.windll.user32.AllowSetForegroundWindow(-1)
        if fg_tid:
            ctypes.windll.user32.AttachThreadInput(current_tid, fg_tid, True)
        ctypes.windll.user32.AttachThreadInput(current_tid, target_tid, True)
        win32gui.SetForegroundWindow(hwnd)
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetActiveWindow(hwnd)
        time.sleep(0.05)
    except Exception:
        try:
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.05)
        except Exception:
            pass
    finally:
        try:
            if target_tid:
                ctypes.windll.user32.AttachThreadInput(current_tid, target_tid, False)
        except Exception:
            pass
        try:
            if fg_tid:
                ctypes.windll.user32.AttachThreadInput(current_tid, fg_tid, False)
        except Exception:
            pass
    return win32gui.GetForegroundWindow() == hwnd


def get_client_rect_on_screen(hwnd: int):
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    pt = win32gui.ClientToScreen(hwnd, (0, 0))
    return pt[0], pt[1], pt[0] + (right - left), pt[1] + (bottom - top)


def capture_screen_region(left: int, top: int, width: int, height: int):
    if width <= 0 or height <= 0:
        return None
    screen_dc = win32gui.GetDC(0)
    mfc_dc = win32ui.CreateDCFromHandle(screen_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    save_bitmap = win32ui.CreateBitmap()
    save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
    save_dc.SelectObject(save_bitmap)
    save_dc.BitBlt((0, 0), (width, height), mfc_dc, (left, top), win32con.SRCCOPY)
    bmpinfo = save_bitmap.GetInfo()
    bmpstr = save_bitmap.GetBitmapBits(True)
    img = np.frombuffer(bmpstr, dtype=np.uint8)
    img.shape = (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
    win32gui.DeleteObject(save_bitmap.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(0, screen_dc)
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def frame_looks_invalid(img_bgr):
    if img_bgr is None or img_bgr.size == 0:
        return True
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    std = float(gray.std())
    if std < FLAT_STD_THRESHOLD:
        return True
    white_ratio = float((gray >= 250).mean())
    black_ratio = float((gray <= 5).mean())
    return white_ratio > 0.97 or black_ratio > 0.97


def capture_window_client(hwnd: int):
    left, top, right, bottom = get_client_rect_on_screen(hwnd)
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        return None

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    save_bitmap = win32ui.CreateBitmap()
    save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
    save_dc.SelectObject(save_bitmap)

    PW_CLIENTONLY = 0x00000001
    result = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), PW_CLIENTONLY)
    if result != 1:
        save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

    bmpinfo = save_bitmap.GetInfo()
    bmpstr = save_bitmap.GetBitmapBits(True)
    img = np.frombuffer(bmpstr, dtype=np.uint8)
    img.shape = (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)

    win32gui.DeleteObject(save_bitmap.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwnd_dc)

    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    if USE_SCREEN_FALLBACK and frame_looks_invalid(img):
        fallback = capture_screen_region(left, top, width, height)
        if fallback is not None:
            if frame_looks_invalid(fallback):
                return None
            return fallback
        return None
    return img


def load_template(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"妯℃澘涓嶅瓨鍦? {path}")
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f"鏃犳硶璇诲彇妯℃澘: {path}")
    return img


def preprocess(img_bgr):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    edge = cv2.Canny(gray, 60, 160)
    _, dark_bin = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    return gray, edge, dark_bin


def resize_template_keep_valid(template, scale: float):
    h, w = template.shape[:2]
    nw = max(10, int(w * scale))
    nh = max(10, int(h * scale))
    return cv2.resize(template, (nw, nh), interpolation=cv2.INTER_LINEAR)


def build_template_variants(template_bgr, crop_ratios):
    variants = []
    h = template_bgr.shape[0]
    for ratio in crop_ratios:
        ch = max(16, int(h * ratio))
        variants.append((ratio, template_bgr[:ch, :].copy()))
    return variants


def calc_zone_rect(img_w, img_h, zone):
    x1 = max(0, min(img_w - 1, int(img_w * zone[0])))
    y1 = max(0, min(img_h - 1, int(img_h * zone[1])))
    x2 = max(x1 + 20, min(img_w, int(img_w * zone[2])))
    y2 = max(y1 + 20, min(img_h, int(img_h * zone[3])))
    return x1, y1, x2, y2


def match_variant(scan_img, template_bgr):
    scan_gray, scan_edge, scan_bin = preprocess(scan_img)
    best = {"score": -1.0, "center": None, "scale": None, "top_left": None, "matched_size": None}
    for scale in SCALES:
        tpl = resize_template_keep_valid(template_bgr, scale)
        th, tw = tpl.shape[:2]
        if th >= scan_gray.shape[0] or tw >= scan_gray.shape[1]:
            continue
        tpl_gray, tpl_edge, tpl_bin = preprocess(tpl)
        res_g = cv2.matchTemplate(scan_gray, tpl_gray, cv2.TM_CCOEFF_NORMED)
        _, vg, _, lg = cv2.minMaxLoc(res_g)
        res_e = cv2.matchTemplate(scan_edge, tpl_edge, cv2.TM_CCOEFF_NORMED)
        _, ve, _, le = cv2.minMaxLoc(res_e)
        res_b = cv2.matchTemplate(scan_bin, tpl_bin, cv2.TM_CCOEFF_NORMED)
        _, vb, _, lb = cv2.minMaxLoc(res_b)
        if vb >= vg and vb >= ve:
            score = 0.70 * vb + 0.20 * vg + 0.10 * ve
            loc = lb
        elif vg >= ve:
            score = 0.65 * vg + 0.25 * vb + 0.10 * ve
            loc = lg
        else:
            score = 0.60 * ve + 0.25 * vg + 0.15 * vb
            loc = le
        if score > best["score"]:
            best["score"] = float(score)
            best["center"] = (loc[0] + tw // 2, loc[1] + th // 2)
            best["top_left"] = (loc[0], loc[1])
            best["matched_size"] = (tw, th)
            best["scale"] = scale
    return best


def detect_buttons(img_bgr, templates):
    h, w = img_bgr.shape[:2]
    gx1, gy1, gx2, gy2 = calc_zone_rect(w, h, (GLOBAL_ROI['x1'], GLOBAL_ROI['y1'], GLOBAL_ROI['x2'], GLOBAL_ROI['y2']))
    results = {}
    hits = []
    for name, tpl in templates.items():
        cfg = BUTTON_CONFIG[name]
        zx1, zy1, zx2, zy2 = calc_zone_rect(w, h, cfg['zone'])
        ix1, iy1 = max(gx1, zx1), max(gy1, zy1)
        ix2, iy2 = min(gx2, zx2), min(gy2, zy2)
        if ix2 <= ix1 + 20 or iy2 <= iy1 + 20:
            results[name] = {"found": False, "score": -1.0, "scale": None, "center": None, "crop_ratio": None, "click_point": None}
            continue
        zone_img = img_bgr[iy1:iy2, ix1:ix2]
        best = {"found": False, "score": -1.0, "scale": None, "center": None, "crop_ratio": None, "click_point": None, "top_left": None, "matched_size": None}
        for crop_ratio, variant in build_template_variants(tpl, cfg['crop_ratios']):
            r = match_variant(zone_img, variant)
            if r['score'] > best['score']:
                best.update(r)
                best['crop_ratio'] = crop_ratio
                best['found'] = r['score'] >= cfg['threshold']
        if best['center'] is not None:
            best['center'] = (best['center'][0] + ix1, best['center'][1] + iy1)
        if best['top_left'] is not None and best['scale'] is not None:
            full_h, full_w = tpl.shape[:2]
            scaled_w = max(10, int(full_w * best['scale']))
            scaled_h = max(10, int(full_h * best['scale']))
            click_rx, click_ry = cfg.get('click_ratio', (0.5, 0.72))
            click_x = int(best['top_left'][0] + scaled_w * click_rx) + ix1
            click_y = int(best['top_left'][1] + scaled_h * click_ry) + iy1
            click_x = max(ix1 + 2, min(ix2 - 3, click_x))
            click_y = max(iy1 + 2, min(iy2 - 3, click_y))
            best['click_point'] = (click_x, click_y)
            best['matched_size'] = (scaled_w, scaled_h)
            best['bbox'] = (best['top_left'][0] + ix1, best['top_left'][1] + iy1, scaled_w, scaled_h)
        results[name] = best
        if best['found'] and best['score'] >= ACTION_BUTTON_ACCEPT_SCORE and best['click_point'] is not None:
            hits.append((name, best['score'], best['click_point'], best['scale'], cfg['priority']))
    hits.sort(key=lambda x: (x[4], -x[1]))
    return hits, results


def match_scene(frame_bgr, template_bgr, roi=None):
    fh, fw = frame_bgr.shape[:2]
    if roi is not None:
        x1, y1, x2, y2 = calc_zone_rect(fw, fh, roi)
        scan = frame_bgr[y1:y2, x1:x2]
        offset = (x1, y1)
    else:
        scan = frame_bgr
        offset = (0, 0)
    fg = cv2.cvtColor(scan, cv2.COLOR_BGR2GRAY)
    tg = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
    best_score = -1.0
    best_scale = None
    best_loc = None
    best_size = None
    for scale in [0.78, 0.88, 0.94, 1.00, 1.06]:
        tpl = resize_template_keep_valid(tg, scale)
        th, tw = tpl.shape[:2]
        if th >= fg.shape[0] or tw >= fg.shape[1]:
            continue
        res = cv2.matchTemplate(fg, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val > best_score:
            best_score = float(max_val)
            best_scale = scale
            best_loc = (max_loc[0] + offset[0], max_loc[1] + offset[1])
            best_size = (tw, th)
    return best_score, best_scale, best_loc, best_size


def detect_blue_popup_button(frame_bgr):
    """璇嗗埆寮圭獥涓嬫柟钃濊壊鎸夐挳銆傚師鐞嗭細
    1) 闄愬埗鍦ㄤ腑涓嬪尯鍩燂紱2) 鎸?HSV 鎵鹃潚钃濇寜閽紱3) 鎵炬í鍚戠煩褰紱4) 浼樺厛搴曢儴灞呬腑鐨勫ぇ鎸夐挳銆?    """
    h, w = frame_bgr.shape[:2]
    y1 = int(h * 0.58)
    y2 = int(h * 0.95)
    x1 = int(w * 0.18)
    x2 = int(w * 0.82)
    roi = frame_bgr[y1:y2, x1:x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, (75, 70, 80), (105, 255, 255))
    mask2 = cv2.inRange(hsv, (78, 35, 130), (110, 255, 255))
    mask = cv2.bitwise_or(mask1, mask2)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    best_score = -1.0
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch
        if area < 0.003 * w * h or area > 0.06 * w * h:
            continue
        aspect = cw / max(ch, 1)
        if not (1.8 <= aspect <= 5.5):
            continue
        cx = x + cw / 2
        cy = y + ch / 2
        # 涓嬫柟灞呬腑浼樺厛
        center_score = 1.0 - min(abs((cx / roi.shape[1]) - 0.5) / 0.5, 1.0)
        bottom_score = min((cy / roi.shape[0]), 1.0)
        fill_ratio = cv2.contourArea(cnt) / max(area, 1)
        score = 0.40 * center_score + 0.30 * bottom_score + 0.30 * fill_ratio
        if score > best_score:
            best_score = score
            best = (x + x1, y + y1, cw, ch)
    if best is None:
        return None
    bx, by, bw, bh = best
    return {
        "bbox": (bx, by, bw, bh),
        "center": (int(bx + bw * 0.5), int(by + bh * 0.5)),
        "score": float(best_score),
    }


def detect_boot_scene(frame_bgr, boot_template):
    score, scale, loc, size = match_scene(frame_bgr, boot_template, roi=None)
    return score, scale, loc, size


def detect_world_prem_scene(frame_bgr, world_template):
    score, scale, loc, size = match_scene(frame_bgr, world_template, roi=(0.18, 0.12, 0.72, 0.92))
    return score, scale, loc, size


def detect_dream_team_scene(frame_bgr, templates):
    best = {"score": -1.0, "scale": None, "loc": None, "size": None, "found": False, "click_point": None}
    for template in templates:
        if template is None:
            continue
        score, scale, loc, size = match_scene(frame_bgr, template, roi=DREAM_TEAM_TEMPLATE_ROI)
        if score > best["score"]:
            best.update({
                "score": score,
                "scale": scale,
                "loc": loc,
                "size": size,
            })
    if best["loc"] is not None and best["size"] is not None:
        x, y = best["loc"]
        w, h = best["size"]
        best["bbox"] = (x, y, w, h)
        best["found"] = best["score"] >= DREAM_TEAM_TEMPLATE_THRESHOLD
        if best["found"]:
            fh, fw = frame_bgr.shape[:2]
            best["click_point"] = (
                int(fw * DREAM_TEAM_CARD_CLICK_RATIO[0]),
                int(fh * DREAM_TEAM_CARD_CLICK_RATIO[1]),
            )
    if not best["found"]:
        best["bbox"] = None
        best["click_point"] = None
    return best


def detect_save_list_scene(frame_bgr, save_list_template, max_action_score: float, popup, boot_score: float):
    title_score, title_scale, title_loc, title_size = match_scene(
        frame_bgr,
        save_list_template,
        roi=(0.00, 0.00, 0.28, 0.14),
    )
    found = (
        title_score >= SAVE_LIST_TITLE_THRESHOLD
        and boot_score < BOOT_THRESHOLD
        and max_action_score <= SAVE_LIST_ACTION_MAX_SCORE
        and (not popup or popup.get('score', -1.0) < POPUP_ACCEPT_SCORE)
    )
    return {
        "found": found,
        "score": float(title_score),
        "scale": title_scale,
        "loc": title_loc,
        "size": title_size,
    }


def detect_top_left_back_button(frame_bgr) -> float:
    h, w = frame_bgr.shape[:2]
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    top_left = hsv[int(h * 0.00):int(h * 0.12), int(w * 0.00):int(w * 0.10)]
    cyan_mask = cv2.inRange(top_left, (75, 80, 120), (110, 255, 255))
    return mask_ratio(cyan_mask)


def try_launch_game(last_launch_at: float):
    now = time.time()
    if now - last_launch_at < GAME_LAUNCH_RETRY_SECONDS:
        return False, last_launch_at, f"Launch throttled, wait {GAME_LAUNCH_RETRY_SECONDS:.0f}s before retry"
    if not GAME_EXE_PATH.exists():
        return False, last_launch_at, f"Game executable not found: {GAME_EXE_PATH}"
    try:
        subprocess.Popen([str(GAME_EXE_PATH)], cwd=str(GAME_EXE_PATH.parent))
        return True, now, f"Game launched: {GAME_EXE_PATH}"
    except Exception as e:
        return False, last_launch_at, f"Game launch failed: {e}"


def do_foreground_click(hwnd: int, client_x: int, client_y: int):
    screen_x, screen_y = win32gui.ClientToScreen(hwnd, (client_x, client_y))
    old_pos = win32gui.GetCursorPos()
    old_fg = win32gui.GetForegroundWindow()
    ok = force_foreground_window(hwnd)
    if not ok:
        return False, "鍓嶅彴鍒囨崲澶辫触"
    time.sleep(0.03)
    win32api.SetCursorPos((screen_x, screen_y))
    time.sleep(0.02)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.02)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.02)
    if RESTORE_CURSOR:
        try:
            win32api.SetCursorPos(old_pos)
        except Exception:
            pass
    if RESTORE_FOREGROUND_WINDOW and old_fg and old_fg != hwnd:
        try:
            win32gui.SetForegroundWindow(old_fg)
        except Exception:
            pass
    return True, f"clicked at screen=({screen_x},{screen_y})"


def click_by_ratio(hwnd: int, ratio_x: float, ratio_y: float):
    left, top, right, bottom = get_client_rect_on_screen(hwnd)
    width = right - left
    height = bottom - top
    cx = int(width * ratio_x)
    cy = int(height * ratio_y)
    ok, msg = do_foreground_click(hwnd, cx, cy)
    return (ok, msg), (cx, cy)


def press_space_confirm(hwnd: int):
    old_fg = win32gui.GetForegroundWindow()
    ok = force_foreground_window(hwnd)
    if not ok:
        return False, "failed to focus target window"
    time.sleep(0.03)
    win32api.keybd_event(win32con.VK_SPACE, 0, 0, 0)
    time.sleep(0.03)
    win32api.keybd_event(win32con.VK_SPACE, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(0.03)
    if RESTORE_FOREGROUND_WINDOW and old_fg and old_fg != hwnd:
        try:
            win32gui.SetForegroundWindow(old_fg)
        except Exception:
            pass
    return True, "pressed SPACE"


def click_current_cursor(hwnd: int):
    old_fg = win32gui.GetForegroundWindow()
    ok = force_foreground_window(hwnd)
    if not ok:
        return False, "failed to focus target window"
    time.sleep(0.03)
    screen_x, screen_y = win32gui.GetCursorPos()
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.02)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.02)
    if RESTORE_FOREGROUND_WINDOW and old_fg and old_fg != hwnd:
        try:
            win32gui.SetForegroundWindow(old_fg)
        except Exception:
            pass
    return True, f"clicked current cursor at screen=({screen_x},{screen_y})"


def drag_by_ratio(hwnd: int, start_ratio: tuple[float, float], end_ratio: tuple[float, float], steps: int = 12):
    left, top, right, bottom = get_client_rect_on_screen(hwnd)
    width = right - left
    height = bottom - top
    start_x = left + int(width * start_ratio[0])
    start_y = top + int(height * start_ratio[1])
    end_x = left + int(width * end_ratio[0])
    end_y = top + int(height * end_ratio[1])
    old_pos = win32gui.GetCursorPos()
    old_fg = win32gui.GetForegroundWindow()
    ok = force_foreground_window(hwnd)
    if not ok:
        return False, "failed to focus target window"
    try:
        win32api.SetCursorPos((start_x, start_y))
        time.sleep(0.03)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        for idx in range(1, steps + 1):
            x = start_x + int((end_x - start_x) * idx / steps)
            y = start_y + int((end_y - start_y) * idx / steps)
            win32api.SetCursorPos((x, y))
            time.sleep(0.02)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.04)
    finally:
        if RESTORE_CURSOR:
            try:
                win32api.SetCursorPos(old_pos)
            except Exception:
                pass
        if RESTORE_FOREGROUND_WINDOW and old_fg and old_fg != hwnd:
            try:
                win32gui.SetForegroundWindow(old_fg)
            except Exception:
                pass
    return True, f"dragged screen=({start_x},{start_y})->({end_x},{end_y})"


def mask_ratio(mask) -> float:
    return float(np.count_nonzero(mask)) / max(mask.size, 1)


def detect_side_control_boxes(frame_bgr):
    h, w = frame_bgr.shape[:2]
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    cyan_mask = cv2.inRange(hsv, (70, 70, 120), (105, 255, 255))
    cyan_mask = cv2.morphologyEx(cyan_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=2)
    contours, _ = cv2.findContours(cyan_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    left_boxes = []
    right_boxes = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch
        if area < 1800:
            continue
        aspect = cw / max(ch, 1)
        if not (0.70 <= aspect <= 1.35):
            continue
        if x < int(w * 0.20):
            left_boxes.append((x, y, cw, ch))
        elif x + cw > int(w * 0.80):
            right_boxes.append((x, y, cw, ch))
    left_boxes.sort(key=lambda item: item[1])
    right_boxes.sort(key=lambda item: item[1])
    return {"left": left_boxes, "right": right_boxes}


def person_icon_score(frame_bgr, box):
    x, y, w, h = box
    pad_x = max(2, int(w * 0.14))
    pad_y = max(2, int(h * 0.14))
    roi = frame_bgr[y + pad_y:y + h - pad_y, x + pad_x:x + w - pad_x]
    if roi.size == 0:
        return 0.0
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    white_mask = cv2.inRange(hsv, (0, 0, 145), (180, 70, 255))
    contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = 0.0
    for cnt in contours:
        rx, ry, rw, rh = cv2.boundingRect(cnt)
        area = rw * rh
        if area < 120:
            continue
        cx = rx + rw / 2
        cy = ry + rh / 2
        center_score = 1.0 - min(abs(cx / max(roi.shape[1], 1) - 0.5) / 0.5, 1.0)
        upper_bias = 1.0 - min(abs(cy / max(roi.shape[0], 1) - 0.45) / 0.55, 1.0)
        fill = cv2.contourArea(cnt) / max(area, 1)
        score = 0.45 * center_score + 0.35 * upper_bias + 0.20 * fill
        best = max(best, score)
    return best


def detect_team_change_scene(frame_bgr):
    h, w = frame_bgr.shape[:2]
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    side_boxes = detect_side_control_boxes(frame_bgr)
    if not side_boxes["right"]:
        return None

    top_roi = hsv[int(h * 0.02):int(h * 0.14), int(w * 0.02):int(w * 0.20)]
    white_mask = cv2.inRange(top_roi, (0, 0, 170), (180, 70, 255))
    top_white = mask_ratio(white_mask)
    if top_white < 0.10:
        return None

    exchange_box = side_boxes["right"][0]
    exchange_person = person_icon_score(frame_bgr, exchange_box)
    if exchange_person < 0.12:
        return None

    return {
        "exchange_box": exchange_box,
        "top_white": top_white,
        "exchange_person": exchange_person,
    }


def detect_team_select_scene(frame_bgr):
    h, w = frame_bgr.shape[:2]
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    top_roi = hsv[int(h * 0.08):int(h * 0.20), int(w * 0.05):int(w * 0.60)]
    white_mask = cv2.inRange(top_roi, (0, 0, 170), (180, 70, 255))
    top_white = mask_ratio(white_mask)
    confirm_x1, confirm_y1, confirm_x2, confirm_y2 = calc_zone_rect(w, h, (0.83, 0.88, 1.00, 1.00))
    confirm_region = hsv[confirm_y1:confirm_y2, confirm_x1:confirm_x2]
    cyan_mask = cv2.inRange(confirm_region, (75, 80, 120), (110, 255, 255))
    confirm_score = mask_ratio(cyan_mask)
    first_row = (
        int(w * 0.50),
        int(h * 0.36),
    )
    confirm_point = (
        int((confirm_x1 + confirm_x2) / 2),
        int((confirm_y1 + confirm_y2) / 2),
    )
    return {
        "found": top_white >= 0.10 and confirm_score >= 0.06,
        "top_white": top_white,
        "confirm_score": confirm_score,
        "first_row_point": first_row,
        "confirm_point": confirm_point,
    }


def detect_training_select_scene(frame_bgr):
    h, w = frame_bgr.shape[:2]
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    title_roi = hsv[int(h * 0.00):int(h * 0.10), int(w * 0.00):int(w * 0.22)]
    title_white = mask_ratio(cv2.inRange(title_roi, (0, 0, 150), (180, 70, 255)))
    list_x1, list_y1, list_x2, list_y2 = calc_zone_rect(w, h, (0.72, 0.08, 0.98, 0.92))
    list_roi = hsv[list_y1:list_y2, list_x1:list_x2]
    list_cyan = mask_ratio(cv2.inRange(list_roi, (75, 80, 120), (110, 255, 255)))
    confirm_x1, confirm_y1, confirm_x2, confirm_y2 = calc_zone_rect(w, h, (0.84, 0.88, 1.00, 1.00))
    confirm_roi = hsv[confirm_y1:confirm_y2, confirm_x1:confirm_x2]
    confirm_cyan = mask_ratio(cv2.inRange(confirm_roi, (75, 80, 120), (110, 255, 255)))
    return {
        "found": title_white >= 0.03 and list_cyan >= 0.035 and confirm_cyan >= 0.10,
        "title_white": title_white,
        "list_cyan": list_cyan,
        "confirm_cyan": confirm_cyan,
        "confirm_point": (int((confirm_x1 + confirm_x2) / 2), int((confirm_y1 + confirm_y2) / 2)),
    }


def save_debug(frame, results=None, popup=None, dream_team=None, note=""):
    if not DEBUG_SAVE:
        return
    raw_path = BASE_DIR / 'last_capture.png'
    cv2.imwrite(str(raw_path), frame)
    if not DEBUG_ANNOTATE:
        return
    vis = frame.copy()
    if results:
        for name, r in results.items():
            bbox = r.get('bbox')
            if bbox:
                x, y, w, h = bbox
                color = (0, 255, 0) if r.get('found') else (0, 180, 255)
                cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
                cv2.putText(vis, f"{name}:{r.get('score', -1):.3f}", (x, max(18, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
            pt = r.get('click_point')
            if pt:
                cv2.circle(vis, pt, 6, (255, 255, 0), -1)
    if popup:
        x, y, w, h = popup['bbox']
        cv2.rectangle(vis, (x, y), (x + w, y + h), (255, 0, 255), 2)
        cv2.putText(vis, f"popup:{popup['score']:.3f}", (x, max(18, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
        cv2.circle(vis, popup['center'], 6, (255, 0, 255), -1)
    if dream_team and dream_team.get('bbox'):
        x, y, w, h = dream_team['bbox']
        color = (0, 255, 255) if dream_team.get('found') else (0, 140, 255)
        cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
        cv2.putText(vis, f"dream:{dream_team['score']:.3f}", (x, max(18, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        pt = dream_team.get('click_point')
        if pt:
            cv2.circle(vis, pt, 6, color, -1)
    if note:
        cv2.putText(vis, note, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    cv2.imwrite(str(BASE_DIR / 'last_debug.png'), vis)


def main():
    enable_dpi_awareness()
    runtime_logger = RuntimeLogger(RUNTIME_LOG_DIR)

    def emit(event: str, message: str, *, archive_tag: str | None = None, log_fields: dict | None = None, end: str = "\n") -> None:
        print(message, end=end, flush=True)
        if end == "\n":
            runtime_logger.log(event, message, **(log_fields or {}))
            if archive_tag:
                runtime_logger.archive_debug_images(archive_tag)

    emit("startup", "[INFO] Starting SFCC auto click script")
    emit("startup", f"[INFO] Process name: {PROCESS_NAME}")
    emit("startup", "[INFO] Using the state-machine navigation strategy")
    emit("startup", "[INFO] Debug images: last_capture.png / last_debug.png")
    emit("startup", "[INFO] Runtime logs: logs/sfcc_run_*.log and logs/debug_*/")
    emit("startup", "[INFO] Priority: action buttons > popup blue button > boot scene > fixed navigation > edge fallback")
    emit("startup", f"[INFO] Practice limit before shutdown: {PRACTICE_CLICK_LIMIT}")
    emit("startup", f"[INFO] Game launch path: {GAME_EXE_PATH}")
    emit("startup", "[INFO] Press Ctrl+C to exit")

    writer = StatusWriter(STATUS_FILE)
    action_templates = {k: load_template(v) for k, v in TEMPLATE_PATHS.items()}
    boot_template = load_template(BOOT_TEMPLATE_PATH)
    world_prem_template = load_template(WORLD_PREM_TEMPLATE_PATH)
    save_list_template = load_template(SAVE_LIST_TEMPLATE_PATH)
    dream_team_templates = [load_template(path) for path in DREAM_TEAM_TEMPLATE_PATHS if path.exists()]

    practice_click_count = 0
    last_click_at = {k: 0.0 for k in action_templates.keys()}
    last_popup_click_at = 0.0
    last_edge_click_at = 0.0
    last_nav_click_at = 0.0
    last_team_change_at = 0.0
    last_game_launch_at = 0.0
    nav_phase = 'idle'   # boot_or_home -> dream_team -> dream_team_wait -> world_prem -> idle
    nav_phase_since = time.time()
    team_change_phase = 'idle'  # idle -> selecting -> scroll_top -> pick_first -> confirm
    team_change_side = None
    team_scrolls_done = 0
    team_change_opened_at = 0.0
    last_scan_log_at = 0.0
    last_progress_at = time.time()
    last_practice_click_count = 0
    last_practice_progress_at = time.time()
    save_list_phase = 'idle'
    save_list_phase_since = time.time()
    invalid_frame_since = 0.0

    while True:
        now = time.time()
        runtime_logger.maybe_cleanup_old_runs()
        pid = find_pid_by_name(PROCESS_NAME)
        if not pid:
            launched, last_game_launch_at, msg = try_launch_game(last_game_launch_at)
            writer.update(force=True, state='waiting_process', last_action='launch_game' if launched else 'waiting_process', practice_click_count=practice_click_count)
            emit("game", f"[GAME] {msg}", log_fields={"launched": launched})
            if launched:
                nav_phase = 'boot_or_home'
                nav_phase_since = time.time()
                time.sleep(GAME_STARTUP_WAIT_SECONDS)
            else:
                time.sleep(1.0)
            continue

        hwnd = find_main_hwnd_by_pid(pid)
        if not hwnd:
            writer.update(state='waiting_window', last_action='waiting_window', practice_click_count=practice_click_count)
            print('[WAIT] 鎵惧埌杩涚▼浣嗘湭鎵惧埌涓荤獥鍙ｏ紝绛夊緟涓?..', end='\r', flush=True)
            time.sleep(1.0)
            continue

        bring_window_if_hidden(hwnd)
        frame = capture_window_client(hwnd)
        if frame is None:
            if invalid_frame_since == 0.0:
                invalid_frame_since = now
            writer.update(state='capture_failed', last_action='capture_failed', practice_click_count=practice_click_count)
            if now - invalid_frame_since >= INVALID_FRAME_RESTART_SECONDS:
                emit(
                    "restart",
                    f"[SAFEGUARD] Invalid frame for {INVALID_FRAME_RESTART_SECONDS:.0f}s, restarting game pid={pid}",
                    archive_tag="restart_invalid_frame",
                    log_fields={"pid": pid, "nav_phase": nav_phase},
                )
                writer.update(force=True, state='restarting_game', last_action='restart_game_invalid_frame', practice_click_count=practice_click_count)
                kill_process_tree(pid)
                nav_phase = 'idle'
                nav_phase_since = now
                last_progress_at = time.time()
                invalid_frame_since = 0.0
                time.sleep(3.0)
                continue
            print('[WARN] Invalid frame detected, retrying...', end='\r', flush=True)
            time.sleep(0.5)
            continue
        invalid_frame_since = 0.0

        hits, results = detect_buttons(frame, action_templates)
        popup = detect_blue_popup_button(frame)
        boot_score, boot_scale, boot_loc, boot_size = detect_boot_scene(frame, boot_template)
        world_prem_score, world_prem_scale, world_prem_loc, world_prem_size = detect_world_prem_scene(frame, world_prem_template)
        dream_team = detect_dream_team_scene(frame, dream_team_templates) if dream_team_templates else None
        team_change = None
        team_select = detect_team_select_scene(frame)
        training_select = {"found": False}
        back_button_ratio = detect_top_left_back_button(frame)
        max_action_score = max(results[name]['score'] for name in ('continue', 'practice', 'view_result'))
        save_list_info = detect_save_list_scene(frame, save_list_template, max_action_score, popup, boot_score)
        save_list_like = save_list_info['found']
        if not hits and not save_list_like and back_button_ratio >= BACK_BUTTON_HINT_RATIO:
            best_name = max(('continue', 'practice', 'view_result'), key=lambda name: results[name]['score'])
            best_result = results[best_name]
            if (
                best_result['score'] >= LOW_CONF_ACTION_ACCEPT_SCORE
                and best_result.get('click_point') is not None
            ):
                hits.append((
                    best_name,
                    best_result['score'],
                    best_result['click_point'],
                    best_result['scale'],
                    BUTTON_CONFIG[best_name]['priority'],
                ))
        fallback_home_like = (
            not save_list_like
            and
            max_action_score < HOME_FALLBACK_MAX_ACTION_SCORE
            and boot_score < HOME_FALLBACK_MAX_BOOT_SCORE
            and (not popup or popup.get('score', -1.0) < POPUP_ACCEPT_SCORE)
        )
        navigation_bootstrap_active = practice_click_count == 0 and max_action_score < ACTION_BUTTON_ACCEPT_SCORE
        home_like = bool(
            navigation_bootstrap_active
            and (
                (dream_team and dream_team.get('score', -1.0) >= HOME_SCENE_DREAM_SCORE and world_prem_score < WORLD_PREM_THRESHOLD)
                or fallback_home_like
            )
        )
        strong_action_hit = hits[0] if hits and hits[0][1] >= ACTION_OVERRIDE_SCORE else None
        if nav_phase == 'idle' and home_like:
            nav_phase = 'dream_team'
            nav_phase_since = now
        elif nav_phase == 'boot_or_home' and (strong_action_hit or max_action_score >= ACTION_OVERRIDE_SCORE):
            nav_phase = 'idle'
            nav_phase_since = now
        elif nav_phase in ('boot_or_home', 'dream_team', 'dream_team_wait', 'world_prem') and (strong_action_hit or max_action_score >= ACTION_OVERRIDE_SCORE) and not home_like:
            nav_phase = 'idle'
            nav_phase_since = now
        navigation_active = nav_phase in ('boot_or_home', 'dream_team', 'dream_team_wait', 'world_prem')
        note = f"nav={nav_phase} boot={boot_score:.3f}"
        if dream_team:
            note += f" dream={dream_team['score']:.3f}"
        note += f" world={world_prem_score:.3f}"
        note += f" back={back_button_ratio:.3f}"
        note += f" save={save_list_info['score']:.3f}"
        if save_list_like:
            note += " save_list=1"
        operable_scene = bool(
            hits
            or (popup and popup.get('score', -1.0) >= POPUP_ACCEPT_SCORE)
            or boot_score >= BOOT_THRESHOLD
            or home_like
            or save_list_like
            or world_prem_score >= WORLD_PREM_THRESHOLD
            or team_select.get('found')
        )
        if operable_scene:
            last_progress_at = now
        elif now - last_progress_at >= NO_PROGRESS_RESTART_SECONDS:
            emit(
                "restart",
                f"[SAFEGUARD] No operable scene for {NO_PROGRESS_RESTART_SECONDS:.0f}s, restarting game pid={pid}",
                archive_tag="restart_no_progress",
                log_fields={"pid": pid, "nav_phase": nav_phase},
            )
            writer.update(force=True, state='restarting_game', last_action='restart_game_no_progress', practice_click_count=practice_click_count)
            kill_process_tree(pid)
            nav_phase = 'idle'
            nav_phase_since = now
            last_progress_at = time.time()
            time.sleep(3.0)
            continue

        if practice_click_count != last_practice_click_count:
            last_practice_click_count = practice_click_count
            last_practice_progress_at = now
        elif practice_click_count > 0 and now - last_practice_progress_at >= PRACTICE_STALL_RESTART_SECONDS:
            emit(
                "restart",
                f"[SAFEGUARD] Practice counter stalled for {PRACTICE_STALL_RESTART_SECONDS:.0f}s at #{practice_click_count}, restarting game pid={pid}",
                archive_tag="restart_practice_stall",
                log_fields={"pid": pid, "practice_click_count": practice_click_count, "nav_phase": nav_phase},
            )
            writer.update(force=True, state='restarting_game', last_action='restart_game_practice_stall', practice_click_count=practice_click_count)
            kill_process_tree(pid)
            nav_phase = 'idle'
            nav_phase_since = now
            last_progress_at = time.time()
            last_practice_progress_at = time.time()
            time.sleep(3.0)
            continue

        if team_change_phase == 'idle' and team_change and team_change.get('exchange_box') and now - last_team_change_at >= TEAM_CHANGE_COOLDOWN:
            box = team_change['exchange_box']
            cx = int(box[0] + box[2] * 0.5)
            cy = int(box[1] + box[3] * 0.5)
            ok, msg = do_foreground_click(hwnd, cx, cy)
            last_team_change_at = now
            if ok:
                team_change_phase = 'pick_first'
                team_change_side = 'match_start'
                team_scrolls_done = 0
                team_change_opened_at = now
                writer.update(force=True, state='team_change', last_action='team_open_selector', practice_click_count=practice_click_count)
                emit("team", f"[TEAM] open_selector top_white={team_change['top_white']:.3f} person={team_change['exchange_person']:.3f} client=({cx},{cy}) -> {msg}", archive_tag="team_change", log_fields={"client_x": cx, "client_y": cy})
                time.sleep(1.2)
                continue

        if team_change_phase != 'idle':
            if team_change_phase == 'pick_first' and now - team_change_opened_at >= TEAM_SELECT_OPEN_WAIT_SECONDS:
                if team_select.get('found'):
                    x, y = team_select['first_row_point']
                else:
                    x = int(frame.shape[1] * TEAM_SELECT_FIRST_ROW_CLICK_RATIO[0])
                    y = int(frame.shape[0] * TEAM_SELECT_FIRST_ROW_CLICK_RATIO[1])
                ok, msg = do_foreground_click(hwnd, x, y)
                last_team_change_at = now
                if ok:
                    team_change_phase = 'confirm'
                    writer.update(force=True, state='team_change', last_action='team_pick_first', practice_click_count=practice_click_count)
                    emit("team", f"[TEAM] pick_first client=({x},{y}) -> {msg}")
                    time.sleep(0.8)
                    continue

            if team_change_phase == 'confirm' and now - last_team_change_at >= 0.6:
                if team_select.get('found'):
                    x, y = team_select['confirm_point']
                else:
                    x = int(frame.shape[1] * TEAM_SELECT_CONFIRM_CLICK_RATIO[0])
                    y = int(frame.shape[0] * TEAM_SELECT_CONFIRM_CLICK_RATIO[1])
                ok, msg = do_foreground_click(hwnd, x, y)
                last_team_change_at = now
                if ok:
                    team_change_phase = 'idle'
                    team_change_side = None
                    team_scrolls_done = 0
                    team_change_opened_at = 0.0
                    writer.update(force=True, state='team_change', last_action='team_confirm', practice_click_count=practice_click_count)
                    emit("team", f"[TEAM] confirm client=({x},{y}) -> {msg}")
                    time.sleep(1.5)
                    continue

            if team_select.get('found'):
                if team_change_phase == 'pick_first':
                    x, y = team_select['first_row_point']
                    ok, msg = do_foreground_click(hwnd, x, y)
                    last_team_change_at = now
                    if ok:
                        team_change_phase = 'confirm'
                        writer.update(force=True, state='team_change', last_action='team_pick_first', practice_click_count=practice_click_count)
                        emit("team", f"[TEAM] pick_first client=({x},{y}) -> {msg}")
                        time.sleep(0.8)
                        continue
                if team_change_phase == 'confirm':
                    x, y = team_select['confirm_point']
                    ok, msg = do_foreground_click(hwnd, x, y)
                    last_team_change_at = now
                    if ok:
                        team_change_phase = 'idle'
                        team_change_side = None
                        team_scrolls_done = 0
                        team_change_opened_at = 0.0
                        writer.update(force=True, state='team_change', last_action='team_confirm', practice_click_count=practice_click_count)
                        emit("team", f"[TEAM] confirm client=({x},{y}) -> {msg}")
                        time.sleep(1.5)
                        continue
            elif now - last_team_change_at > 4.0:
                team_change_phase = 'idle'
                team_change_side = None
                team_scrolls_done = 0
                team_change_opened_at = 0.0
        if not save_list_like:
            save_list_phase = 'idle'
            save_list_phase_since = now

        save_debug(frame, results=results, popup=popup, dream_team=dream_team, note=note)

        # 1) 鍙充笅鍔ㄤ綔鎸夐挳浼樺厛
        if navigation_active:
            hits = []
        if hits:
            btn_name, score, (x, y), scale, _ = hits[0]
            writer.update(state='main_loop', last_button=btn_name, practice_click_count=practice_click_count)
            if now - last_click_at[btn_name] >= CLICK_COOLDOWN:
                ok, msg = do_foreground_click(hwnd, x, y)
                last_click_at[btn_name] = now
                nav_phase = 'idle'
                nav_phase_since = now
                if ok:
                    if btn_name == 'practice':
                        practice_click_count += 1
                        writer.update(force=True, state='main_loop', last_action='click_practice', last_button=btn_name, practice_click_count=practice_click_count)
                        emit("action", f'[ACT] practice #{practice_click_count}/{PRACTICE_CLICK_LIMIT} score={score:.3f} scale={scale:.2f} pos=({x},{y}) -> {msg}', archive_tag="action_practice", log_fields={"button": btn_name, "score": round(score, 4), "scale": scale, "client_x": x, "client_y": y})
                        if practice_click_count >= PRACTICE_CLICK_LIMIT:
                            writer.update(force=True, state='done', last_action='shutdown', last_button='practice', practice_click_count=practice_click_count)
                            emit("done", f"[DONE] Practice clicked {practice_click_count} times, shutting down in {SHUTDOWN_DELAY_SECONDS}s")
                            subprocess.run(['shutdown', '/s', '/t', str(SHUTDOWN_DELAY_SECONDS)], check=False)
                            return
                    else:
                        writer.update(force=True, state='main_loop', last_action=f'click_{btn_name}', last_button=btn_name, practice_click_count=practice_click_count)
                        emit("action", f'[ACT] {btn_name} score={score:.3f} scale={scale:.2f} pos=({x},{y}) -> {msg}', archive_tag=f"action_{btn_name}", log_fields={"button": btn_name, "score": round(score, 4), "scale": scale, "client_x": x, "client_y": y})
                else:
                    emit("warn", f'[WARN] {btn_name} score={score:.3f} pos=({x},{y}) -> {msg}', archive_tag=f"warn_{btn_name}")
            else:
                print(f'[SKIP] {btn_name} 鍐峰嵈涓?score={score:.3f}', end='\r', flush=True)
            time.sleep(SCAN_INTERVAL)
            continue

        # 2) 寮圭獥钃濊壊鎸夐挳锛氫换浣曟枃鏈兘涓嶇锛岀洿鎺ョ偣鎸夐挳涓績
        if popup and boot_score < BOOT_THRESHOLD and popup.get('score', -1.0) >= POPUP_ACCEPT_SCORE and now - last_popup_click_at >= POPUP_CLICK_COOLDOWN:
            x, y = popup['center']
            ok, msg = do_foreground_click(hwnd, x, y)
            last_popup_click_at = now
            writer.update(force=True, state='popup', last_action='popup_blue_button', practice_click_count=practice_click_count)
            if ok:
                emit("popup", f"[POPUP] blue_button score={popup['score']:.3f} bbox={popup['bbox']} client=({x},{y}) -> {msg}", archive_tag="popup_blue", log_fields={"score": round(popup['score'], 4), "bbox": popup['bbox'], "client_x": x, "client_y": y})
            else:
                emit("warn", f"[POPUP][WARN] bbox={popup['bbox']} client=({x},{y}) -> {msg}", archive_tag="popup_warn")
            time.sleep(1.2)
            continue

        # 3) 鍚姩椤碉細SEGA 鏂板垱閫犵悆浼?2026
        if boot_score >= BOOT_THRESHOLD and now - last_nav_click_at >= NAV_CLICK_COOLDOWN:
            (ok, msg), (cx, cy) = click_by_ratio(hwnd, BOOT_CLICK_RATIO[0], BOOT_CLICK_RATIO[1])
            last_nav_click_at = now
            nav_phase = 'dream_team'
            nav_phase_since = now
            writer.update(force=True, state='navigating', last_action='boot_click', practice_click_count=practice_click_count)
            emit("nav", f'[NAV] boot_click score={boot_score:.3f} scale={boot_scale:.2f} client=({cx},{cy}) -> {msg}', archive_tag="nav_boot", log_fields={"score": round(boot_score, 4), "scale": boot_scale, "client_x": cx, "client_y": cy})
            time.sleep(BOOT_WAIT_SECONDS)
            continue

        # 4) Enter the home scene and advance the navigation state machine.
        if nav_phase == 'boot_or_home' and now - nav_phase_since > 2.0:
            nav_phase = 'dream_team'
            nav_phase_since = now

        if nav_phase == 'dream_team' and now - last_nav_click_at >= NAV_CLICK_COOLDOWN:
            if dream_team and dream_team.get('found') and dream_team.get('click_point') is not None:
                cx, cy = dream_team['click_point']
                ok, msg = do_foreground_click(hwnd, cx, cy)
                nav_action = 'create_club_template_gate'
                emit("nav", f"[NAV] create_club_template_gate score={dream_team['score']:.3f} bbox={dream_team['bbox']} client=({cx},{cy}) -> {msg}", archive_tag="nav_create_club_gate", log_fields={"score": round(dream_team['score'], 4), "bbox": dream_team['bbox'], "client_x": cx, "client_y": cy})
            else:
                (ok, msg), (cx, cy) = click_by_ratio(hwnd, CREATE_CLUB_CLICK_RATIO[0], CREATE_CLUB_CLICK_RATIO[1])
                nav_action = 'create_club_fixed'
                emit("nav", f"[NAV] create_club_fixed score={(dream_team['score'] if dream_team else -1.0):.3f} client=({cx},{cy}) -> {msg}", archive_tag="nav_create_club_fixed", log_fields={"score": round((dream_team['score'] if dream_team else -1.0), 4), "client_x": cx, "client_y": cy})
            last_nav_click_at = now
            if ok:
                nav_phase = 'dream_team_wait'
                nav_phase_since = now
                writer.update(force=True, state='navigating', last_action=nav_action, practice_click_count=practice_click_count)
                time.sleep(3.0)
                continue
            writer.update(force=True, state='navigating', last_action=f'{nav_action}_failed', practice_click_count=practice_click_count)

        if nav_phase == 'dream_team_wait':
            if world_prem_score >= WORLD_PREM_THRESHOLD:
                nav_phase = 'world_prem'
                nav_phase_since = now
            elif save_list_like and now - last_nav_click_at >= NAV_CLICK_COOLDOWN:
                (ok, msg), (cx, cy) = click_by_ratio(hwnd, SAVE_LIST_BACK_CLICK_RATIO[0], SAVE_LIST_BACK_CLICK_RATIO[1])
                nav_action = 'save_list_back'
                last_nav_click_at = now
                emit("nav", f"[NAV] {nav_action} client=({cx},{cy}) -> {msg}", archive_tag=nav_action, log_fields={"client_x": cx, "client_y": cy})
                if ok:
                    nav_phase_since = now
                    writer.update(force=True, state='navigating', last_action=nav_action, practice_click_count=practice_click_count)
                    time.sleep(3.0)
                    continue
            elif home_like and now - nav_phase_since >= NAV_CLICK_COOLDOWN:
                nav_phase = 'dream_team'
                nav_phase_since = now
            elif not navigation_bootstrap_active:
                nav_phase = 'idle'
                nav_phase_since = now
            elif not home_like and now - nav_phase_since >= NAV_STEP_TIMEOUT:
                nav_phase = 'idle'
                nav_phase_since = now
            elif home_like and now - nav_phase_since >= 18.0:
                nav_phase = 'dream_team'
                nav_phase_since = now
            elif now - nav_phase_since >= NAV_STEP_TIMEOUT:
                nav_phase = 'dream_team'
                nav_phase_since = now

        if nav_phase == 'world_prem' and now - last_nav_click_at >= NAV_CLICK_COOLDOWN:
            (ok, msg), (cx, cy) = click_by_ratio(hwnd, WORLD_PREM_CLICK_RATIO[0], WORLD_PREM_CLICK_RATIO[1])
            last_nav_click_at = now
            emit("nav", f'[NAV] world_prem_fixed client=({cx},{cy}) -> {msg}', archive_tag="nav_world_prem", log_fields={"client_x": cx, "client_y": cy})
            if ok:
                nav_phase = 'idle'
                nav_phase_since = now
                writer.update(force=True, state='navigating', last_action='world_prem_fixed', practice_click_count=practice_click_count)
                time.sleep(3.0)
                continue
            writer.update(force=True, state='navigating', last_action='world_prem_fixed_failed', practice_click_count=practice_click_count)

        # 濡傛灉瀵艰埅鍚庨暱鏃堕棿杩樻病杩涜仈璧涢〉闈紝鍥炲埌姊﹀够鐞冮槦姝ラ閲嶆柊鏉ヤ竴娆?
        if navigation_bootstrap_active and nav_phase == 'idle' and now - nav_phase_since >= NAV_STEP_TIMEOUT:
            nav_phase = 'dream_team'
            nav_phase_since = now

        # 5) 鍏滃簳锛氬疄鍦ㄤ粈涔堥兘娌″彂鐜帮紝鐐逛竴娆″睆骞曞乏杈圭紭
        if ENABLE_EDGE_FALLBACK and not navigation_active and now - last_edge_click_at >= EDGE_CLICK_COOLDOWN:
            ok, msg = click_current_cursor(hwnd)
            last_edge_click_at = now
            writer.update(force=True, state='fallback', last_action='mouse_click', practice_click_count=practice_click_count)
            print(f'[FALLBACK] mouse_click -> {msg}')
            time.sleep(1.0)
            continue

        writer.update(state='scanning', last_action='scan_idle', practice_click_count=practice_click_count)
        if PRINT_BEST_SCORE:
            c = results['continue']
            p = results['practice']
            v = results['view_result']
            popup_text = 'none' if not popup else f"{popup['score']:.3f}@{popup['bbox']}"
            scan_line = (
                f"[SCAN] continue={c['score']:.3f}@{c['scale']}/crop{c['crop_ratio']} "
                f"practice={p['score']:.3f}@{p['scale']}/crop{p['crop_ratio']} "
                f"view_result={v['score']:.3f}@{v['scale']}/crop{v['crop_ratio']} "
                f"boot={boot_score:.3f}@{boot_scale} popup={popup_text} nav={nav_phase}"
            )
            print(scan_line, end='\r', flush=True)
            if now - last_scan_log_at >= SCAN_LOG_INTERVAL_SECONDS:
                runtime_logger.log(
                    "scan",
                    scan_line,
                    nav_phase=nav_phase,
                    continue_score=round(c['score'], 4),
                    practice_score=round(p['score'], 4),
                    view_result_score=round(v['score'], 4),
                    boot_score=round(boot_score, 4),
                    world_prem_score=round(world_prem_score, 4),
                    dream_team_score=round((dream_team['score'] if dream_team else -1.0), 4),
                    popup_score=round((popup['score'] if popup else -1.0), 4),
                )
                last_scan_log_at = now
        else:
            print('[SCAN] 鏈娴嬪埌鐩爣鎸夐挳', end='\r', flush=True)
        time.sleep(SCAN_INTERVAL)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Exited.", flush=True)
