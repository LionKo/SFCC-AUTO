from __future__ import annotations

import logging
import time

import cv2
import numpy as np

CLUB_TRANSFERS_RENEWAL_BUTTONS = ["club_transfers_renewal_button", "club_transfers_renewal_button_2"]
CONFIRM_BUTTONS = ["ok_button", "ok_button2", "ok_button3", "ok_chs_button"]
SP_JOIN_BELONG_MARKERS = ["sp_belong"]
SP_JOIN_BUTTONS = ["sp_join_button1", "sp_join_button2", "sp_join_button3", "sp_join_button4"]
SP_JOIN_FILTER_ENTRANCES = ["sp_join_filter_entrance"]
SP_BELONG_THRESHOLD = 0.72
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
SP_JOIN_SLOT_CLICK_OFFSET_Y = 42
SP_JOIN_SCROLL_RATIO = (0.82, 0.52)
SP_JOIN_SCROLL_STEPS_TO_BOTTOM = 3
SP_JOIN_SCROLL_DELTA = -120
FINAL_CONFIRM_BUTTONS = ["final_confirm_ok_button", "final_confirm_ok_button2"]
CLUB_TRANSFERS_MIN_CLICK_COOLDOWN_SECONDS = 1.0
FINAL_CONFIRM_TO_MAIN_HANDOFF_SECONDS = 8.0
FINAL_CONFIRM_TO_MAIN_POLL_INTERVAL_SECONDS = 0.2
NEW_SEASON_FOLLOWUP_POLL_INTERVAL_SECONDS = 0.2
NEW_SEASON_CHAIN_CONTINUATION_SECONDS = 20.0
NEW_SEASON_CHAIN_IDLE_MISS_LIMIT = 5
CLUB_TRANSFERS_LEVEL_FOLLOWUP_SECONDS = 10.0
SPONSOR_SELECTION_FOLLOWUP_SECONDS = 8.0
SP_JOIN_CONFIRM_HANDOFF_SECONDS = 10.0
SP_JOIN_CONFIRM_MAX_CLICKS = 2
CLUB_TRANSFERS_SETTLE_SECONDS = 1.0
CLUB_TRANSFERS_CONFIRM_WAIT_SECONDS = 10.0
CLUB_TRANSFERS_LEVEL_SETTLE_SECONDS = 2.0
SPONSOR_SELECTION_SETTLE_SECONDS = 1.0
SP_JOIN_SETTLE_SECONDS = 2.0
FINAL_CONFIRM_SETTLE_SECONDS = 3.0
CLUB_TRANSFERS_CONFIRM_POPUP_REGION = (0.34, 0.54, 0.74, 0.84)
CLUB_TRANSFERS_CONFIRM_POPUP_MIN_AREA = 3500

NEW_SEASON_STEP_LABELS = {
    "club_transfers": "club transfers",
    "club_transfers_level": "club transfers level",
    "sponsor_selection": "sponsor selection",
    "final_confirm": "final confirm",
    "sp_join": "SP join",
}


class NewSeasonFlow:
    def __init__(self, bot: object) -> None:
        self.bot = bot

    def mark_active(self) -> None:
        self.bot.last_new_season_activity_time = time.time()

    def handle_priority_confirm(self, timeout: float = 1.5, settle: float = 0.5) -> bool:
        ok = self.bot.vision.wait_for_any(
            CONFIRM_BUTTONS,
            min(self.bot.button_threshold, 0.72),
            timeout=timeout,
            interval=0.12,
        )
        if not ok:
            return False
        self.mark_active()
        logging.info("New-season priority confirm detected: %s (score=%.3f)", ok.name, ok.score)
        self.bot.click_match(ok, settle=settle)
        return True

    def matches(self, screenshot) -> bool:
        return self.bot.detect_new_season_step_in_screenshot(screenshot) is not None

    def run_step(self, step: str, screenshot=None, fast_dispatch: bool = False) -> bool:
        if fast_dispatch:
            if not self.bot.check_runtime_process_only():
                return False
        elif not self.bot.check_runtime_health():
            return False
        return self._run_chain(initial_step=step, screenshot=screenshot, fast_dispatch=fast_dispatch)

    def _dispatch_step(self, step: str, screenshot=None, fast_dispatch: bool = False) -> bool:
        self.bot.set_active_flow("new_season")
        logging.info("New season flow step: %s", NEW_SEASON_STEP_LABELS.get(step, step))
        if step == "club_transfers":
            return self.run_club_transfers(assume_detected=True)
        if step == "club_transfers_level":
            return self.run_club_transfers_level(screenshot=screenshot, assume_detected=True)
        if step == "sponsor_selection":
            return self.run_sponsor_selection(assume_detected=True)
        if step == "final_confirm":
            return self.run_final_confirm(assume_detected=True)
        if step == "sp_join":
            return self.run_sp_join(screenshot=screenshot, assume_detected=True)
        return False

    def _run_chain(self, *, initial_step: str | None = None, screenshot=None, fast_dispatch: bool = False) -> bool:
        self.bot.set_active_flow("new_season")
        current_step = initial_step
        current_screenshot = screenshot
        idle_misses = 0
        deadline = time.time() + NEW_SEASON_CHAIN_CONTINUATION_SECONDS

        while time.time() < deadline:
            self.mark_active()
            if current_screenshot is None:
                current_screenshot = self.bot.vision.capture()

            if self.bot.find_main_screen_in_screenshot(current_screenshot):
                logging.info("New-season chain has already returned to creative mode main screen")
                return True

            step = current_step or self.bot.detect_new_season_step_in_screenshot(current_screenshot)
            if not step:
                if self.handle_priority_confirm(timeout=0.25, settle=0.2):
                    idle_misses = 0
                    current_screenshot = None
                    current_step = None
                    continue

                idle_misses += 1
                if idle_misses >= NEW_SEASON_CHAIN_IDLE_MISS_LIMIT:
                    return False
                time.sleep(NEW_SEASON_FOLLOWUP_POLL_INTERVAL_SECONDS)
                current_screenshot = None
                current_step = None
                continue

            idle_misses = 0
            result = self._dispatch_step(step, screenshot=current_screenshot, fast_dispatch=fast_dispatch)
            fast_dispatch = False

            current_screenshot = self.bot.vision.capture()
            current_step = None

            if self.bot.find_main_screen_in_screenshot(current_screenshot):
                logging.info("New-season chain returned to creative mode main screen")
                return True

            followup_step = self.bot.detect_new_season_step_in_screenshot(current_screenshot)
            if followup_step:
                logging.info(
                    "New-season chain continuing directly into %s",
                    NEW_SEASON_STEP_LABELS.get(followup_step, followup_step),
                )
                current_step = followup_step
                continue

            if result:
                if self.handle_priority_confirm(timeout=0.25, settle=0.2):
                    continue
                idle_misses += 1
                if idle_misses >= NEW_SEASON_CHAIN_IDLE_MISS_LIMIT:
                    return True
                time.sleep(NEW_SEASON_FOLLOWUP_POLL_INTERVAL_SECONDS)
                continue

            return False

        logging.warning("New-season chain continuation window expired")
        return False

    def _wait_for_followup_step(
        self,
        allowed_steps: set[str],
        timeout: float,
        poll_interval: float = NEW_SEASON_FOLLOWUP_POLL_INTERVAL_SECONDS,
    ) -> tuple[str | None, object | None]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.bot.check_runtime_process_only():
                return None, None

            screenshot = self.bot.vision.capture()
            if "sp_join" in allowed_steps and self.bot.find_sp_join_screen_in_screenshot(screenshot):
                return "sp_join", screenshot
            if "sponsor_selection" in allowed_steps and self.bot.find_sponsor_selection_screen_in_screenshot(screenshot):
                return "sponsor_selection", screenshot
            if "final_confirm" in allowed_steps and self.bot.find_final_confirm_screen_in_screenshot(screenshot):
                return "final_confirm", screenshot
            if "club_transfers_level" in allowed_steps and self.bot.find_club_transfers_level_screen_in_screenshot(screenshot):
                return "club_transfers_level", screenshot
            if "club_transfers" in allowed_steps and self.bot.find_club_transfers_screen_in_screenshot(screenshot):
                return "club_transfers", screenshot

            next_step = self.bot.detect_new_season_step_in_screenshot(screenshot)
            if next_step in allowed_steps:
                return next_step, screenshot

            if self.bot.find_main_screen_in_screenshot(screenshot):
                return "creative_mode_main", screenshot

            if self.handle_priority_confirm(timeout=0.2, settle=0.2):
                continue

            time.sleep(poll_interval)
        return None, None

    def _wait_for_expected_step(
        self,
        expected_step: str,
        timeout: float,
        poll_interval: float = NEW_SEASON_FOLLOWUP_POLL_INTERVAL_SECONDS,
    ) -> tuple[bool, object | None]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.bot.check_runtime_process_only():
                return False, None

            screenshot = self.bot.vision.capture()
            if expected_step == "club_transfers_level" and self.bot.find_club_transfers_level_screen_in_screenshot(screenshot):
                return True, screenshot
            if expected_step == "sponsor_selection" and self.bot.find_sponsor_selection_screen_in_screenshot(screenshot):
                return True, screenshot
            if expected_step == "sp_join" and self.bot.find_sp_join_screen_in_screenshot(screenshot):
                return True, screenshot
            if expected_step == "final_confirm" and self.bot.find_final_confirm_screen_in_screenshot(screenshot):
                return True, screenshot
            if expected_step == "creative_mode_main" and self.bot.find_main_screen_in_screenshot(screenshot):
                return True, screenshot

            if expected_step != "club_transfers_level" and self.handle_priority_confirm(timeout=0.2, settle=0.2):
                continue

            time.sleep(poll_interval)
        return False, None

    def _dispatch_visible_followup_step(
        self,
        allowed_steps: tuple[str, ...],
        *,
        screenshot=None,
        log_prefix: str,
    ) -> bool | None:
        current = screenshot if screenshot is not None else self.bot.vision.capture()

        for step in allowed_steps:
            if step == "club_transfers_level" and self.bot.find_club_transfers_level_screen_in_screenshot(current):
                logging.info("%s detected visible club_transfers_level, continuing inline", log_prefix)
                return self.run_club_transfers_level(screenshot=current, assume_detected=True)
            if step == "sponsor_selection" and self.bot.find_sponsor_selection_screen_in_screenshot(current):
                logging.info("%s detected visible sponsor_selection, continuing inline", log_prefix)
                return self.run_sponsor_selection(assume_detected=True)
            if step == "sp_join" and self.bot.find_sp_join_screen_in_screenshot(current):
                logging.info("%s detected visible sp_join, continuing inline", log_prefix)
                return self.run_sp_join(screenshot=current, assume_detected=True)
            if step == "final_confirm" and self.bot.find_final_confirm_screen_in_screenshot(current):
                logging.info("%s detected visible final_confirm, continuing inline", log_prefix)
                return self.run_final_confirm(assume_detected=True)
            if step == "creative_mode_main" and self.bot.find_main_screen_in_screenshot(current):
                logging.info("%s detected creative mode main screen, ending new-season flow", log_prefix)
                return True

        return None

    def _find_club_transfers_popup_confirm_center(self, screenshot) -> tuple[int, int] | None:
        height, width = screenshot.shape[:2]
        left = max(0, int(width * CLUB_TRANSFERS_CONFIRM_POPUP_REGION[0]))
        top = max(0, int(height * CLUB_TRANSFERS_CONFIRM_POPUP_REGION[1]))
        right = min(width, int(width * CLUB_TRANSFERS_CONFIRM_POPUP_REGION[2]))
        bottom = min(height, int(height * CLUB_TRANSFERS_CONFIRM_POPUP_REGION[3]))
        if right <= left or bottom <= top:
            return None

        region = screenshot[top:bottom, left:right]
        if region.size == 0:
            return None

        hsv_masks = []
        for conversion in (cv2.COLOR_BGR2HSV, cv2.COLOR_RGB2HSV):
            hsv = cv2.cvtColor(region, conversion)
            mask = cv2.inRange(hsv, np.array([70, 70, 80]), np.array([110, 255, 255]))
            hsv_masks.append(mask)

        mask = hsv_masks[0]
        for extra_mask in hsv_masks[1:]:
            mask = cv2.bitwise_or(mask, extra_mask)

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_rect = None
        best_area = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < CLUB_TRANSFERS_CONFIRM_POPUP_MIN_AREA:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            if w < 80 or h < 30:
                continue
            rect_area = w * h
            if rect_area > best_area:
                best_area = rect_area
                best_rect = (x, y, w, h)

        if not best_rect:
            return None

        x, y, w, h = best_rect
        return left + x + w // 2, top + y + h // 2

    def run_club_transfers(self, assume_detected: bool = False) -> bool:
        self.mark_active()
        if not self.bot.check_runtime_health():
            return False
        corrected = self._dispatch_visible_followup_step(
            ("club_transfers_level", "sponsor_selection", "sp_join", "final_confirm", "creative_mode_main"),
            log_prefix="Club transfers flow",
        )
        if corrected is not None:
            return corrected
        title = True if assume_detected else self.bot.is_club_transfers_screen()
        if not title:
            return self.run_club_transfers_level()

        logging.info("Club transfers screen detected, starting renewal flow")
        renewal = self.bot.click_named_button(CLUB_TRANSFERS_RENEWAL_BUTTONS, timeout=5.0, settle=1.0)
        if not renewal:
            logging.warning("Club transfers renewal button not found")
            return False

        time.sleep(CLUB_TRANSFERS_SETTLE_SECONDS)
        followup_level_screenshot = None
        level_seen_count = 0
        saw_ok_chs = False
        confirm_deadline = time.time() + CLUB_TRANSFERS_CONFIRM_WAIT_SECONDS
        while time.time() < confirm_deadline:
            if not self.bot.check_runtime_process_only():
                return False
            screenshot = self.bot.vision.capture()
            ok_chs = self.bot.vision.match_best(
                screenshot,
                ["ok_chs_button"],
                min(self.bot.button_threshold, 0.72),
            )
            if ok_chs:
                self.mark_active()
                saw_ok_chs = True
                logging.info("Club transfers follow-up confirm detected: %s (score=%.3f)", ok_chs.name, ok_chs.score)
                self.bot.click_match(ok_chs, settle=0.35)
                time.sleep(CLUB_TRANSFERS_SETTLE_SECONDS)
                break

            popup_confirm_center = self._find_club_transfers_popup_confirm_center(screenshot)
            if popup_confirm_center:
                self.mark_active()
                logging.info(
                    "Club transfers follow-up detected the centered green confirm button, clicking it directly at (%s, %s)",
                    popup_confirm_center[0],
                    popup_confirm_center[1],
                )
                self.bot.window.click_client(popup_confirm_center[0], popup_confirm_center[1], settle=0.35)
                time.sleep(CLUB_TRANSFERS_SETTLE_SECONDS)
                break

            if self.bot.find_club_transfers_level_screen_in_screenshot(screenshot):
                level_seen_count += 1
                if level_seen_count >= 2:
                    followup_level_screenshot = screenshot
                    break
            else:
                level_seen_count = 0

            time.sleep(0.15)

        if followup_level_screenshot is not None:
            logging.info("Club transfers handoff detected club_transfers_level")
            return self._dispatch_step("club_transfers_level", screenshot=followup_level_screenshot, fast_dispatch=True)

        advanced, followup_screenshot = self._wait_for_expected_step("club_transfers_level", timeout=6.0)
        if advanced:
            logging.info("Club transfers handoff detected club_transfers_level")
            return self.run_club_transfers_level(screenshot=followup_screenshot, assume_detected=True)

        final_screenshot = self.bot.vision.capture()
        if self.bot.find_club_transfers_screen_in_screenshot(final_screenshot):
            logging.warning(
                "Club transfers is still active after the renewal flow%s; keeping the new-season chain alive instead of dropping back to the scheduler",
                " with ok_chs handled" if saw_ok_chs else "",
            )
            return True
        return False

    def run_club_transfers_level(self, screenshot=None, assume_detected: bool = False) -> bool:
        self.mark_active()
        if not self.bot.check_runtime_health():
            return False
        screenshot = screenshot if screenshot is not None else self.bot.vision.capture()
        corrected = self._dispatch_visible_followup_step(
            ("sponsor_selection", "sp_join", "final_confirm", "creative_mode_main"),
            screenshot=screenshot,
            log_prefix="Club transfers level flow",
        )
        if corrected is not None:
            return corrected
        level_screen = True if assume_detected else (
            self.bot.find_club_transfers_level_screen_in_screenshot(screenshot) or self.bot.find_club_transfers_level_title_in_screenshot(screenshot)
        )
        if not level_screen:
            return False

        clicked_min = False
        clicked_confirm = False
        deadline = time.time() + 8.0
        while time.time() < deadline:
            screenshot = self.bot.vision.capture()
            still_level = self.bot.find_club_transfers_level_screen_in_screenshot(screenshot) or self.bot.find_club_transfers_level_title_in_screenshot(screenshot)
            if not still_level:
                if self.bot.find_sponsor_selection_screen_in_screenshot(screenshot):
                    logging.info("Club transfers level screen has advanced to sponsor_selection")
                    return self.run_sponsor_selection(assume_detected=True)
                if self.bot.find_main_screen_in_screenshot(screenshot):
                    return True
                advanced, followup_screenshot = self._wait_for_expected_step("sponsor_selection", timeout=CLUB_TRANSFERS_LEVEL_FOLLOWUP_SECONDS)
                if advanced:
                    logging.info("Club transfers level handoff detected sponsor_selection")
                    return self.run_sponsor_selection(assume_detected=True)
                time.sleep(0.2)
                continue

            now = time.time()
            if not clicked_min and now - self.bot.last_club_transfers_min_click_time >= CLUB_TRANSFERS_MIN_CLICK_COOLDOWN_SECONDS:
                logging.info("Club transfers level screen detected, selecting minimum difficulty")
                min_button = self.bot.find_club_transfers_min_button_in_screenshot(screenshot)
                if min_button:
                    logging.info(
                        "Selecting left-most minimum difficulty button at (%s,%s)",
                        min_button.center[0],
                        min_button.center[1],
                    )
                    self.mark_active()
                    self.bot.click_match(min_button, settle=0.35)
                else:
                    logging.warning("Club transfers minimum difficulty button not found, using hotspot fallback")
                    self.mark_active()
                    self.bot.click_club_transfers_min_hotspot(settle=0.35)
                self.bot.last_club_transfers_min_click_time = time.time()
                clicked_min = True
                time.sleep(0.15)
                continue

            if clicked_min and not clicked_confirm and self.handle_priority_confirm(timeout=0.8, settle=0.35):
                clicked_confirm = True
                time.sleep(0.15)
                continue

            if clicked_confirm:
                ok_button = self.bot.vision.wait_for_any(["ok_button"], min(self.bot.button_threshold, 0.72), timeout=0.6, interval=0.15)
                if ok_button:
                    logging.info("Club transfers level follow-up confirm detected: %s (score=%.3f)", ok_button.name, ok_button.score)
                    self.bot.click_match(ok_button, settle=0.3)
                    time.sleep(CLUB_TRANSFERS_LEVEL_SETTLE_SECONDS)
                    advanced, followup_screenshot = self._wait_for_expected_step("sponsor_selection", timeout=CLUB_TRANSFERS_LEVEL_FOLLOWUP_SECONDS)
                    if advanced:
                        logging.info("Club transfers level post-confirm detected sponsor_selection")
                        return self.run_sponsor_selection(assume_detected=True)
                    continue

            if self.bot.find_main_screen_in_screenshot(screenshot):
                logging.info("Club transfers level flow returned to creative mode main screen")
                return True

            time.sleep(0.15)

        logging.warning("Club transfers level handling timed out without leaving the level-selection screen")
        return False

    def run_sponsor_selection(self, assume_detected: bool = False) -> bool:
        self.mark_active()
        if not self.bot.check_runtime_health():
            return False
        corrected = self._dispatch_visible_followup_step(
            ("sp_join", "final_confirm", "creative_mode_main"),
            log_prefix="Sponsor selection flow",
        )
        if corrected is not None:
            return corrected
        if not assume_detected and not self.bot.is_sponsor_selection_screen():
            return False

        logging.info("Sponsor selection screen detected, confirming directly")
        button = self.bot.click_named_button(FINAL_CONFIRM_BUTTONS, timeout=4.0, settle=0.5)
        if not button:
            logging.warning("Sponsor selection confirm button not found")
            return False

        time.sleep(SPONSOR_SELECTION_SETTLE_SECONDS)
        deadline = time.time() + SPONSOR_SELECTION_FOLLOWUP_SECONDS
        while time.time() < deadline:
            if not self.bot.check_runtime_process_only():
                return False

            followup_screenshot = self.bot.vision.capture()
            if self.bot.find_sp_join_screen_in_screenshot(followup_screenshot):
                logging.info("Sponsor selection handoff detected sp_join")
                return self.run_sp_join(screenshot=followup_screenshot, assume_detected=True)
            if self.bot.find_final_confirm_screen_in_screenshot(followup_screenshot):
                logging.info("Sponsor selection flow has already advanced to final_confirm, continuing inline")
                return self.run_final_confirm(assume_detected=True)
            if self.bot.find_main_screen_in_screenshot(followup_screenshot):
                logging.info("Sponsor selection flow returned directly to creative mode main screen")
                return True
            time.sleep(NEW_SEASON_FOLLOWUP_POLL_INTERVAL_SECONDS)
        return False

    def select_sp_join_candidates(self, screenshot, max_select: int = 3) -> int:
        belong_matches = self.bot.vision.match_all(
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
            click_x = slot_x
            click_y = slot_y + SP_JOIN_SLOT_CLICK_OFFSET_Y
            self.bot.window.click_client(click_x, click_y, settle=0.9)
            selected += 1
            logging.info(
                "Selected SP player slot using adjusted click target (%s, %s) from slot center (%s, %s), total=%s",
                click_x,
                click_y,
                slot_x,
                slot_y,
                selected,
            )
            if selected >= max_select:
                break
        return selected

    def scroll_sp_join_list_to_bottom(self) -> None:
        rect = self.bot.window.client_rect_screen()
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
            self.bot.window.scroll_client(x, y, SP_JOIN_SCROLL_DELTA, settle=0.18)

    def apply_sp_join_filter(self) -> bool:
        logging.info("Applying SP join filter before selecting players")
        entrance = self.bot.click_named_button(SP_JOIN_FILTER_ENTRANCES, timeout=5.0, settle=1.0)
        if not entrance:
            logging.warning("SP join filter entrance not found")
            return False

        ok = self.bot.vision.wait_for_any(CONFIRM_BUTTONS, min(self.bot.button_threshold, 0.72), timeout=4.0, interval=0.3)
        if not ok:
            logging.warning("Confirm button not found after opening the SP join filter")
            return False

        self.bot.click_match(ok, settle=1.0)
        return True

    def run_sp_join_followup_confirms(self) -> bool:
        deadline = time.time() + SP_JOIN_CONFIRM_HANDOFF_SECONDS
        confirm_clicks = 0

        while time.time() < deadline and confirm_clicks < SP_JOIN_CONFIRM_MAX_CLICKS:
            if not self.bot.check_runtime_process_only():
                return False

            screenshot = self.bot.vision.capture()

            if self.bot.find_main_screen_in_screenshot(screenshot):
                logging.info("SP join follow-up returned to creative mode main screen")
                return True

            confirm = self.bot.vision.match_best(
                screenshot,
                FINAL_CONFIRM_BUTTONS + CONFIRM_BUTTONS,
                min(self.bot.button_threshold, 0.72),
            )
            if confirm:
                confirm_clicks += 1
                logging.info(
                    "SP join follow-up confirm detected: %s (score=%.3f), click %s/%s",
                    confirm.name,
                    confirm.score,
                    confirm_clicks,
                    SP_JOIN_CONFIRM_MAX_CLICKS,
                )
                self.bot.click_match(confirm, settle=0.25)
                continue

            next_step = self.bot.detect_new_season_step_in_screenshot(screenshot)
            if next_step == "final_confirm":
                logging.info("SP join follow-up advanced into final_confirm, continuing in the same new-season flow")
                return self.run_final_confirm(assume_detected=True)

            time.sleep(NEW_SEASON_FOLLOWUP_POLL_INTERVAL_SECONDS)

        return True

    def run_sp_join(self, screenshot=None, assume_detected: bool = False) -> bool:
        self.mark_active()
        if not self.bot.check_runtime_health():
            return False
        corrected = self._dispatch_visible_followup_step(
            ("final_confirm", "creative_mode_main"),
            screenshot=screenshot,
            log_prefix="SP join flow",
        )
        if corrected is not None:
            return corrected
        if not assume_detected and not self.bot.is_sp_join_screen():
            return False

        logging.info("SP join screen detected, applying filter and selecting up to 3 available SP players")
        self.apply_sp_join_filter()
        screenshot = self.bot.vision.capture()
        selected = self.select_sp_join_candidates(screenshot, max_select=3)
        if selected == 0:
            logging.info("No selectable SP players found in the initial view, scrolling up to three times and retrying")
            self.scroll_sp_join_list_to_bottom()
            screenshot = self.bot.vision.capture()
            selected = self.select_sp_join_candidates(screenshot, max_select=3)
        logging.info("SP player selection finished, selected=%s", selected)

        join_button = self.bot.click_named_button(SP_JOIN_BUTTONS, timeout=5.0, settle=1.0)
        if not join_button:
            logging.warning("SP join button not found")
            return False

        time.sleep(SP_JOIN_SETTLE_SECONDS)
        if not self.run_sp_join_followup_confirms():
            return False
        advanced, followup_screenshot = self._wait_for_expected_step("final_confirm", timeout=SP_JOIN_CONFIRM_HANDOFF_SECONDS)
        if advanced:
            logging.info("SP join handoff detected final_confirm")
            return self.run_final_confirm(assume_detected=True)
        return False

    def run_final_confirm(self, assume_detected: bool = False) -> bool:
        self.mark_active()
        if not self.bot.check_runtime_health():
            return False
        current_screenshot = self.bot.vision.capture()
        if self.bot.find_main_screen_in_screenshot(current_screenshot):
            logging.info("Final confirm flow has already returned to creative mode main screen, handing off inline")
            return self.bot.main_flow.run(30.0, screenshot=current_screenshot, assume_main_visible=True)
        if not assume_detected and not self.bot.is_final_confirm_screen():
            return False

        logging.info("Final confirm screen detected, confirming new season")
        button = self.bot.click_named_button(FINAL_CONFIRM_BUTTONS, timeout=5.0, settle=1.0)
        if not button:
            logging.warning("Final confirm button not found")
            fallback_screenshot = self.bot.vision.capture()
            if self.bot.find_main_screen_in_screenshot(fallback_screenshot):
                logging.info("Final confirm button disappeared because creative mode main is already visible, handing off inline")
                return self.bot.main_flow.run(30.0, screenshot=fallback_screenshot, assume_main_visible=True)
            return False

        time.sleep(FINAL_CONFIRM_SETTLE_SECONDS)
        ok_chs = self.bot.vision.wait_for_any(["ok_chs_button"], min(self.bot.button_threshold, 0.72), timeout=2.5, interval=0.2)
        if ok_chs:
            logging.info("Final confirm follow-up dialog detected: %s (score=%.3f)", ok_chs.name, ok_chs.score)
            self.bot.click_match(ok_chs, settle=0.35)
        self.bot.last_final_confirm_time = time.time()

        deadline = time.time() + FINAL_CONFIRM_TO_MAIN_HANDOFF_SECONDS
        while time.time() < deadline:
            if not self.bot.check_runtime_process_only():
                return False

            screenshot = self.bot.vision.capture()
            if self.bot.find_main_screen_in_screenshot(screenshot):
                logging.info("Final confirm handoff returned directly to creative mode main screen, dispatching inline to main flow")
                return self.bot.main_flow.run(30.0, screenshot=screenshot, assume_main_visible=True)

            if self.handle_priority_confirm(timeout=0.2, settle=0.2):
                continue

            time.sleep(FINAL_CONFIRM_TO_MAIN_POLL_INTERVAL_SECONDS)
        return True

    def run(self, screenshot=None, fast_dispatch: bool = False) -> bool:
        self.mark_active()
        if fast_dispatch:
            if not self.bot.check_runtime_process_only():
                return False
        elif not self.bot.check_runtime_health():
            return False
        current = screenshot if screenshot is not None else self.bot.vision.capture()
        step = self.bot.detect_new_season_step_in_screenshot(current)
        if not step:
            return False
        return self._run_chain(initial_step=step, screenshot=current, fast_dispatch=fast_dispatch)
