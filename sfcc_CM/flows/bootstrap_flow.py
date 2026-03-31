from __future__ import annotations

import logging
import time
from dataclasses import dataclass

UNKNOWN_BOOTSTRAP_SETTLE_AFTER_VISUAL_CHANGE_SECONDS = 2.5
SAVE_SELECTION_MAIN_HANDOFF_TIMEOUT_SECONDS = 6.0


@dataclass(frozen=True)
class ScreenRegion:
    left_ratio: float
    top_ratio: float
    right_ratio: float
    bottom_ratio: float


REGION_TOP_RIGHT = ScreenRegion(0.72, 0.0, 1.0, 0.24)
POST_SAVE_MAIN_INTERMEDIATE_BUTTONS = [
    "continue_button",
    "continue_button2",
    "continue_button3",
    "ok_button",
    "ok_button2",
    "ok_button3",
    "ok_chs_button",
    "skip_button",
    "skip_button2",
]


class BootstrapFlow:
    def __init__(self, bot: object) -> None:
        self.bot = bot

    def _detect_post_save_new_season_step(self, screenshot):
        if self.bot.find_club_transfers_screen_in_screenshot(screenshot):
            return "club_transfers"
        if self.bot.find_club_transfers_level_screen_in_screenshot(screenshot):
            return "club_transfers_level"
        if self.bot.find_sponsor_selection_screen_in_screenshot(screenshot):
            return "sponsor_selection"
        if self.bot.find_sp_join_screen_in_screenshot(screenshot):
            return "sp_join"
        if self.bot.find_final_confirm_screen_in_screenshot(screenshot):
            return "final_confirm"
        return self.bot.detect_new_season_step_in_screenshot(screenshot)

    def _is_post_save_main_intermediate(self, screenshot) -> bool:
        if self.bot.find_match_reward_screen_in_screenshot(screenshot):
            return True
        if self.bot.vision.match_best_in_region(
            screenshot,
            ["log", "log2"],
            min(self.bot.button_threshold, self.bot.dialog_threshold, 0.72),
            REGION_TOP_RIGHT,
        ):
            return True
        if self.bot.vision.match_best(
            screenshot,
            POST_SAVE_MAIN_INTERMEDIATE_BUTTONS,
            min(self.bot.button_threshold, 0.72),
        ):
            return True
        return False

    def matches(self, screenshot) -> bool:
        if self.bot.awaiting_main_after_save_selection and self.bot.find_main_screen_in_screenshot(screenshot):
            return True
        if self.bot.awaiting_main_after_save_selection and self._detect_post_save_new_season_step(screenshot):
            return True
        if self.bot.awaiting_main_after_save_selection and self._is_post_save_main_intermediate(screenshot):
            return True
        if self.bot.awaiting_main_after_save_selection:
            return False
        if self.bot.find_login_screen_in_screenshot(screenshot):
            return True
        if self.bot.find_game_main_screen_in_screenshot(screenshot):
            return True
        if self.bot.awaiting_save_selection and self.bot.find_save_selection_screen_in_screenshot(screenshot):
            return True
        return False

    def run(
        self,
        timeout_seconds: float,
        post_login_cooldown_seconds: float,
        handoff_main_wait_seconds: float | None = None,
    ) -> bool:
        self.bot.set_active_flow("bootstrap")
        logging.info("Running bootstrap flow to reach creative mode save entry")
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if not self.bot.check_runtime_health():
                return False
            screenshot = self.bot.vision.capture()
            post_login_wait = (
                time.time() - self.bot.last_bootstrap_login_click_time
                if self.bot.last_bootstrap_login_click_time > 0
                else 0.0
            )
            login_cooldown_active = 0.0 < post_login_wait < post_login_cooldown_seconds

            if self.bot.awaiting_save_selection and self.bot.find_main_screen_in_screenshot(screenshot):
                self.bot.set_active_flow("main")
                self.bot.awaiting_save_selection = False
                self.bot.awaiting_main_after_save_selection = False
                self.bot.last_bootstrap_login_click_time = 0.0
                self.bot.last_bootstrap_to_main_time = time.time()
                logging.info("Bootstrap flow reached creative mode main screen")
                return True

            if self.bot.awaiting_main_after_save_selection:
                handoff_wait = (
                    time.time() - self.bot.last_save_selection_click_time
                    if self.bot.last_save_selection_click_time > 0
                    else 0.0
                )
                new_season_step = self._detect_post_save_new_season_step(screenshot)
                if new_season_step:
                    self.bot.awaiting_main_after_save_selection = False
                    self.bot.last_bootstrap_login_click_time = 0.0
                    self.bot.set_active_flow("new_season")
                    logging.info(
                        "Bootstrap handoff detected new-season step %s after save selection, dispatching directly",
                        new_season_step,
                    )
                    return self.bot.new_season_flow.run_step(new_season_step, screenshot=screenshot, fast_dispatch=True)
                if self.bot.find_main_screen_in_screenshot(screenshot):
                    self.bot.set_active_flow("main")
                    self.bot.awaiting_main_after_save_selection = False
                    self.bot.last_bootstrap_login_click_time = 0.0
                    self.bot.last_bootstrap_to_main_time = time.time()
                    logging.info("Bootstrap flow reached creative mode main screen after save selection")
                    if handoff_main_wait_seconds is not None:
                        logging.info("Bootstrap is handing off directly into the fast main-screen flow")
                        return self.bot.fast_main_screen_flow(
                            handoff_main_wait_seconds,
                            screenshot=screenshot,
                            assume_main_visible=True,
                        )
                    return True
                if self._is_post_save_main_intermediate(screenshot):
                    self.bot.awaiting_main_after_save_selection = False
                    self.bot.last_bootstrap_login_click_time = 0.0
                    self.bot.set_active_flow("main")
                    logging.info("Bootstrap handoff detected a main-chain intermediate screen after save selection, dispatching directly")
                    return self.bot.main_flow.wait_for_main_screen_return(
                        handoff_main_wait_seconds if handoff_main_wait_seconds is not None else timeout_seconds
                    )
                if handoff_wait >= SAVE_SELECTION_MAIN_HANDOFF_TIMEOUT_SECONDS:
                    logging.warning(
                        "Still waiting %.1fs after save selection; bootstrap remains in the save-selection handoff state and will keep watching for creative mode main, new-season, or main-chain intermediate screens",
                        handoff_wait,
                    )
                else:
                    logging.info("Waiting for creative mode main, new-season, or main-chain handoff after save selection")
                time.sleep(0.8)
                continue

            if self.bot.handle_global_priority_buttons(max_clicks=1, initial_screenshot=screenshot):
                continue

            game_main = self.bot.find_game_main_screen_in_screenshot(screenshot)
            if game_main:
                logging.info("Game main screen detected, entering creative mode")
                logging.info("Using game_main_mark to enter creative mode (score=%.3f)", game_main.score)
                self.bot.click_match(game_main, settle=0.8)
                self.bot.awaiting_save_selection = True
                self.bot.awaiting_main_after_save_selection = False
                self.bot.last_bootstrap_login_click_time = 0.0
                time.sleep(0.8)
                continue

            if login_cooldown_active:
                game_main = self.bot.find_game_main_screen_in_screenshot(screenshot)
                if game_main:
                    logging.info(
                        "Within %.0fs post-login cooldown, game main matched early and will enter creative mode: %s (score=%.3f)",
                        post_login_wait,
                        game_main.name,
                        game_main.score,
                    )
                    self.bot.click_match(game_main, settle=0.8)
                    self.bot.awaiting_save_selection = True
                    self.bot.awaiting_main_after_save_selection = False
                    self.bot.last_bootstrap_login_click_time = 0.0
                    time.sleep(0.8)
                    continue

            if self.bot.awaiting_save_selection and self.bot.find_save_selection_screen_in_screenshot(screenshot):
                logging.info("Save selection screen detected, choosing the third save slot")
                self.bot.choose_third_save_slot()
                time.sleep(1.2)
                continue

            login_screen = self.bot.find_login_screen_in_screenshot(screenshot)
            if login_screen:
                if login_cooldown_active:
                    logging.info(
                        "Login screen still visible %.0fs after the last login click, waiting for game main instead of clicking again",
                        post_login_wait,
                    )
                    time.sleep(0.8)
                    continue
                logging.info("Login screen detected, clicking through to game main screen")
                self.bot.window.click_client_center(settle=0.6)
                self.bot.last_bootstrap_login_click_time = time.time()
                time.sleep(0.8)
                continue

            if post_login_wait >= post_login_cooldown_seconds:
                logging.info(
                    "Login click was %.0fs ago, checking game main immediately and entering creative mode early if matched",
                    post_login_wait,
                )
                game_main = self.bot.find_game_main_screen_in_screenshot(screenshot)
                if game_main:
                    logging.info(
                        "Game main suspected after login wait, using game_main_mark to enter creative mode: %s (score=%.3f)",
                        game_main.name,
                        game_main.score,
                    )
                    self.bot.click_match(game_main, settle=0.8)
                    self.bot.awaiting_save_selection = True
                    self.bot.awaiting_main_after_save_selection = False
                    self.bot.last_bootstrap_login_click_time = 0.0
                    time.sleep(0.8)
                    continue
                logging.info("Post-login wait window expired without a game-main hit, allowing one remedial center click")
                self.bot.window.click_client_center(settle=0.6)
                self.bot.last_bootstrap_login_click_time = time.time()
                time.sleep(0.8)
                continue

            if login_cooldown_active:
                logging.info(
                    "Within %.0fs post-login cooldown, skipping unrelated bootstrap detections while waiting for game main",
                    post_login_wait,
                )
                time.sleep(0.8)
                continue

            since_visual_change = time.time() - self.bot.last_visual_change_time
            if since_visual_change < UNKNOWN_BOOTSTRAP_SETTLE_AFTER_VISUAL_CHANGE_SECONDS:
                logging.info(
                    "Bootstrap is still unknown but the screen changed %.1fs ago, waiting for the login/game-main UI to settle",
                    since_visual_change,
                )
                time.sleep(0.8)
                continue

            logging.info("Bootstrap stage is still unknown, waiting for login screen or game main screen to appear")
            time.sleep(1.0)

        self.bot.vision.save_debug_screenshot("bootstrap_timeout")
        logging.error("Bootstrap flow timed out before reaching creative mode main screen")
        return False
