from __future__ import annotations

import logging
import time
from dataclasses import dataclass

UNKNOWN_BOOTSTRAP_SETTLE_AFTER_VISUAL_CHANGE_SECONDS = 2.5
STARTUP_BACK_ESCAPE_START_SECONDS = 12.0
STARTUP_BACK_ESCAPE_INTERVAL_SECONDS = 1.5
SAVE_SELECTION_MAIN_HANDOFF_TIMEOUT_SECONDS = 12.0
SAVE_SELECTION_MAIN_HANDOFF_LOADING_GRACE_SECONDS = 20.0
SAVE_SELECTION_MAIN_HANDOFF_MAX_TIMEOUT_SECONDS = 30.0
SAVE_SELECTION_LOADING_SETTLE_AFTER_VISUAL_CHANGE_SECONDS = 5.0


@dataclass(frozen=True)
class ScreenRegion:
    left_ratio: float
    top_ratio: float
    right_ratio: float
    bottom_ratio: float


REGION_TOP_RIGHT = ScreenRegion(0.72, 0.0, 1.0, 0.24)

class BootstrapFlow:
    def __init__(self, bot: object) -> None:
        self.bot = bot

    def _complete_post_save_boundary(
        self,
        target_label: str,
        result: bool,
        *,
        allow_false_without_bootstrap_failure: bool = True,
    ) -> bool:
        if result:
            logging.info("Bootstrap has completed at the post-save boundary and handed control to %s", target_label)
            return True
        if allow_false_without_bootstrap_failure:
            logging.warning(
                "Bootstrap had already completed at the post-save boundary before %s returned failure; keeping bootstrap successful and leaving follow-up recovery/retry to the main loop",
                target_label,
            )
            return True
        return False

    def _probe_startup_bootstrap_stage(self, screenshot) -> str:
        if self.bot.awaiting_main_after_save_selection:
            if self.bot.main_flow.matches_any_step(screenshot):
                return "main_flow"
            if self.bot.new_season_flow.matches_any_step(screenshot):
                return "new_season"
            return "unknown"

        if self.bot.awaiting_save_selection and self.bot.find_save_selection_screen_in_screenshot(screenshot):
            return "save_selection"

        login_screen = self.bot.find_login_screen_in_screenshot(screenshot)
        if login_screen:
            return "login_screen"

        game_main = self.bot.find_game_main_screen_in_screenshot(screenshot)
        if game_main:
            return "game_main"

        return "unknown"

    def _update_startup_bootstrap_probe(self, screenshot) -> str:
        now = time.time()
        stage = self._probe_startup_bootstrap_stage(screenshot)
        self.bot.last_stage_probe_time = now
        self.bot.last_stage_probe_screenshot = screenshot
        self.bot.last_stage_probe_detected_stage = stage
        if stage != "unknown" and stage != self.bot.last_stage_signature:
            logging.info("Stage changed: %s -> %s", self.bot.last_stage_signature, stage)
            self.bot.last_stage_signature = stage
            self.bot.last_stage_change_time = now
        return stage

    def _enter_creative_mode_from_game_main(self, game_main, reason: str) -> None:
        logging.info("%s", reason)
        logging.info("Using game_main_mark to enter creative mode (score=%.3f)", game_main.score)
        self.bot.click_match(game_main, settle=0.8)
        self.bot.awaiting_save_selection = True
        self.bot.awaiting_main_after_save_selection = False
        self.bot.last_bootstrap_login_click_time = 0.0

    def _choose_third_save_slot(self, reason: str) -> None:
        logging.info("%s", reason)
        self.bot.choose_third_save_slot()

    def _handoff_to_main_after_save_selection(
        self,
        screenshot,
        handoff_main_wait_seconds: float | None,
        timeout_seconds: float,
    ) -> bool:
        self.bot.set_active_flow("main")
        self.bot.awaiting_main_after_save_selection = False
        self.bot.last_bootstrap_login_click_time = 0.0
        self.bot.last_bootstrap_to_main_time = time.time()
        logging.info("Bootstrap flow reached creative mode main screen after save selection")
        logging.info("Bootstrap is handing off directly into the fast main-screen flow")
        return self._complete_post_save_boundary(
            "main_flow fast path",
            self.bot.fast_main_screen_flow(
                handoff_main_wait_seconds if handoff_main_wait_seconds is not None else timeout_seconds,
                screenshot=screenshot,
                assume_main_visible=True,
            ),
        )

    def matches(self, screenshot) -> bool:
        if self.bot.awaiting_main_after_save_selection and self.bot.main_flow.matches_any_step(screenshot):
            return True
        if self.bot.awaiting_main_after_save_selection and self.bot.new_season_flow.matches_any_step(screenshot):
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
        startup_started_at = time.time()
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if not self.bot.check_runtime_process_only():
                return False
            if not self.bot.check_visual_stall():
                return False
            screenshot = self.bot.vision.capture()
            startup_stage = self._update_startup_bootstrap_probe(screenshot)
            recent_stage, recent_stage_screenshot = self.bot.get_recent_stage_probe(max_age_seconds=4.0)
            post_login_wait = (
                time.time() - self.bot.last_bootstrap_login_click_time
                if self.bot.last_bootstrap_login_click_time > 0
                else 0.0
            )
            login_cooldown_active = 0.0 < post_login_wait < post_login_cooldown_seconds
            if (
                self.bot.last_stage_signature == "login_screen"
                and not login_cooldown_active
                and not self.bot.awaiting_save_selection
                and not self.bot.awaiting_main_after_save_selection
            ):
                logging.info("Bootstrap sees sticky login-screen state and clicks through immediately")
                self.bot.window.click_client_center(settle=0.6)
                self.bot.last_bootstrap_login_click_time = time.time()
                time.sleep(0.8)
                continue
            if (
                recent_stage == "login_screen"
                and recent_stage_screenshot is not None
                and not login_cooldown_active
                and not self.bot.awaiting_save_selection
                and not self.bot.awaiting_main_after_save_selection
            ):
                logging.info("Bootstrap is reusing the fresh login-screen stage probe and clicking through immediately")
                self.bot.window.click_client_center(settle=0.6)
                self.bot.last_bootstrap_login_click_time = time.time()
                time.sleep(0.8)
                continue
            if (
                recent_stage == "game_main"
                and recent_stage_screenshot is not None
                and not self.bot.awaiting_save_selection
                and not self.bot.awaiting_main_after_save_selection
            ):
                recent_game_main = self.bot.find_game_main_screen_in_screenshot(recent_stage_screenshot)
                if recent_game_main:
                    self._enter_creative_mode_from_game_main(
                        recent_game_main,
                        "Bootstrap is reusing the fresh game-main stage probe and entering creative mode immediately",
                    )
                    time.sleep(0.8)
                    continue
            if (
                recent_stage == "save_selection"
                and recent_stage_screenshot is not None
                and self.bot.awaiting_save_selection
                and not self.bot.awaiting_main_after_save_selection
            ):
                recent_save_selection = self.bot.find_save_selection_screen_in_screenshot(recent_stage_screenshot)
                if recent_save_selection:
                    self._choose_third_save_slot(
                        "Bootstrap is reusing the fresh save-selection stage probe and choosing the third save slot immediately"
                    )
                    time.sleep(1.2)
                    continue

            if self.bot.awaiting_save_selection and self.bot.find_save_selection_screen_in_screenshot(screenshot):
                self._choose_third_save_slot("Save selection screen detected, choosing the third save slot")
                time.sleep(1.2)
                continue

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
                main_step = None
                if recent_stage == "main_flow" and recent_stage_screenshot is not None:
                    main_step = self.bot.main_flow.detect_step(recent_stage_screenshot)
                    if main_step == "creative_mode_main":
                        logging.info("Bootstrap is reusing the fresh creative-mode-main stage probe after save selection")
                        return self._handoff_to_main_after_save_selection(
                            recent_stage_screenshot,
                            handoff_main_wait_seconds,
                            timeout_seconds,
                        )
                if main_step:
                    self.bot.awaiting_main_after_save_selection = False
                    self.bot.last_bootstrap_login_click_time = 0.0
                    logging.info(
                        "Bootstrap handoff detected main-flow step %s after save selection, dispatching directly",
                        main_step,
                    )
                    return self._complete_post_save_boundary(
                        f"main_flow step {main_step}",
                        self.bot.main_flow.run(
                            handoff_main_wait_seconds if handoff_main_wait_seconds is not None else timeout_seconds,
                            screenshot=recent_stage_screenshot,
                            assume_main_visible=(main_step == "creative_mode_main"),
                        ),
                    )

                main_step = self.bot.main_flow.detect_step(screenshot)
                if main_step == "creative_mode_main":
                    return self._handoff_to_main_after_save_selection(
                        screenshot,
                        handoff_main_wait_seconds,
                        timeout_seconds,
                    )
                if main_step:
                    self.bot.awaiting_main_after_save_selection = False
                    self.bot.last_bootstrap_login_click_time = 0.0
                    self.bot.set_active_flow("main")
                    logging.info(
                        "Bootstrap handoff detected main-flow step %s after save selection, dispatching directly",
                        main_step,
                    )
                    return self._complete_post_save_boundary(
                        f"main_flow step {main_step}",
                        self.bot.main_flow.run(
                            handoff_main_wait_seconds if handoff_main_wait_seconds is not None else timeout_seconds,
                            screenshot=screenshot,
                            assume_main_visible=False,
                        ),
                    )

                new_season_step = self.bot.new_season_flow.detect_step(screenshot)
                if new_season_step:
                    self.bot.awaiting_main_after_save_selection = False
                    self.bot.last_bootstrap_login_click_time = 0.0
                    self.bot.set_active_flow("new_season")
                    logging.info(
                        "Bootstrap handoff detected new-season step %s after save selection, dispatching directly",
                        new_season_step,
                    )
                    return self._complete_post_save_boundary(
                        f"new_season step {new_season_step}",
                        self.bot.new_season_flow.run_step(new_season_step, screenshot=screenshot, fast_dispatch=True),
                    )
                if handoff_wait >= SAVE_SELECTION_MAIN_HANDOFF_TIMEOUT_SECONDS:
                    if self.bot.should_defer_recovery_for_recent_visual_change(
                        context=(
                            "Bootstrap post-save handoff is still unknown %.1fs after save selection"
                            % handoff_wait
                        ),
                        settle_seconds=SAVE_SELECTION_LOADING_SETTLE_AFTER_VISUAL_CHANGE_SECONDS,
                        absolute_timeout_seconds=SAVE_SELECTION_MAIN_HANDOFF_MAX_TIMEOUT_SECONDS,
                        reference_time=self.bot.last_save_selection_click_time,
                    ):
                        time.sleep(0.8)
                        continue
                    if handoff_wait < SAVE_SELECTION_MAIN_HANDOFF_LOADING_GRACE_SECONDS:
                        logging.info(
                            "Bootstrap post-save handoff is still unknown %.1fs after save selection, but it is still within the loading grace window; waiting before escalating to recovery",
                            handoff_wait,
                        )
                        time.sleep(0.8)
                        continue
                    self.bot.awaiting_main_after_save_selection = False
                    self.bot.last_bootstrap_login_click_time = 0.0
                    logging.warning(
                        "Bootstrap did not detect a main-flow step or a new-season step %.1fs after save selection, escalating directly to recovery",
                        handoff_wait,
                    )
                    return self._complete_post_save_boundary("recovery", self.bot.recover_to_main_screen())
                else:
                    logging.info("Waiting for main-flow or new-season handoff after save selection")
                time.sleep(0.8)
                continue

            game_main = self.bot.find_game_main_screen_in_screenshot(screenshot)
            if game_main:
                self._enter_creative_mode_from_game_main(game_main, "Game main screen detected, entering creative mode")
                time.sleep(0.8)
                continue

            if login_cooldown_active:
                game_main = self.bot.find_game_main_screen_in_screenshot(screenshot)
                if game_main:
                    self._enter_creative_mode_from_game_main(
                        game_main,
                        "Within %.0fs post-login cooldown, game main matched early and will enter creative mode: %s"
                        % (post_login_wait, game_main.name),
                    )
                    time.sleep(0.8)
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

            if self.bot.handle_bootstrap_continue_buttons(max_clicks=1, initial_screenshot=screenshot):
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

            startup_elapsed = time.time() - startup_started_at
            if (
                startup_stage == "unknown"
                and not self.bot.awaiting_save_selection
                and not self.bot.awaiting_main_after_save_selection
                and not login_cooldown_active
                and startup_elapsed >= STARTUP_BACK_ESCAPE_START_SECONDS
                and time.time() - self.bot.last_startup_back_escape_click_time >= STARTUP_BACK_ESCAPE_INTERVAL_SECONDS
            ):
                logging.info(
                    "Bootstrap startup probe is still unknown %.1fs after startup, using the startup back escape to dismiss illegal startup screens",
                    startup_elapsed,
                )
                self.bot.click_back_hotspot(settle=0.35)
                self.bot.last_startup_back_escape_click_time = time.time()
                time.sleep(0.5)
                continue

            logging.info(
                "Bootstrap startup mode is only waiting for login/game_main/save_selection; current startup probe is %s, so it will keep waiting instead of exploring other flows",
                startup_stage,
            )
            time.sleep(1.0)

        self.bot.vision.save_debug_screenshot("bootstrap_timeout")
        logging.error("Bootstrap flow timed out before reaching creative mode main screen")
        return False
