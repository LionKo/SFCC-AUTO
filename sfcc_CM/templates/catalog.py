from __future__ import annotations

from itertools import chain


COMMON_TEMPLATES = {
    "back_button": "common/back_button",
    "close_button": "common/close_button",
    "continue_button": "common/continue_button",
    "continue_button2": "common/continue_button2",
    "continue_button3": "common/continue_button3",
    "final_confirm_ok_button": "common/final_confirm_ok_button",
    "final_confirm_ok_button2": "common/final_confirm_ok_button2",
    "login_retry": "common/login_retry",
    "ok_button": "common/ok_button",
    "ok_button2": "common/ok_button2",
    "ok_button3": "common/ok_button3",
    "ok_chs_button": "common/ok_chs_button",
}

LOGIN_TEMPLATES = {
    "game_main_mark": "login/game_main_mark",
    "login_mark": "login/login_mark",
}

MAIN_TEMPLATES = {
    "assistant": "main/assistant",
    "creative_mode_advance_schedule_button_small": "main/creative_mode_advance_schedule_button_small",
    "creative_mode_special_training_button": "main/creative_mode_special_training_button",
    "creative_mode_special_training_button3": "main/creative_mode_special_training_button3",
    "creative_mode_speed1": "main/creative_mode_speed1",
    "creative_mode_speed3": "main/creative_mode_speed3",
    "creative_mode_speed_popup": "main/creative_mode_speed_popup",
    "event_choose_mark": "main/event_choose_mark",
    "log": "main/log",
    "log2": "main/log2",
    "match_result_button": "main/match_result_button",
    "match_reward_speed1": "main/match_reward_speed1",
    "skip_button": "main/skip_button",
    "skip_button2": "main/skip_button2",
    "special_training_execute_button": "main/special_training_execute_button",
    "special_training_execute_button2": "main/special_training_execute_button2",
    "special_training_recommend_button": "main/special_training_recommend_button",
    "special_training_recommend_button2": "main/special_training_recommend_button2",
    "special_training_reset_all_button": "main/special_training_reset_all_button",
    "special_training_reset_all_button2": "main/special_training_reset_all_button2",
}

NEW_SEASON_TEMPLATES = {
    "club_transfers_min_button": "new_season/club_transfers_min_button",
    "club_transfers_renewal_button": "new_season/club_transfers_renewal_button",
    "club_transfers_renewal_button_2": "new_season/club_transfers_renewal_button_2",
    "sp_belong": "new_season/sp_belong",
    "sp_join_button1": "new_season/sp_join_button1",
    "sp_join_button2": "new_season/sp_join_button2",
    "sp_join_button3": "new_season/sp_join_button3",
    "sp_join_button4": "new_season/sp_join_button4",
    "sp_join_filter_entrance": "new_season/sp_join_filter_entrance",
}

FLOW_TEMPLATE_GROUPS = {
    "common": COMMON_TEMPLATES,
    "login": LOGIN_TEMPLATES,
    "main": MAIN_TEMPLATES,
    "new_season": NEW_SEASON_TEMPLATES,
}

TEMPLATE_PATHS = dict(chain.from_iterable(group.items() for group in FLOW_TEMPLATE_GROUPS.values()))


def get_required_templates() -> list[str]:
    return sorted(TEMPLATE_PATHS)
