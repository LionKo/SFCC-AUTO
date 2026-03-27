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
MATCH_SEQUENCE_TITLE_TEXT = ("比赛开始",)
MATCH_SEQUENCE_RESULT_BUTTONS = ["match_result_button"]
MATCH_SEQUENCE_STICKY_SECONDS = 25.0
SEASON_END_TITLE_TEXT = ("\u68a6\u5e7b\u7403\u961f",)
SEASON_END_STICKY_SECONDS = 25.0


class MainFlow:
    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self.last_match_sequence_time = 0.0
        self.last_season_end_time = 0.0

    def matches(self, screenshot) -> bool:
        main = self.bot.find_main_screen_in_screenshot(screenshot)
        return bool(main or self.bot.should_trust_main_screen(screenshot) or self.bot.find_special_training_screen_in_screenshot(screenshot))

    def _is_match_sequence_screen(self, screenshot) -> bool:
        title = self.bot._match_ocr_title(
            screenshot,
            MATCH_SEQUENCE_TITLE_TEXT,
            self.bot.REGION_WIDE_TOP if hasattr(self.bot, "REGION_WIDE_TOP") else ScreenRegion(0.0, 0.0, 1.0, 0.32),
            min_score=0.35,
        )
        result_button = self.bot.vision.match_best(
            screenshot,
            MATCH_SEQUENCE_RESULT_BUTTONS,
            min(self.bot.button_threshold, 0.72),
        )
        if title or result_button:
            self.last_match_sequence_time = time.time()
            return True

        if time.time() - self.last_match_sequence_time <= MATCH_SEQUENCE_STICKY_SECONDS:
            continue_button = self.bot.vision.match_best(
                screenshot,
                POST_SCHEDULE_CONFIRM_BUTTONS,
                min(self.bot.button_threshold, 0.72),
            )
            if continue_button and not self.bot.find_match_reward_screen_in_screenshot(screenshot):
                return True
        return False

    def _handle_match_sequence(self, screenshot) -> bool:
        if not self._is_match_sequence_screen(screenshot):
            return False

        result_button = self.bot.vision.match_best(
            screenshot,
            MATCH_SEQUENCE_RESULT_BUTTONS,
            min(self.bot.button_threshold, 0.72),
        )
        if result_button:
            logging.info("Main match-sequence detected result button: %s (score=%.3f)", result_button.name, result_button.score)
            self.bot.click_match(result_button, settle=0.2)
            return True

        continue_button = self.bot.vision.match_best(
            screenshot,
            CONTINUE_BUTTONS + CONFIRM_BUTTONS,
            min(self.bot.button_threshold, 0.72),
        )
        if continue_button:
            logging.info("Main match-sequence detected continue/confirm: %s (score=%.3f)", continue_button.name, continue_button.score)
            self.bot.click_match(continue_button, settle=0.2)
            return True

        return True

    def _is_season_end_screen(self, screenshot) -> bool:
        title = self.bot._match_ocr_title(
            screenshot,
            SEASON_END_TITLE_TEXT,
            self.bot.REGION_WIDE_TOP if hasattr(self.bot, "REGION_WIDE_TOP") else ScreenRegion(0.0, 0.0, 1.0, 0.32),
            min_score=0.35,
        )
        if title:
            self.last_season_end_time = time.time()
            return True

        if time.time() - self.last_season_end_time <= SEASON_END_STICKY_SECONDS:
            if self.bot.detect_new_season_step_in_screenshot(screenshot):
                return False
            confirm_button = self.bot.vision.match_best_in_region(
                screenshot,
                POST_SCHEDULE_CONFIRM_BUTTONS,
                min(self.bot.button_threshold, 0.72),
                REGION_BOTTOM_RIGHT,
            )
            if confirm_button:
                return True
        return False

    def _handle_season_end(self, screenshot) -> bool:
        if not self._is_season_end_screen(screenshot):
            return False

        confirm_button = self.bot.vision.match_best_in_region(
            screenshot,
            POST_SCHEDULE_CONFIRM_BUTTONS,
            min(self.bot.button_threshold, 0.72),
            REGION_BOTTOM_RIGHT,
        )
        if confirm_button:
            logging.info(
                "Season-end stage detected right-side confirm: %s (score=%.3f)",
                confirm_button.name,
                confirm_button.score,
            )
            self.bot.click_match(confirm_button, settle=0.15)
            self.last_season_end_time = time.time()
            return True

        logging.info("Season-end stage is active, waiting for the next right-side confirm to appear")
        return True

    def _handle_main_chain_transition(self, screenshot) -> bool | None:
        if self._handle_season_end(screenshot):
            return True

        if self.bot.detect_new_season_step_in_screenshot(screenshot):
            logging.info("Main transition chain detected a new-season step, dispatching inline")
            return self.bot.new_season_flow.run(screenshot, fast_dispatch=True)

        if self.bot.handle_story_dialog_fast(screenshot=screenshot, attempts=3):
            return True

        if self._handle_match_sequence(screenshot):
            return True

        if self.bot.find_match_reward_screen_in_screenshot(screenshot):
            logging.info("Wait-for-main exception chain detected match reward, handling it inline")
            return self.bot.handle_match_reward_screen()

        if (
            self.bot.find_login_screen_in_screenshot(screenshot)
            or self.bot.find_game_main_screen_in_screenshot(screenshot)
            or self.bot.find_save_selection_screen_in_screenshot(screenshot)
        ):
            logging.info("Main transition chain detected a bootstrap stage")
            return False

        quick_button = self.bot.vision.match_best(
            screenshot,
            POST_SCHEDULE_CONFIRM_BUTTONS,
            min(self.bot.button_threshold, 0.72),
        )
        if quick_button:
            logging.info(
                "Main transition chain detected quick button: %s (score=%.3f)",
                quick_button.name,
                quick_button.score,
            )
            self.bot.click_match(quick_button, settle=0.15)
            return True

        return None

    def wait_for_main_screen_return(self, max_wait_seconds: float) -> bool:
        logging.info("Waiting for main transition chain to return to creative mode main")
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

            if not self.bot.check_runtime_health():
                return False

            screenshot = self.bot.vision.capture()
            transition_result = self._handle_main_chain_transition(screenshot)
            if transition_result is True:
                continue
            if transition_result is False:
                return False

            if self.bot.is_main_screen_returned_quickly(screenshot) or self.bot.should_trust_main_screen(screenshot):
                logging.info("Returned to creative mode main screen")
                return True

            # Returning to creative mode main is the common case; prefer that path
            # before treating the screen as a rarer new-season branch.
            main_visible = self.bot.find_main_screen_in_screenshot(screenshot)
            if main_visible:
                logging.info("Wait-for-main confirmed creative mode main screen before new-season fallback")
                return True

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

            # Auto-progress stage: do nothing while the game is advancing on its own.
            time.sleep(0.2)

        self.bot.vision.save_debug_screenshot("wait_main_screen_timeout")
        logging.warning("Timed out waiting for main transition chain to return to creative mode main")
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

            handled_post_schedule = self.bot.handle_post_schedule_events_fast(max_clicks=4)
            post_schedule_screenshot = self.bot.vision.capture()
            post_schedule_main_visible = self.bot.find_main_screen_in_screenshot(post_schedule_screenshot)
            post_schedule_main_trusted = self.bot.should_trust_main_screen(post_schedule_screenshot)

            if handled_post_schedule and not post_schedule_main_visible and not post_schedule_main_trusted:
                logging.info("Fast advance schedule handed off into a post-schedule exception chain without retrying the main-screen action")
                left_main_screen = True
                break

            if post_schedule_main_visible or post_schedule_main_trusted:
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
