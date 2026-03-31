from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto

import numpy as np


class StageName(Enum):
    LOGIN = "login"
    WORLD_LEAGUE = "world_league"


class StageResult(Enum):
    IN_PROGRESS = auto()
    SWITCH_TO_WORLD_LEAGUE = auto()
    RESTART_GAME = auto()
    DONE = auto()


@dataclass
class RunContext:
    practice_click_count: int = 0
    last_click_at: dict[str, float] = field(default_factory=dict)
    last_popup_click_at: float = 0.0
    last_edge_click_at: float = 0.0
    last_nav_click_at: float = 0.0
    last_team_change_at: float = 0.0
    last_game_launch_at: float = 0.0
    last_scan_log_at: float = 0.0
    last_progress_at: float = field(default_factory=time.time)
    last_practice_click_count: int = 0
    last_practice_progress_at: float = field(default_factory=time.time)
    invalid_frame_since: float = 0.0
    current_stage: StageName = StageName.LOGIN
    restart_reason: str = ""


@dataclass
class LoginStageState:
    nav_phase: str = "idle"
    nav_phase_since: float = field(default_factory=time.time)

    def set_phase(self, phase: str, now: float) -> None:
        self.nav_phase = phase
        self.nav_phase_since = now

    def reset(self, now: float, phase: str = "idle") -> None:
        self.set_phase(phase, now)

    @property
    def navigation_active(self) -> bool:
        return self.nav_phase in ("boot_or_home", "dream_team", "dream_team_wait", "world_prem")


@dataclass
class WorldLeagueStageState:
    team_change_phase: str = "idle"
    team_change_side: str | None = None
    team_change_opened_at: float = 0.0
    team_change_completed_for_scene: bool = False

    def reset(self) -> None:
        self.team_change_phase = "idle"
        self.team_change_side = None
        self.team_change_opened_at = 0.0


@dataclass
class SceneSnapshot:
    now: float
    pid: int
    hwnd: int
    frame: np.ndarray
    hits: list[tuple]
    results: dict
    popup: dict | None
    boot_score: float
    boot_scale: float | None
    world_prem_score: float
    world_prem_scale: float | None
    dream_team: dict | None
    team_change: dict | None
    team_select: dict
    back_button_ratio: float
    max_action_score: float
    save_list_info: dict
    save_list_like: bool
    home_like: bool
    navigation_bootstrap_active: bool
    operable_scene: bool
    world_league_ready: bool
