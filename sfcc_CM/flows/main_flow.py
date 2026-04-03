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


REGION_WIDE_TOP = ScreenRegion(0.0, 0.0, 1.0, 0.32)
REGION_TOP_RIGHT = ScreenRegion(0.72, 0.0, 1.0, 0.24)
REGION_BOTTOM_RIGHT = ScreenRegion(0.56, 0.56, 1.0, 1.0)
REGION_CONFIRM_CHAIN = ScreenRegion(0.46, 0.48, 1.0, 1.0)
SPECIAL_TRAINING_EXECUTE_REGION = ScreenRegion(0.72, 0.78, 1.0, 1.0)
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
SEASON_END_OK_BUTTONS = [
    "ok_button",
    "ok_button2",
    "ok_button3",
]
SPECIAL_TRAINING_RESET_BUTTONS = ["special_training_reset_all_button", "special_training_reset_all_button2"]
SPECIAL_TRAINING_RECOMMEND_BUTTONS = ["special_training_recommend_button", "special_training_recommend_button2"]
SPECIAL_TRAINING_EXECUTE_BUTTONS = ["special_training_execute_button", "special_training_execute_button2"]
MAIN_SCREEN_SCHEDULE_VARIANT_COUNT = 3
POST_SCHEDULE_CONFIRM_BURST_SECONDS = 6.0
POST_SCHEDULE_CONFIRM_BURST_INTERVAL_SECONDS = 0.12
POST_SCHEDULE_CONFIRM_BURST_MISS_LIMIT = 6
POST_SCHEDULE_OK_CHAIN_SECONDS = 10.0
POST_SCHEDULE_OK_CHAIN_TARGET_CLICKS = 2
MATCH_SEQUENCE_TITLE_TEXT = ("比赛开始",)
MATCH_SEQUENCE_RESULT_BUTTONS = ["match_result_button"]
MATCH_SEQUENCE_STICKY_SECONDS = 25.0
SEASON_END_TITLE_TEXT = ("\u68a6\u5e7b\u7403\u961f",)
SEASON_END_STICKY_SECONDS = 25.0
SEASON_END_TO_NEW_SEASON_WAIT_SECONDS = 8.0
SEASON_END_TO_NEW_SEASON_POLL_SECONDS = 0.2
MAIN_FOLLOWUP_POLL_SECONDS = 0.2
MAIN_FOLLOWUP_WAIT_SECONDS = 5.0
POST_SCHEDULE_TRANSITION_GRACE_SECONDS = 2.0
FORMAL_MAIN_STEPS = (
    "creative_mode_main",
    "special_training_settings",
    "special_training_result",
    "event_dialog",
    "match_sequence",
    "match_reward",
    "season_end",
)
FORMAL_MAIN_STEP_LABELS = {
    "creative_mode_main": "creative mode main",
    "special_training_settings": "special training settings",
    "special_training_result": "special training result",
    "event_dialog": "event dialog",
    "match_sequence": "match sequence",
    "match_reward": "match reward",
    "season_end": "season end",
}


class MainFlow:
    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self.last_match_sequence_time = 0.0
        self.last_season_end_time = 0.0

    def detect_step(self, screenshot) -> str | None:
        if (
            self.bot.find_login_screen_in_screenshot(screenshot)
            or self.bot.find_game_main_screen_in_screenshot(screenshot)
            or self.bot.find_save_selection_screen_in_screenshot(screenshot)
        ):
            return None

        if self.bot.detect_new_season_step_in_screenshot(screenshot):
            return None

        if self._is_season_end_screen(screenshot):
            return "season_end"

        if self.bot.find_match_reward_screen_in_screenshot(screenshot):
            return "match_reward"

        if self._is_match_sequence_screen(screenshot):
            return "match_sequence"

        if self.bot.find_special_training_result_screen_in_screenshot(screenshot):
            return "special_training_result"

        if self.bot.find_special_training_title_in_screenshot(screenshot):
            return "special_training_settings"

        if (
            self.bot.vision.match_best_in_region(
                screenshot,
                ["log", "log2"],
                min(self.bot.button_threshold, 0.72),
                REGION_TOP_RIGHT,
            )
            or self.bot.find_event_choice_in_screenshot(screenshot)
            or self.bot.vision.match_best(
                screenshot,
                ["skip_button", "skip_button2"],
                min(self.bot.button_threshold, 0.72),
            )
        ):
            return "event_dialog"

        if self.bot.find_main_screen_in_screenshot(screenshot) or self.bot.should_trust_main_screen(screenshot):
            return "creative_mode_main"

        return None

    def matches_any_step(self, screenshot) -> bool:
        return self.detect_step(screenshot) is not None

    def matches(self, screenshot) -> bool:
        return self.matches_any_step(screenshot)

    def _continue_from_followup(self, current_step: str, max_wait_seconds: float) -> bool:
        allowed_steps = tuple(step for step in FORMAL_MAIN_STEPS if step != current_step)
        return self._continue_to_allowed_steps(
            allowed_steps,
            max_wait_seconds,
            log_prefix=f"Main flow step {current_step}",
            timeout_seconds=MAIN_FOLLOWUP_WAIT_SECONDS,
            allow_no_transition=True,
        )

    def _continue_to_allowed_steps(
        self,
        allowed_steps: tuple[str, ...],
        max_wait_seconds: float,
        *,
        log_prefix: str,
        timeout_seconds: float | None = None,
        allow_no_transition: bool = False,
    ) -> bool:
        deadline = time.time() + min(max_wait_seconds, timeout_seconds if timeout_seconds is not None else 8.0)
        while time.time() < deadline:
            if not self.bot.check_runtime_process_only():
                return False

            screenshot = self.bot.vision.capture()
            new_season_step = self.bot.new_season_flow.detect_step(screenshot)
            if new_season_step:
                logging.info("%s handed off directly into new-season step %s", log_prefix, new_season_step)
                return self.bot.new_season_flow.run_step(
                    new_season_step,
                    screenshot=screenshot,
                    fast_dispatch=True,
                )

            step = self.detect_step(screenshot)
            if step in allowed_steps:
                if step == "creative_mode_main":
                    logging.info("%s returned to creative mode main screen", log_prefix)
                    return True
                logging.info("%s continued directly into %s", log_prefix, step)
                return self._dispatch_formal_step(
                    step,
                    max_wait_seconds,
                    screenshot=screenshot,
                    assume_main_visible=(step == "creative_mode_main"),
                )

            time.sleep(MAIN_FOLLOWUP_POLL_SECONDS)

        if allow_no_transition:
            logging.info("%s did not expose a new formal follow-up step within the short follow-up window", log_prefix)
            return True

        logging.warning("%s did not reach any allowed follow-up step within the expected window", log_prefix)
        return False

    def _dispatch_formal_step(
        self,
        step: str,
        max_wait_seconds: float,
        *,
        screenshot=None,
        assume_main_visible: bool = False,
    ) -> bool:
        self.bot.set_active_flow("main")
        logging.info("Main flow step: %s", FORMAL_MAIN_STEP_LABELS.get(step, step))
        if step == "creative_mode_main":
            if self.fast_path(max_wait_seconds, screenshot=screenshot, assume_main_visible=assume_main_visible):
                return True
            return self.standard_path(max_wait_seconds)

        if step in {"special_training_settings", "special_training_result"}:
            if not self.run_special_training_fast(screenshot=screenshot):
                return False
            followup_screenshot = self.bot.vision.capture()
            if self.bot.find_main_screen_in_screenshot(followup_screenshot) or self.bot.should_trust_main_screen(followup_screenshot):
                logging.info("Main flow special-training step returned to main screen, continuing directly with fast advance schedule")
                return self.advance_schedule_fast(max_wait_seconds)
            return self._continue_from_followup(step, max_wait_seconds)

        if step == "event_dialog":
            handled = self.bot.handle_post_schedule_events_fast(max_clicks=8)
            if not handled and screenshot is not None:
                handled = self.bot.handle_story_dialog_fast(screenshot=screenshot, attempts=4)
            if not handled:
                return False
            return self._continue_to_allowed_steps(
                tuple(candidate for candidate in FORMAL_MAIN_STEPS if candidate != "event_dialog"),
                max_wait_seconds,
                log_prefix="Event-dialog flow",
                timeout_seconds=MAIN_FOLLOWUP_WAIT_SECONDS,
                allow_no_transition=True,
            )

        if step == "match_sequence":
            if not self._handle_match_sequence(screenshot if screenshot is not None else self.bot.vision.capture()):
                return False
            return self._continue_to_allowed_steps(
                ("match_reward", "creative_mode_main"),
                max_wait_seconds,
                log_prefix="Match-sequence flow",
            )

        if step == "match_reward":
            if not self.bot.handle_match_reward_screen():
                return False
            return self._continue_to_allowed_steps(
                tuple(candidate for candidate in FORMAL_MAIN_STEPS if candidate != "match_reward"),
                max_wait_seconds,
                log_prefix="Match-reward flow",
                timeout_seconds=MAIN_FOLLOWUP_WAIT_SECONDS,
                allow_no_transition=True,
            )

        if step == "season_end":
            if not self.bot.handle_league_result_screen():
                return False
            return self._continue_to_allowed_steps(
                ("creative_mode_main",),
                max_wait_seconds,
                log_prefix="Season-end flow",
                timeout_seconds=SEASON_END_TO_NEW_SEASON_WAIT_SECONDS,
                allow_no_transition=True,
            )

        return False

    def _is_match_sequence_screen(self, screenshot) -> bool:
        title = self.bot._match_ocr_title(
            screenshot,
            MATCH_SEQUENCE_TITLE_TEXT,
            REGION_WIDE_TOP,
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
            REGION_WIDE_TOP,
            min_score=0.35,
        )
        if title:
            self.last_season_end_time = time.time()
            return True

        if time.time() - self.last_season_end_time <= SEASON_END_STICKY_SECONDS:
            if self.bot.detect_new_season_step_in_screenshot(screenshot):
                return False
            confirm_button = self._find_season_end_confirm_button(screenshot)
            if confirm_button:
                return True
        return False

    def _find_season_end_confirm_button(self, screenshot):
        return self.bot.vision.match_best_in_region(
            screenshot,
            SEASON_END_OK_BUTTONS,
            min(self.bot.button_threshold, 0.72),
            REGION_CONFIRM_CHAIN,
        )

    def _find_post_schedule_transition_signal(self, screenshot):
        close_button = self.bot.vision.match_best(
            screenshot,
            ["close_button"],
            min(self.bot.button_threshold, 0.72),
        )
        if close_button:
            return close_button

        quick_button = self.bot.vision.match_best_in_region(
            screenshot,
            POST_SCHEDULE_CONFIRM_BUTTONS,
            min(self.bot.button_threshold, 0.72),
            REGION_CONFIRM_CHAIN,
        )
        if quick_button:
            return quick_button

        event_dialog = self.bot.vision.match_best_in_region(
            screenshot,
            ["log", "log2"],
            min(self.bot.dialog_threshold, 0.72),
            REGION_TOP_RIGHT,
        )
        if event_dialog:
            return event_dialog

        skip_button = self.bot.vision.match_best(
            screenshot,
            ["skip_button", "skip_button2"],
            min(self.bot.button_threshold, 0.72),
        )
        if skip_button:
            return skip_button

        event_choice = self.bot.find_event_choice_in_screenshot(screenshot)
        if event_choice:
            return event_choice

        return None

    def _handle_wait_followup_step(self, screenshot, max_wait_seconds: float) -> bool | None:
        step = self.detect_step(screenshot)
        if step == "creative_mode_main":
            logging.info("Wait-for-main detected creative mode main screen via formal main-flow step")
            return True
        if step:
            logging.info("Wait-for-main detected main-flow step %s, continuing inline", step)
            return self._dispatch_formal_step(step, max_wait_seconds, screenshot=screenshot)

        new_season_step = self.bot.new_season_flow.detect_step(screenshot)
        if new_season_step:
            logging.info("Wait-for-main detected new-season step %s, dispatching inline", new_season_step)
            return self.bot.new_season_flow.run_step(
                new_season_step,
                screenshot=screenshot,
                fast_dispatch=True,
            )

        if (
            self.bot.find_login_screen_in_screenshot(screenshot)
            or self.bot.find_game_main_screen_in_screenshot(screenshot)
            or self.bot.find_save_selection_screen_in_screenshot(screenshot)
        ):
            logging.info("Wait-for-main detected a bootstrap stage")
            return False

        quick_button = self.bot.vision.match_best_in_region(
            screenshot,
            POST_SCHEDULE_CONFIRM_BUTTONS,
            min(self.bot.button_threshold, 0.72),
            REGION_CONFIRM_CHAIN,
        )
        if quick_button:
            logging.info(
                "Wait-for-main detected a quick confirm/continue: %s (score=%.3f)",
                quick_button.name,
                quick_button.score,
            )
            self.bot.click_match(quick_button, settle=0.15)
            return True

        if self.bot._handle_close_button_interrupt_from_screenshot(screenshot, min(self.bot.button_threshold, 0.72)):
            logging.info("Wait-for-main dismissed a close button while the schedule transition was active")
            return True

        return None

    def wait_for_main_screen_return(self, max_wait_seconds: float) -> bool:
        logging.info("Waiting for main transition chain to return to creative mode main")
        deadline = time.time() + max_wait_seconds
        burst_deadline = min(deadline, time.time() + POST_SCHEDULE_CONFIRM_BURST_SECONDS)
        ok_chain_deadline = min(deadline, time.time() + POST_SCHEDULE_OK_CHAIN_SECONDS)
        burst_misses = 0
        ok_chain_clicks = 0
        while time.time() < deadline:
            # Most schedule advances first surface one or two confirm dialogs.
            # Handle those quickly before falling back to the heavier stage machine.
            while time.time() < burst_deadline or (
                time.time() < ok_chain_deadline and ok_chain_clicks < POST_SCHEDULE_OK_CHAIN_TARGET_CLICKS
            ):
                screenshot = self.bot.vision.capture()
                quick_button = self.bot.vision.match_best_in_region(
                    screenshot,
                    POST_SCHEDULE_CONFIRM_BUTTONS,
                    min(self.bot.button_threshold, 0.72),
                    REGION_CONFIRM_CHAIN,
                )
                if quick_button:
                    logging.info(
                        "Post-schedule confirm burst detected: %s (score=%.3f)",
                        quick_button.name,
                        quick_button.score,
                    )
                    self.bot.click_match(quick_button, settle=0.15)
                    burst_deadline = min(deadline, time.time() + POST_SCHEDULE_CONFIRM_BURST_SECONDS)
                    ok_chain_deadline = min(deadline, time.time() + POST_SCHEDULE_OK_CHAIN_SECONDS)
                    ok_chain_clicks += 1
                    burst_misses = 0
                    continue
                if self.bot.is_main_screen_returned_quickly(screenshot) or self.bot.should_trust_main_screen(screenshot):
                    logging.info("Returned to creative mode main screen during post-schedule confirm burst")
                    return True
                if time.time() < ok_chain_deadline and ok_chain_clicks < POST_SCHEDULE_OK_CHAIN_TARGET_CLICKS:
                    time.sleep(POST_SCHEDULE_CONFIRM_BURST_INTERVAL_SECONDS)
                    continue
                burst_misses += 1
                if burst_misses >= POST_SCHEDULE_CONFIRM_BURST_MISS_LIMIT:
                    break
                time.sleep(POST_SCHEDULE_CONFIRM_BURST_INTERVAL_SECONDS)

            if not self.bot.check_runtime_health():
                return False

            screenshot = self.bot.vision.capture()
            transition_result = self._handle_wait_followup_step(screenshot, max_wait_seconds)
            if transition_result is True:
                burst_deadline = min(deadline, time.time() + POST_SCHEDULE_CONFIRM_BURST_SECONDS)
                ok_chain_deadline = min(deadline, time.time() + POST_SCHEDULE_OK_CHAIN_SECONDS)
                burst_misses = 0
                ok_chain_clicks = 0
                if self.bot.find_main_screen_in_screenshot(self.bot.vision.capture()) or self.bot.should_trust_main_screen():
                    return True
                continue
            if transition_result is False:
                return False

            if self.bot.is_main_screen_returned_quickly(screenshot) or self.bot.should_trust_main_screen(screenshot):
                logging.info("Returned to creative mode main screen")
                return True

            # Auto-progress stage: do nothing while the game is advancing on its own.
            time.sleep(0.2)

        self.bot.vision.save_debug_screenshot("wait_main_screen_timeout")
        logging.warning("Timed out waiting for main transition chain to return to creative mode main")
        return False

    def run_special_training(self) -> bool:
        if not self.bot.check_runtime_health():
            return False
        initial_screenshot = self.bot.vision.capture()
        result_screen = self.bot.find_special_training_result_screen_in_screenshot(initial_screenshot)
        settings_screen = self.bot.find_special_training_title_in_screenshot(initial_screenshot)
        if not result_screen and not settings_screen and not self.bot.try_enter_special_training():
            return False
        current_screenshot = self.bot.vision.capture()
        result_screen = self.bot.find_special_training_result_screen_in_screenshot(current_screenshot)
        if result_screen:
            logging.info("Special training result screen detected via %s, leaving immediately", result_screen.name)
            self.bot.leave_special_training()
            self.bot.last_special_training_run_time = time.time()
            return True

        settings_screen = self.bot.find_special_training_title_in_screenshot(current_screenshot)
        if not settings_screen:
            logging.warning("Special training screen was entered, but the settings/result title could not be confirmed")
            return False

        reset_match = self.bot.click_named_button(SPECIAL_TRAINING_RESET_BUTTONS, timeout=1.5, settle=0.45)
        if reset_match:
            self.bot.handle_confirm_dialog("special_training_reset_all_confirm_dialog")
        else:
            logging.info("Reset-all button not found, continuing")

        recommend_match = self.bot.click_named_button(SPECIAL_TRAINING_RECOMMEND_BUTTONS, timeout=1.5, settle=0.45)
        if not recommend_match:
            logging.warning("Recommend button not found")

        execute_match = self.bot.click_named_button(SPECIAL_TRAINING_EXECUTE_BUTTONS, timeout=1.5, settle=0.45)
        if execute_match:
            self.bot.handle_confirm_dialog("special_training_execute_confirm_dialog")
            self.bot.handle_optional_confirm_dialog("special_training_execute_confirm_next_dialog")
        else:
            logging.warning("Execute training button not found")

        returned_to_main = self.bot.leave_special_training()
        self.bot.last_special_training_run_time = time.time()
        if returned_to_main:
            logging.info("Standard special-training flow returned to main screen, continuing directly with fast advance schedule")
            return self.advance_schedule_fast(max_wait_seconds=90.0)
        return True

    def run_special_training_fast(self, screenshot=None, assume_main_visible: bool = False) -> bool:
        if not self.bot.check_runtime_process_only():
            return False
        initial_screenshot = screenshot if screenshot is not None else self.bot.vision.capture()
        result_screen = self.bot.find_special_training_result_screen_in_screenshot(initial_screenshot)
        if result_screen:
            logging.info("Fast path detected the special training result screen via %s, leaving immediately", result_screen.name)
            self.bot.leave_special_training_fast()
            self.bot.last_special_training_run_time = time.time()
            return True
        if (
            not self.bot.find_special_training_screen_in_screenshot(initial_screenshot)
            and not self.bot.try_enter_special_training_fast(
                screenshot=initial_screenshot,
                assume_main_visible=assume_main_visible,
            )
        ):
            return False

        current_screenshot = self.bot.vision.capture()
        result_screen = self.bot.find_special_training_result_screen_in_screenshot(current_screenshot)
        if result_screen:
            logging.info("Fast path detected the special training result screen via %s after entry, leaving immediately", result_screen.name)
            self.bot.leave_special_training_fast()
            self.bot.last_special_training_run_time = time.time()
            return True

        settings_screen = self.bot.find_special_training_title_in_screenshot(current_screenshot)
        settings_markers = self.bot.find_special_training_settings_markers_in_screenshot(current_screenshot)
        if not settings_screen:
            if settings_markers:
                logging.info(
                    "Fast path accepted the special training settings page via screen markers: %s (score=%.3f)",
                    settings_markers.name,
                    settings_markers.score,
                )
            else:
                logging.warning("Fast path entered special training, but the settings/result title could not be confirmed")
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

        logging.info("Fast path will only leave special training after attempting the execute action once")
        execute_match = self.bot.click_special_training_action_fast(
            SPECIAL_TRAINING_EXECUTE_BUTTONS,
            region=SPECIAL_TRAINING_EXECUTE_REGION,
            timeout=1.6,
            settle=0.35,
        )
        if execute_match:
            logging.info(
                "Fast path executed special training via %s (score=%.3f); returning afterwards",
                execute_match.name,
                execute_match.score,
            )
            self.bot.handle_confirm_dialog_fast("special_training_execute_confirm_dialog")
            self.bot.handle_optional_confirm_dialog_fast("special_training_execute_confirm_next_dialog")
        else:
            logging.warning("Fast path did not find an execute-training button after entering settings; returning without execution")

        self.bot.leave_special_training_fast()
        self.bot.last_special_training_run_time = time.time()
        return True

    def advance_schedule(self, max_wait_seconds: float) -> bool:
        left_main_screen = False
        for attempt in range(1, 9):
            if not self.bot.check_runtime_health():
                return False
            screenshot = self.bot.vision.capture()
            if self.bot.handle_fast_main_screen_interrupts(screenshot=screenshot):
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
                    assume_main_visible=True,
                )
            else:
                logging.info("Advance schedule matched via template: %s (score=%.3f)", match.name, match.score)
                action_clicked = self.bot.click_advance_schedule_action(
                    match=match,
                    settle_between=0.16,
                    assume_main_visible=True,
                )
            if not action_clicked:
                logging.warning("Advance schedule action was skipped, aborting the current advance attempt")
                return False
            self.bot.last_advance_schedule_click_time = time.time()
            time.sleep(0.4)

            self.bot.handle_fast_main_screen_interrupts()
            post_schedule_screenshot = self.bot.vision.capture()
            post_schedule_step = self.detect_step(post_schedule_screenshot)
            if post_schedule_step and post_schedule_step != "creative_mode_main":
                logging.info(
                    "Advance schedule immediately handed off into main-flow step %s without waiting for another scheduler pass",
                    post_schedule_step,
                )
                left_main_screen = True
                break
            if self.bot.new_season_flow.detect_step(post_schedule_screenshot):
                logging.info("Advance schedule immediately handed off into a new-season step without retrying the main-screen action")
                left_main_screen = True
                break
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
            confirmed_main = self.bot.is_confirmed_main_screen(screenshot) if not main_visible and not trusted_main else main_visible or trusted_main
            advance_button_visible = self.bot.find_advance_schedule_button_in_screenshot(screenshot)
            schedule_ready_main = bool(main_visible or trusted_main or advance_button_visible)
            if not main_visible and not trusted_main and not confirmed_main:
                if not schedule_ready_main:
                    self.bot.invalidate_runtime_stage("fast advance schedule precheck could not confirm main screen")
                    logging.warning("Fast advance schedule aborted because the current screen is not a confirmed creative mode main screen")
                    return False
                logging.info("Fast advance schedule is proceeding because the schedule button is visible on an otherwise weakly confirmed main screen")
            if trusted_main and not main_visible:
                logging.info("Fast advance schedule trusted recent creative mode main-screen confirmation")
                refreshed = self.bot.vision.capture()
                refreshed_advance_button = self.bot.find_advance_schedule_button_in_screenshot(refreshed)
                if not self.bot.is_confirmed_main_screen(refreshed) and not refreshed_advance_button:
                    self.bot.invalidate_runtime_stage("trusted main screen check failed before fast advance schedule click")
                    logging.warning("Fast advance schedule aborted because a second main-screen confirmation failed")
                    return False
                screenshot = refreshed
                main_visible = self.bot.find_main_screen_in_screenshot(screenshot)
            match = advance_button_visible or self.bot.find_advance_schedule_button_in_screenshot(screenshot)
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

            post_schedule_screenshot = self.bot.vision.capture()
            transition_deadline = time.time() + POST_SCHEDULE_TRANSITION_GRACE_SECONDS
            while time.time() < transition_deadline:
                post_schedule_step = self.detect_step(post_schedule_screenshot)
                if post_schedule_step and post_schedule_step != "creative_mode_main":
                    logging.info(
                        "Fast advance schedule immediately handed off into main-flow step %s without retrying the main-screen action",
                        post_schedule_step,
                    )
                    left_main_screen = True
                    break

                if self.bot.new_season_flow.detect_step(post_schedule_screenshot):
                    logging.info("Fast advance schedule immediately handed off into a new-season step without retrying the main-screen action")
                    left_main_screen = True
                    break

                transition_signal = self._find_post_schedule_transition_signal(post_schedule_screenshot)
                if transition_signal:
                    logging.info(
                        "Fast advance schedule accepted a transition signal %s (score=%.3f) and will continue waiting for the main return chain",
                        transition_signal.name,
                        transition_signal.score,
                    )
                    left_main_screen = True
                    break

                post_schedule_main_visible = self.bot.find_main_screen_in_screenshot(post_schedule_screenshot)
                post_schedule_main_trusted = self.bot.should_trust_main_screen(post_schedule_screenshot)
                if not post_schedule_main_visible and not post_schedule_main_trusted:
                    logging.info("Fast advance schedule accepted, main screen has been left")
                    left_main_screen = True
                    break

                if time.time() - self.bot.last_visual_change_time < 0.9:
                    time.sleep(0.15)
                    post_schedule_screenshot = self.bot.vision.capture()
                    continue
                break

            if left_main_screen:
                break

            if attempt == 1:
                self.bot.invalidate_runtime_stage("fast advance schedule click left the bot on main screen")
            logging.warning("Fast advance schedule click did not leave main screen, retrying (attempt %s)", attempt)
            continue

        if not left_main_screen:
            self.bot.invalidate_runtime_stage("fast advance schedule failed to leave main screen after retries")
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

        self.bot.ensure_speed_three(screenshot=screenshot)
        post_speed_screenshot = self.bot.vision.capture()
        if not self.run_special_training_fast(
            screenshot=post_speed_screenshot,
            assume_main_visible=True,
        ):
            logging.info("Fast path skipped or missed special training, continuing to schedule advance")
        return self.advance_schedule_fast(max_wait_seconds)

    def standard_path(self, max_wait_seconds: float) -> bool:
        self.bot.ensure_speed_three()
        self.run_special_training()
        return self.advance_schedule(max_wait_seconds)

    def run(self, max_wait_seconds: float, screenshot=None, assume_main_visible: bool = False) -> bool:
        current_screenshot = screenshot if screenshot is not None else self.bot.vision.capture()
        step = "creative_mode_main" if assume_main_visible else self.detect_step(current_screenshot)
        if not step:
            return False

        return self._dispatch_formal_step(
            step,
            max_wait_seconds,
            screenshot=current_screenshot,
            assume_main_visible=(step == "creative_mode_main"),
        )

    def run_after_recovery(self, max_wait_seconds: float) -> bool:
        logging.info("Recovery returned to creative mode main screen, starting season flow")
        if self.fast_path(max_wait_seconds):
            return True
        logging.info("Fast main-screen flow failed after recovery, using the standard main-screen flow")
        return self.standard_path(max_wait_seconds)
