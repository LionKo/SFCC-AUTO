from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScreenRegion:
    left_ratio: float
    top_ratio: float
    right_ratio: float
    bottom_ratio: float


REGION_BOTTOM_RIGHT = ScreenRegion(0.56, 0.56, 1.0, 1.0)
MAIN_SCREEN_BUTTONS = [
    "creative_mode_advance_schedule_button_small",
    "creative_mode_advance_schedule_button",
]
POST_SCHEDULE_CONFIRM_BUTTONS = [
    "ok_button",
    "ok_button2",
    "ok_button3",
    "ok_chs_button",
    "continue_button",
    "continue_button2",
    "continue_button3",
    "final_confirm_ok_button",
    "final_confirm_ok_button2",
]
SPECIAL_TRAINING_RESET_BUTTONS = ["special_training_reset_all_button", "special_training_reset_all_button2"]
SPECIAL_TRAINING_RECOMMEND_BUTTONS = ["special_training_recommend_button", "special_training_recommend_button2"]
SPECIAL_TRAINING_EXECUTE_BUTTONS = ["special_training_execute_button", "special_training_execute_button2"]
MAIN_SCREEN_SCHEDULE_VARIANT_COUNT = 3
POST_SCHEDULE_CONFIRM_BURST_SECONDS = 6.0
POST_SCHEDULE_CONFIRM_BURST_INTERVAL_SECONDS = 0.12
POST_SCHEDULE_CONFIRM_BURST_MISS_LIMIT = 6


class MainFlow:
    def __init__(self, bot: Any) -> None:
        self.bot = bot

    def matches(self, screenshot) -> bool:
        main = self.bot.find_main_screen_in_screenshot(screenshot)
        return bool(main or self.bot.should_trust_main_screen(screenshot) or self.bot.find_special_training_screen_in_screenshot(screenshot))

    def wait_for_main_screen_return(self, max_wait_seconds: float) -> bool:
        logging.info("Waiting for creative mode main screen to return")
        deadline = time.time() + max_wait_seconds
        burst_deadline = min(deadline, time.time() + POST_SCHEDULE_CONFIRM_BURST_SECONDS)
        burst_misses = 0
        while time.time() < deadline:
            # Most schedule advances first surface one or two confirm dialogs.
            # Handle those quickly before falling back to the heavier stage machine.
            while time.time() < burst_deadline:
                screenshot = self.bot.vision.capture()
                quick_button = self.bot.vision.match_best(
                    screenshot,
                    POST_SCHEDULE_CONFIRM_BUTTONS,
                    min(self.bot.button_threshold, 0.72),
                )
                if quick_button:
                    logging.info(
                        "Post-schedule confirm burst detected: %s (score=%.3f)",
                        quick_button.name,
                        quick_button.score,
                    )
                    self.bot.click_match(quick_button, settle=0.15)
                    burst_misses = 0
                    continue
                if self.bot.is_main_screen_returned_quickly(screenshot) or self.bot.should_trust_main_screen(screenshot):
                    logging.info("Returned to creative mode main screen during post-schedule confirm burst")
                    return True
                burst_misses += 1
                if burst_misses >= POST_SCHEDULE_CONFIRM_BURST_MISS_LIMIT:
                    break
                time.sleep(POST_SCHEDULE_CONFIRM_BURST_INTERVAL_SECONDS)

            if self.bot.handle_global_priority_buttons():
                continue
            if not self.bot.check_runtime_health():
                return False

            screenshot = self.bot.vision.capture()
            if self.bot.is_main_screen_returned_quickly(screenshot) or self.bot.should_trust_main_screen(screenshot):
                logging.info("Returned to creative mode main screen")
                return True

            # Returning to creative mode main is the common case; prefer that path
            # before treating the screen as a rarer new-season branch.
            main_visible = self.bot.find_main_screen_in_screenshot(screenshot)
            if main_visible:
                logging.info("Wait-for-main confirmed creative mode main screen before new-season fallback")
                return True

            if self.bot.handle_global_priority_buttons():
                continue

            if self.bot.handle_post_schedule_events(max_clicks=12):
                continue

            if self.bot.handle_league_result_screen():
                continue

            if self.bot.handle_connecting_screen():
                continue

            if self.bot.handle_speed_one_anywhere():
                continue

            if self.bot.handle_match_reward_screen():
                continue

            if self.bot.detect_new_season_step_in_screenshot(screenshot):
                logging.info("Wait-for-main detected a new-season stage after main-screen checks, leaving the main flow for the next scheduler pass")
                return False

            if (
                self.bot.find_login_screen_in_screenshot(screenshot)
                or self.bot.find_game_main_screen_in_screenshot(screenshot)
                or self.bot.find_save_selection_screen_in_screenshot(screenshot)
            ):
                logging.info("Wait-for-main detected a bootstrap stage, leaving the main flow for the next scheduler pass")
                return False

            if self.bot.handle_generic_confirm_fallback(min_interval=0.8):
                continue

            if not self.bot.find_any_known_operation():
                self.bot.fallback_click_when_no_operation_found()
                continue

            time.sleep(0.2)

        self.bot.vision.save_debug_screenshot("wait_main_screen_timeout")
        logging.warning("Timed out waiting for creative mode main screen to return")
        return False

    def run_special_training(self) -> bool:
        if not self.bot.check_runtime_health():
            return False
        if not self.bot.is_special_training_screen() and not self.bot.try_enter_special_training():
            return False

        reset_match = self.bot.click_named_button(SPECIAL_TRAINING_RESET_BUTTONS, timeout=5.0, settle=1.0)
        if reset_match:
            self.bot.handle_confirm_dialog("special_training_reset_all_confirm_dialog")
        else:
            logging.info("Reset-all button not found, continuing")

        recommend_match = self.bot.click_named_button(SPECIAL_TRAINING_RECOMMEND_BUTTONS, timeout=5.0, settle=1.0)
        if not recommend_match:
            logging.warning("Recommend button not found")

        execute_match = self.bot.click_named_button(SPECIAL_TRAINING_EXECUTE_BUTTONS, timeout=5.0, settle=1.0)
        if execute_match:
            self.bot.handle_confirm_dialog("special_training_execute_confirm_dialog")
            self.bot.handle_optional_confirm_dialog("special_training_execute_confirm_next_dialog")
        else:
            logging.warning("Execute training button not found")

        self.bot.leave_special_training()
        self.bot.last_special_training_run_time = time.time()
        return True

    def run_special_training_fast(self) -> bool:
        if not self.bot.check_runtime_process_only():
            return False
        if not self.bot.is_special_training_screen() and not self.bot.try_enter_special_training_fast():
            return False

        reset_match = self.bot.click_special_training_action_fast(
            SPECIAL_TRAINING_RESET_BUTTONS,
            timeout=0.9,
            settle=0.35,
        )
        if reset_match:
            self.bot.handle_confirm_dialog_fast("special_training_reset_all_confirm_dialog")

        self.bot.click_special_training_action_fast(
            SPECIAL_TRAINING_RECOMMEND_BUTTONS,
            timeout=0.9,
            settle=0.35,
        )

        execute_match = self.bot.click_special_training_action_fast(
            SPECIAL_TRAINING_EXECUTE_BUTTONS,
            timeout=0.9,
            settle=0.35,
        )
        if execute_match:
            self.bot.handle_confirm_dialog_fast("special_training_execute_confirm_dialog")
            self.bot.handle_optional_confirm_dialog_fast("special_training_execute_confirm_next_dialog")

        self.bot.leave_special_training_fast()
        self.bot.last_special_training_run_time = time.time()
        return True

    def advance_schedule(self, max_wait_seconds: float) -> bool:
        left_main_screen = False
        for attempt in range(1, 9):
            if not self.bot.check_runtime_health():
                return False
            self.bot.handle_global_priority_buttons()
            screenshot = self.bot.vision.capture()
            if not self.bot.is_confirmed_main_screen(screenshot):
                logging.warning("Advance schedule aborted because the current screen is not a confirmed creative mode main screen")
                return False
            match = self.bot.find_advance_schedule_button_in_screenshot(screenshot)
            action_clicked = False
            if not match:
                match = self.bot.click_named_button_in_region(
                    MAIN_SCREEN_BUTTONS,
                    min(self.bot.main_threshold, 0.55),
                    REGION_BOTTOM_RIGHT,
                    timeout=1.5,
                    interval=0.12,
                    settle=0.5,
                )
                if match:
                    action_clicked = True
            if not match:
                logging.warning("Advance schedule button not found in dedicated schedule ROI, using main-screen schedule hotspot fallback")
                action_clicked = self.bot.click_advance_schedule_action(
                    match=None,
                    hotspot_variant=(attempt - 1) % MAIN_SCREEN_SCHEDULE_VARIANT_COUNT,
                    settle_between=0.16,
                )
            else:
                logging.info("Advance schedule matched via template: %s (score=%.3f)", match.name, match.score)
                action_clicked = self.bot.click_advance_schedule_action(match=match, settle_between=0.16)
            if not action_clicked:
                logging.warning("Advance schedule action was skipped, aborting the current advance attempt")
                return False
            self.bot.last_advance_schedule_click_time = time.time()
            time.sleep(0.4)

            self.bot.handle_global_priority_buttons()
            self.bot.handle_post_schedule_events(max_clicks=8)
            if self.bot.is_main_screen():
                logging.warning("Advance schedule click did not leave main screen, retrying (attempt %s)", attempt)
                continue

            logging.info("Advance schedule accepted, main screen has been left")
            left_main_screen = True
            break

        if not left_main_screen:
            self.bot.vision.save_debug_screenshot("advance_schedule_leave_failed")
            logging.error("Advance schedule failed to leave main screen after repeated clicks")
            return False

        return self.wait_for_main_screen_return(max_wait_seconds)

    def advance_schedule_fast(self, max_wait_seconds: float) -> bool:
        left_main_screen = False
        for attempt in range(1, 5):
            if not self.bot.check_runtime_process_only():
                return False
            if self.bot.handle_fast_main_screen_interrupts():
                continue

            screenshot = self.bot.vision.capture()
            main_visible = self.bot.find_main_screen_in_screenshot(screenshot)
            trusted_main = self.bot.should_trust_main_screen(screenshot)
            if not main_visible and not trusted_main and not self.bot.is_confirmed_main_screen(screenshot):
                logging.warning("Fast advance schedule aborted because the current screen is not a confirmed creative mode main screen")
                return False
            if trusted_main and not main_visible:
                logging.info("Fast advance schedule trusted recent creative mode main-screen confirmation")
            match = self.bot.find_advance_schedule_button_in_screenshot(screenshot)
            action_clicked = False
            if not match:
                match = self.bot.click_named_button_in_region(
                    MAIN_SCREEN_BUTTONS,
                    min(self.bot.main_threshold, 0.55),
                    REGION_BOTTOM_RIGHT,
                    timeout=0.8,
                    interval=0.10,
                    settle=0.45,
                )
                if match:
                    action_clicked = True
                if not match:
                    logging.warning("Fast path could not find advance schedule template in dedicated schedule ROI, using schedule hotspot fallback")
                    action_clicked = self.bot.click_advance_schedule_action(
                        match=None,
                        hotspot_variant=(attempt - 1) % MAIN_SCREEN_SCHEDULE_VARIANT_COUNT,
                        settle_between=0.14,
                    )
                else:
                    logging.info("Fast path matched advance schedule via dedicated ROI template: %s (score=%.3f)", match.name, match.score)
            else:
                logging.info("Fast path matched advance schedule via dedicated ROI template: %s (score=%.3f)", match.name, match.score)
                action_clicked = self.bot.click_advance_schedule_action(
                    match=match,
                    settle_between=0.14,
                    assume_main_visible=True,
                )

            if not action_clicked:
                logging.warning("Fast advance schedule action was skipped, aborting the current advance attempt")
                return False

            self.bot.last_advance_schedule_click_time = time.time()
            time.sleep(0.35)

            self.bot.handle_post_schedule_events_fast(max_clicks=4)

            if self.bot.is_main_screen_visible():
                logging.warning("Fast advance schedule click did not leave main screen, retrying (attempt %s)", attempt)
                continue

            logging.info("Fast advance schedule accepted, main screen has been left")
            left_main_screen = True
            break

        if not left_main_screen:
            self.bot.vision.save_debug_screenshot("advance_schedule_fast_leave_failed")
            logging.error("Fast advance schedule failed to leave main screen")
            return False

        return self.wait_for_main_screen_return(max_wait_seconds)

    def fast_path(self, max_wait_seconds: float, screenshot=None, assume_main_visible: bool = False) -> bool:
        self.bot.set_active_flow("main")
        if not self.bot.check_runtime_process_only():
            return False

        screenshot = screenshot if screenshot is not None else self.bot.vision.capture()
        if not assume_main_visible and not self.bot.find_main_screen_in_screenshot(screenshot) and not self.bot.should_trust_main_screen(screenshot):
            return False
        if assume_main_visible:
            logging.info("Fast main-screen flow is trusting the caller-confirmed creative mode main screen")

        logging.info("Fast main-screen flow engaged")

        if self.bot.handle_fast_main_screen_interrupts(screenshot=screenshot):
            return True

        self.bot.ensure_speed_three()
        if not self.run_special_training_fast():
            logging.info("Fast path skipped or missed special training, continuing to schedule advance")
        return self.advance_schedule_fast(max_wait_seconds)

    def standard_path(self, max_wait_seconds: float) -> bool:
        self.bot.ensure_speed_three()
        self.run_special_training()
        return self.advance_schedule(max_wait_seconds)

    def run(self, max_wait_seconds: float, screenshot=None, assume_main_visible: bool = False) -> bool:
        if not assume_main_visible and screenshot is not None and self.bot.find_special_training_screen_in_screenshot(screenshot):
            self.bot.set_active_flow("main")
            return self.run_special_training_fast()

        main = assume_main_visible
        if not main:
            main = screenshot is not None and self.bot.find_main_screen_in_screenshot(screenshot)
        if not main and screenshot is not None and self.bot.should_trust_main_screen(screenshot):
            main = True
        if not main:
            return False

        self.bot.set_active_flow("main")
        if self.fast_path(max_wait_seconds, screenshot=screenshot, assume_main_visible=assume_main_visible):
            return True
        return self.standard_path(max_wait_seconds)

    def run_after_recovery(self, max_wait_seconds: float) -> bool:
        logging.info("Recovery returned to creative mode main screen, starting season flow")
        if self.fast_path(max_wait_seconds):
            return True
        logging.info("Fast main-screen flow failed after recovery, using the standard main-screen flow")
        return self.standard_path(max_wait_seconds)
