from __future__ import annotations

import logging
import time

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
SP_JOIN_SCROLL_RATIO = (0.82, 0.52)
SP_JOIN_SCROLL_STEPS_TO_BOTTOM = 7
SP_JOIN_SCROLL_DELTA = -120
FINAL_CONFIRM_BUTTONS = ["final_confirm_ok_button", "final_confirm_ok_button2"]
CLUB_TRANSFERS_MIN_CLICK_COOLDOWN_SECONDS = 1.0
FINAL_CONFIRM_TO_SP_JOIN_HANDOFF_SECONDS = 20.0
FINAL_CONFIRM_TO_SP_JOIN_POLL_INTERVAL_SECONDS = 0.2
NEW_SEASON_FOLLOWUP_POLL_INTERVAL_SECONDS = 0.2
CLUB_TRANSFERS_LEVEL_FOLLOWUP_SECONDS = 10.0
SP_JOIN_CONFIRM_HANDOFF_SECONDS = 15.0
SP_JOIN_CONFIRM_MAX_CLICKS = 3

NEW_SEASON_STEP_LABELS = {
    "club_transfers": "club transfers",
    "club_transfers_level": "club transfers level",
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

    def _dispatch_step(self, step: str, screenshot=None, fast_dispatch: bool = False) -> bool:
        self.bot.set_active_flow("new_season")
        logging.info("New season flow step: %s", NEW_SEASON_STEP_LABELS.get(step, step))
        if step == "club_transfers":
            return self.run_club_transfers(assume_detected=True)
        if step == "club_transfers_level":
            return self.run_club_transfers_level(screenshot=screenshot, assume_detected=True)
        if step == "final_confirm":
            return self.run_final_confirm(assume_detected=True)
        if step == "sp_join":
            return self.run_sp_join(screenshot=screenshot, assume_detected=True)
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

    def run_club_transfers(self, assume_detected: bool = False) -> bool:
        self.mark_active()
        if not self.bot.check_runtime_health():
            return False
        title = True if assume_detected else self.bot.is_club_transfers_screen()
        if not title:
            return self.run_club_transfers_level()

        logging.info("Club transfers screen detected, starting renewal flow")
        renewal = self.bot.click_named_button(CLUB_TRANSFERS_RENEWAL_BUTTONS, timeout=5.0, settle=1.0)
        if not renewal:
            logging.warning("Club transfers renewal button not found")
            return False

        if self.handle_priority_confirm(timeout=2.0, settle=0.6):
            time.sleep(0.2)

        deadline = time.time() + 6.0
        while time.time() < deadline:
            if not self.bot.check_runtime_health():
                return False
            screenshot = self.bot.vision.capture()
            if self.bot.find_club_transfers_level_title_in_screenshot(screenshot) or self.bot.find_club_transfers_level_screen_in_screenshot(screenshot):
                logging.info("Club transfers flow advanced into the level-selection screen")
                return self.run_club_transfers_level(screenshot=screenshot, assume_detected=True)
            next_step = self.bot.detect_new_season_step_in_screenshot(screenshot)
            if next_step in {"final_confirm", "sp_join"}:
                logging.info("Club transfers flow advanced directly into %s", next_step)
                return self._dispatch_step(next_step, screenshot=screenshot, fast_dispatch=True)
            if self.handle_priority_confirm(timeout=0.5, settle=0.4):
                continue
            if self.run_club_transfers_level():
                return True
            self.bot.handle_global_priority_buttons(max_clicks=1)
            time.sleep(0.4)
        return True

    def run_club_transfers_level(self, screenshot=None, assume_detected: bool = False) -> bool:
        self.mark_active()
        if not self.bot.check_runtime_health():
            return False
        screenshot = screenshot if screenshot is not None else self.bot.vision.capture()
        level_screen = True if assume_detected else (
            self.bot.find_club_transfers_level_screen_in_screenshot(screenshot) or self.bot.find_club_transfers_level_title_in_screenshot(screenshot)
        )
        if not level_screen:
            return False

        deadline = time.time() + 5.0
        while time.time() < deadline:
            screenshot = self.bot.vision.capture()
            still_level = self.bot.find_club_transfers_level_screen_in_screenshot(screenshot) or self.bot.find_club_transfers_level_title_in_screenshot(screenshot)
            if not still_level:
                next_step = self.bot.detect_new_season_step_in_screenshot(screenshot)
                if next_step:
                    logging.info("Club transfers level screen has advanced to %s", next_step)
                    return self._dispatch_step(next_step, screenshot=screenshot, fast_dispatch=True)
                if self.bot.find_main_screen_in_screenshot(screenshot):
                    return True
                followup_step, followup_screenshot = self._wait_for_followup_step({"final_confirm", "sp_join"}, timeout=CLUB_TRANSFERS_LEVEL_FOLLOWUP_SECONDS)
                if followup_step == "creative_mode_main":
                    return True
                if followup_step:
                    logging.info("Club transfers level handoff detected %s", followup_step)
                    return self._dispatch_step(followup_step, screenshot=followup_screenshot, fast_dispatch=True)
                time.sleep(0.2)
                continue

            now = time.time()
            if now - self.bot.last_club_transfers_min_click_time >= CLUB_TRANSFERS_MIN_CLICK_COOLDOWN_SECONDS:
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
                time.sleep(0.15)

            if self.handle_priority_confirm(timeout=0.8, settle=0.35):
                time.sleep(0.15)
                continue

            if self.bot.find_main_screen_in_screenshot(screenshot):
                logging.info("Club transfers level flow returned to creative mode main screen")
                return True

            time.sleep(0.15)

        logging.warning("Club transfers level handling timed out without leaving the level-selection screen")
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
            self.bot.window.click_client(slot_x, slot_y, settle=0.8)
            selected += 1
            logging.info("Selected SP player slot at (%s, %s), total=%s", slot_x, slot_y, selected)
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
            if next_step and next_step != "sp_join":
                logging.info("SP join follow-up advanced into %s, continuing in the same new-season flow", next_step)
                return self._dispatch_step(next_step, screenshot=screenshot, fast_dispatch=True)

            time.sleep(NEW_SEASON_FOLLOWUP_POLL_INTERVAL_SECONDS)

        return True

    def run_sp_join(self, screenshot=None, assume_detected: bool = False) -> bool:
        self.mark_active()
        if not self.bot.check_runtime_health():
            return False
        if not assume_detected and not self.bot.is_sp_join_screen():
            return False

        logging.info("SP join screen detected, applying filter and selecting up to 3 available SP players")
        self.apply_sp_join_filter()
        screenshot = self.bot.vision.capture()
        selected = self.select_sp_join_candidates(screenshot, max_select=3)
        if selected == 0:
            logging.info("No selectable SP players found in the initial view, scrolling to the bottom and retrying")
            self.scroll_sp_join_list_to_bottom()
            screenshot = self.bot.vision.capture()
            selected = self.select_sp_join_candidates(screenshot, max_select=3)
        logging.info("SP player selection finished, selected=%s", selected)

        join_button = self.bot.click_named_button(SP_JOIN_BUTTONS, timeout=5.0, settle=1.0)
        if not join_button:
            logging.warning("SP join button not found")
            return False

        return self.run_sp_join_followup_confirms()

    def run_final_confirm(self, assume_detected: bool = False) -> bool:
        self.mark_active()
        if not self.bot.check_runtime_health():
            return False
        if not assume_detected and not self.bot.is_final_confirm_screen():
            return False

        logging.info("Final confirm screen detected, confirming new season")
        self.bot.window.move_cursor_client(x_ratio=0.08, y_ratio=0.08)
        button = self.bot.click_named_button(FINAL_CONFIRM_BUTTONS, timeout=5.0, settle=1.0)
        if not button:
            logging.warning("Final confirm button not found, falling back to generic confirm buttons")
            generic_ok = self.bot.vision.wait_for_any(
                CONFIRM_BUTTONS,
                min(self.bot.button_threshold, 0.72),
                timeout=2.5,
                interval=0.2,
            )
            if not generic_ok:
                return False
            self.bot.click_match(generic_ok, settle=0.8)

        self.bot.window.move_cursor_client(x_ratio=0.08, y_ratio=0.08)
        for _ in range(4):
            if not self.bot.handle_global_priority_buttons(max_clicks=1):
                break
        self.bot.last_final_confirm_time = time.time()

        deadline = time.time() + FINAL_CONFIRM_TO_SP_JOIN_HANDOFF_SECONDS
        while time.time() < deadline:
            if not self.bot.check_runtime_process_only():
                return False

            screenshot = self.bot.vision.capture()
            sp_join = self.bot.find_sp_join_screen_in_screenshot(screenshot)
            if sp_join:
                logging.info("Final confirm handoff detected SP join immediately, continuing in the same new-season flow")
                return self.run_sp_join(screenshot=screenshot, assume_detected=True)

            if self.handle_priority_confirm(timeout=0.2, settle=0.2):
                continue

            next_step = self.bot.detect_new_season_step_in_screenshot(screenshot)
            if next_step == "sp_join":
                logging.info("Final confirm handoff detected SP join via new-season step check")
                return self.run_sp_join(screenshot=screenshot, assume_detected=True)
            if next_step and next_step != "final_confirm":
                logging.info("Final confirm handoff advanced into %s, continuing in the same new-season flow", next_step)
                return self._dispatch_step(next_step, screenshot=screenshot, fast_dispatch=True)

            if self.bot.find_main_screen_in_screenshot(screenshot):
                logging.info("Final confirm handoff returned directly to creative mode main screen")
                return True

            time.sleep(FINAL_CONFIRM_TO_SP_JOIN_POLL_INTERVAL_SECONDS)
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
        return self._dispatch_step(step, screenshot=current, fast_dispatch=fast_dispatch)
