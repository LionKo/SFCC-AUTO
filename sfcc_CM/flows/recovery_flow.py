from __future__ import annotations

import logging
import time


class RecoveryFlow:
    def __init__(self, bot: object) -> None:
        self.bot = bot

    def run(self, timeout_seconds: float) -> bool:
        screenshot = self.bot.vision.capture()
        if self.bot.should_trust_main_screen(screenshot):
            self.bot.set_active_flow("main")
            logging.info("Skipping recovery because creative mode main screen is still within the trust window")
            return True

        self.bot.set_active_flow("recovery")
        logging.info("Current screen is not the creative mode main screen, attempting recovery")
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if not self.bot.check_runtime_health():
                return False
            screenshot = self.bot.vision.capture()
            trusted_main = self.bot.should_trust_main_screen(screenshot)

            if self.bot.handle_global_priority_buttons(max_clicks=1, initial_screenshot=screenshot):
                continue

            if self.bot.find_main_screen_in_screenshot(screenshot) or trusted_main:
                self.bot.set_active_flow("main")
                if trusted_main and not self.bot.find_main_screen_in_screenshot(screenshot):
                    logging.info("Recovery trusted creative mode main screen based on recent stage confirmation")
                else:
                    logging.info("Recovery found creative mode main screen")
                return True

            recovery_main_hint = self.bot.find_main_screen_recovery_hint(screenshot)
            if recovery_main_hint and not (
                self.bot.find_special_training_screen_in_screenshot(screenshot)
                or self.bot.find_match_reward_screen_in_screenshot(screenshot)
                or self.bot.find_club_transfers_screen_in_screenshot(screenshot)
                or self.bot.find_club_transfers_level_screen_in_screenshot(screenshot)
                or self.bot.find_sp_join_screen_in_screenshot(screenshot)
                or self.bot.find_final_confirm_screen_in_screenshot(screenshot)
            ):
                self.bot.set_active_flow("main")
                logging.info(
                    "Recovery accepted creative mode main screen via main-action hint %s (score=%.3f)",
                    recovery_main_hint.name,
                    recovery_main_hint.score,
                )
                return True

            if (
                self.bot.find_login_screen_in_screenshot(screenshot)
                or self.bot.find_game_main_screen_in_screenshot(screenshot)
                or self.bot.find_save_selection_screen_in_screenshot(screenshot)
            ):
                if self.bot.run_bootstrap_flow():
                    return True
                continue

            if self.bot.run_new_season_flow(screenshot):
                logging.info("Handled new season flow during recovery")
                return True

            if self.bot.run_back_recovery_flow():
                if self.bot.is_main_screen():
                    self.bot.set_active_flow("main")
                    logging.info("Recovered to creative mode main screen via back-button recovery")
                    return True
                continue

            if self.bot.handle_exception_layer(max_clicks=2, initial_screenshot=screenshot):
                if self.bot.is_main_screen():
                    logging.info("Recovered to creative mode main screen via exception-layer handling")
                    return True
                continue

            if self.bot.handle_post_schedule_events(max_clicks=6):
                if self.bot.is_main_screen():
                    logging.info("Recovered to creative mode main screen via event handling")
                    return True
                continue

            if self.bot.handle_league_result_screen():
                if self.bot.is_main_screen():
                    logging.info("Recovered to creative mode main screen via league-result handling")
                    return True
                continue

            if self.bot.handle_connecting_screen():
                if self.bot.is_main_screen():
                    logging.info("Recovered to creative mode main screen via CONNECTING handling")
                    return True
                continue

            if self.bot.handle_match_reward_screen():
                continue

            main_after_reward = self.bot.find_main_screen_recovery_hint(self.bot.vision.capture())
            if main_after_reward:
                self.bot.set_active_flow("main")
                logging.info(
                    "Recovery accepted creative mode main screen after reward handling via %s (score=%.3f)",
                    main_after_reward.name,
                    main_after_reward.score,
                )
                return True

            if self.bot.handle_speed_one_anywhere():
                refreshed = self.bot.vision.capture()
                if self.bot.find_main_screen_in_screenshot(refreshed) or self.bot.find_main_screen_recovery_hint(refreshed):
                    self.bot.set_active_flow("main")
                    logging.info("Recovery resumed main flow immediately after speed handling on creative mode main screen")
                    return True
                continue

            if self.bot.handle_generic_confirm_fallback(min_interval=0.8):
                refreshed = self.bot.vision.capture()
                if self.bot.find_main_screen_in_screenshot(refreshed) or self.bot.find_main_screen_recovery_hint(refreshed):
                    logging.info("Recovered to creative mode main screen via generic confirm fallback")
                    return True
                continue

            if self.bot.run_back_recovery_flow():
                if self.bot.is_main_screen():
                    logging.info("Recovered to creative mode main screen via back-button recovery")
                    return True
                continue

            main = self.bot.is_main_screen()
            if main:
                self.bot.set_active_flow("main")
                logging.info("Recovered to creative mode main screen")
                return True

            if not self.bot.find_any_known_operation():
                self.bot.fallback_click_when_no_operation_found()
            else:
                time.sleep(1.0)

        self.bot.vision.save_debug_screenshot("recover_main_screen_timeout")
        logging.error("Failed to recover to creative mode main screen within timeout")
        return False
