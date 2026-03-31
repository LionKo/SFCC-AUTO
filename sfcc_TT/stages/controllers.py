from __future__ import annotations

import subprocess
import time
from typing import Any

from .models import LoginStageState, RunContext, SceneSnapshot, StageName, StageResult, WorldLeagueStageState


def current_sub_stage(ctx: RunContext, login_stage: LoginStageState, world_stage: WorldLeagueStageState) -> str:
    if ctx.current_stage == StageName.LOGIN:
        return login_stage.nav_phase
    if world_stage.team_change_phase != "idle":
        return world_stage.team_change_phase
    return "loop"


def write_status(writer, ctx: RunContext, login_stage: LoginStageState, world_stage: WorldLeagueStageState, force: bool = False, **kwargs) -> None:
    writer.update(
        force=force,
        stage=ctx.current_stage.value,
        sub_stage=current_sub_stage(ctx, login_stage, world_stage),
        restart_reason=ctx.restart_reason,
        **kwargs,
    )


def reset_to_login(ctx: RunContext, login_stage: LoginStageState, world_stage: WorldLeagueStageState, now: float) -> None:
    ctx.current_stage = StageName.LOGIN
    login_stage.reset(now, "boot_or_home")
    world_stage.reset()


class LoginStageController:
    def __init__(self, config: dict[str, Any], actions: dict[str, Any]) -> None:
        self.state = LoginStageState()
        self.config = config
        self.actions = actions

    def tick(self, scene: SceneSnapshot, ctx: RunContext, writer, world_stage: WorldLeagueStageState, emit) -> StageResult:
        strong_action_hit = scene.hits[0] if scene.hits and scene.hits[0][1] >= self.config["ACTION_OVERRIDE_SCORE"] else None

        if self.state.nav_phase == "idle" and scene.home_like:
            self.state.set_phase("dream_team", scene.now)
        elif self.state.nav_phase == "boot_or_home" and (strong_action_hit or scene.max_action_score >= self.config["ACTION_OVERRIDE_SCORE"]):
            self.state.set_phase("idle", scene.now)
        elif self.state.navigation_active and (strong_action_hit or scene.max_action_score >= self.config["ACTION_OVERRIDE_SCORE"]) and not scene.home_like:
            self.state.set_phase("idle", scene.now)

        if scene.world_league_ready and not self.state.navigation_active and not scene.home_like and not scene.save_list_like:
            write_status(writer, ctx, self.state, world_stage, force=True, state="stage_transition", last_action="enter_world_league", practice_click_count=ctx.practice_click_count)
            return StageResult.SWITCH_TO_WORLD_LEAGUE

        if scene.popup and scene.boot_score < self.config["BOOT_THRESHOLD"] and scene.popup.get("score", -1.0) >= self.config["POPUP_ACCEPT_SCORE"] and scene.now - ctx.last_popup_click_at >= self.config["POPUP_CLICK_COOLDOWN"]:
            x, y = scene.popup["center"]
            ok, msg = self.actions["do_foreground_click"](scene.hwnd, x, y)
            ctx.last_popup_click_at = scene.now
            write_status(writer, ctx, self.state, world_stage, force=True, state="popup", last_action="popup_blue_button", practice_click_count=ctx.practice_click_count)
            if ok:
                emit("popup", f"[POPUP] blue_button score={scene.popup['score']:.3f} bbox={scene.popup['bbox']} client=({x},{y}) -> {msg}", archive_tag="popup_blue", log_fields={"score": round(scene.popup['score'], 4), "bbox": scene.popup["bbox"], "client_x": x, "client_y": y})
            else:
                emit("warn", f"[POPUP][WARN] bbox={scene.popup['bbox']} client=({x},{y}) -> {msg}", archive_tag="popup_warn")
            time.sleep(1.2)
            return StageResult.IN_PROGRESS

        if scene.boot_score >= self.config["BOOT_THRESHOLD"] and scene.now - ctx.last_nav_click_at >= self.config["NAV_CLICK_COOLDOWN"]:
            (ok, msg), (cx, cy) = self.actions["click_by_ratio"](scene.hwnd, *self.config["BOOT_CLICK_RATIO"])
            ctx.last_nav_click_at = scene.now
            self.state.set_phase("dream_team", scene.now)
            write_status(writer, ctx, self.state, world_stage, force=True, state="navigating", last_action="boot_click", practice_click_count=ctx.practice_click_count)
            emit("nav", f"[NAV] boot_click score={scene.boot_score:.3f} scale={scene.boot_scale:.2f} client=({cx},{cy}) -> {msg}", archive_tag="nav_boot", log_fields={"score": round(scene.boot_score, 4), "scale": scene.boot_scale, "client_x": cx, "client_y": cy})
            time.sleep(self.config["BOOT_WAIT_SECONDS"])
            return StageResult.IN_PROGRESS

        if self.state.nav_phase == "boot_or_home" and scene.now - self.state.nav_phase_since > 2.0:
            self.state.set_phase("dream_team", scene.now)

        if self.state.nav_phase == "dream_team" and scene.now - ctx.last_nav_click_at >= self.config["NAV_CLICK_COOLDOWN"]:
            if scene.dream_team and scene.dream_team.get("found") and scene.dream_team.get("click_point") is not None:
                cx, cy = scene.dream_team["click_point"]
                ok, msg = self.actions["do_foreground_click"](scene.hwnd, cx, cy)
                nav_action = "create_club_template_gate"
                emit("nav", f"[NAV] create_club_template_gate score={scene.dream_team['score']:.3f} bbox={scene.dream_team['bbox']} client=({cx},{cy}) -> {msg}", archive_tag="nav_create_club_gate", log_fields={"score": round(scene.dream_team["score"], 4), "bbox": scene.dream_team["bbox"], "client_x": cx, "client_y": cy})
            else:
                (ok, msg), (cx, cy) = self.actions["click_by_ratio"](scene.hwnd, *self.config["CREATE_CLUB_CLICK_RATIO"])
                score = scene.dream_team["score"] if scene.dream_team else -1.0
                nav_action = "create_club_fixed"
                emit("nav", f"[NAV] create_club_fixed score={score:.3f} client=({cx},{cy}) -> {msg}", archive_tag="nav_create_club_fixed", log_fields={"score": round(score, 4), "client_x": cx, "client_y": cy})
            ctx.last_nav_click_at = scene.now
            if ok:
                self.state.set_phase("dream_team_wait", scene.now)
                write_status(writer, ctx, self.state, world_stage, force=True, state="navigating", last_action=nav_action, practice_click_count=ctx.practice_click_count)
                time.sleep(3.0)
                return StageResult.IN_PROGRESS
            write_status(writer, ctx, self.state, world_stage, force=True, state="navigating", last_action=f"{nav_action}_failed", practice_click_count=ctx.practice_click_count)

        if self.state.nav_phase == "dream_team_wait":
            if scene.world_prem_score >= self.config["WORLD_PREM_THRESHOLD"]:
                self.state.set_phase("world_prem", scene.now)
            elif scene.save_list_like and scene.now - ctx.last_nav_click_at >= self.config["NAV_CLICK_COOLDOWN"]:
                (ok, msg), (cx, cy) = self.actions["click_by_ratio"](scene.hwnd, *self.config["SAVE_LIST_BACK_CLICK_RATIO"])
                nav_action = "save_list_back"
                ctx.last_nav_click_at = scene.now
                emit("nav", f"[NAV] {nav_action} client=({cx},{cy}) -> {msg}", archive_tag=nav_action, log_fields={"client_x": cx, "client_y": cy})
                if ok:
                    self.state.nav_phase_since = scene.now
                    write_status(writer, ctx, self.state, world_stage, force=True, state="navigating", last_action=nav_action, practice_click_count=ctx.practice_click_count)
                    time.sleep(3.0)
                    return StageResult.IN_PROGRESS
            elif scene.home_like and scene.now - self.state.nav_phase_since >= self.config["NAV_CLICK_COOLDOWN"]:
                self.state.set_phase("dream_team", scene.now)
            elif not scene.navigation_bootstrap_active:
                self.state.set_phase("idle", scene.now)
            elif not scene.home_like and scene.now - self.state.nav_phase_since >= self.config["NAV_STEP_TIMEOUT"]:
                self.state.set_phase("idle", scene.now)
            elif scene.home_like and scene.now - self.state.nav_phase_since >= 18.0:
                self.state.set_phase("dream_team", scene.now)
            elif scene.now - self.state.nav_phase_since >= self.config["NAV_STEP_TIMEOUT"]:
                self.state.set_phase("dream_team", scene.now)

        if self.state.nav_phase == "world_prem" and scene.now - ctx.last_nav_click_at >= self.config["NAV_CLICK_COOLDOWN"]:
            (ok, msg), (cx, cy) = self.actions["click_by_ratio"](scene.hwnd, *self.config["WORLD_PREM_CLICK_RATIO"])
            ctx.last_nav_click_at = scene.now
            emit("nav", f"[NAV] world_prem_fixed client=({cx},{cy}) -> {msg}", archive_tag="nav_world_prem", log_fields={"client_x": cx, "client_y": cy})
            if ok:
                self.state.set_phase("idle", scene.now)
                write_status(writer, ctx, self.state, world_stage, force=True, state="navigating", last_action="world_prem_fixed", practice_click_count=ctx.practice_click_count)
                time.sleep(3.0)
                return StageResult.IN_PROGRESS
            write_status(writer, ctx, self.state, world_stage, force=True, state="navigating", last_action="world_prem_fixed_failed", practice_click_count=ctx.practice_click_count)

        if scene.navigation_bootstrap_active and self.state.nav_phase == "idle" and scene.now - self.state.nav_phase_since >= self.config["NAV_STEP_TIMEOUT"]:
            self.state.set_phase("dream_team", scene.now)

        write_status(writer, ctx, self.state, world_stage, state="login_scanning", last_action="scan_login", practice_click_count=ctx.practice_click_count)
        return StageResult.IN_PROGRESS


class WorldLeagueStageController:
    def __init__(self, config: dict[str, Any], actions: dict[str, Any]) -> None:
        self.state = WorldLeagueStageState()
        self.config = config
        self.actions = actions

    def tick(self, scene: SceneSnapshot, ctx: RunContext, writer, login_stage: LoginStageState, emit) -> StageResult:
        if scene.boot_score >= self.config["BOOT_THRESHOLD"] or scene.save_list_like:
            ctx.restart_reason = "world_stage_unexpected_login_scene"
            emit("restart", f"[SAFEGUARD] Unexpected login scene detected during world_league stage, restarting game pid={scene.pid}", archive_tag="restart_unexpected_login_scene", log_fields={"pid": scene.pid, "boot_score": round(scene.boot_score, 4), "save_list_like": scene.save_list_like, "home_like": scene.home_like})
            return StageResult.RESTART_GAME

        if (
            self.state.team_change_phase == "idle"
            and scene.team_change
            and scene.team_change.get("found")
            and scene.team_change.get("click_point") is not None
            and scene.now - ctx.last_team_change_at >= self.config["TEAM_CHANGE_COOLDOWN"]
            and not scene.team_select.get("found")
            and not self.state.team_change_completed_for_scene
        ):
            cx, cy = scene.team_change["click_point"]
            ok, msg = self.actions["do_foreground_click"](scene.hwnd, cx, cy)
            ctx.last_team_change_at = scene.now
            if ok:
                self.state.team_change_phase = "open_selector"
                self.state.team_change_side = "match_start"
                self.state.team_change_opened_at = scene.now
                write_status(writer, ctx, login_stage, self.state, force=True, state="team_change", last_action="team_open_selector", practice_click_count=ctx.practice_click_count)
                emit("team", f"[TEAM] open_selector score={scene.team_change['score']:.3f} client=({cx},{cy}) -> {msg}", archive_tag="team_change", log_fields={"client_x": cx, "client_y": cy, "score": round(scene.team_change['score'], 4)})
                time.sleep(1.2)
                return StageResult.IN_PROGRESS

        if self.state.team_change_phase != "idle":
            if self.state.team_change_phase == "open_selector":
                if scene.team_select.get("found"):
                    self.state.team_change_phase = "scroll_top"
                    self.state.team_change_opened_at = scene.now
                elif scene.now - self.state.team_change_opened_at > self.config["TEAM_SELECT_OPEN_WAIT_SECONDS"] + 3.0:
                    self.state.reset()

            if self.state.team_change_phase == "scroll_top" and scene.team_select.get("found") and scene.now - ctx.last_team_change_at >= 0.6:
                ok, msg = self.actions["drag_by_ratio"](
                    scene.hwnd,
                    self.config["TEAM_LIST_SCROLL_START_RATIO"],
                    self.config["TEAM_LIST_SCROLL_END_RATIO"],
                )
                ctx.last_team_change_at = scene.now
                if ok:
                    self.state.team_change_phase = "pick_first"
                    write_status(writer, ctx, login_stage, self.state, force=True, state="team_change", last_action="team_scroll_top_once", practice_click_count=ctx.practice_click_count)
                    emit("team", f"[TEAM] scroll_top_once -> {msg}")
                    time.sleep(0.8)
                    return StageResult.IN_PROGRESS

            if self.state.team_change_phase == "pick_first" and scene.team_select.get("found") and scene.now - ctx.last_team_change_at >= 0.6:
                x, y = scene.team_select["first_row_point"]
                ok, msg = self.actions["do_foreground_click"](scene.hwnd, x, y)
                ctx.last_team_change_at = scene.now
                if ok:
                    self.state.team_change_phase = "confirm"
                    write_status(writer, ctx, login_stage, self.state, force=True, state="team_change", last_action="team_pick_first", practice_click_count=ctx.practice_click_count)
                    emit("team", f"[TEAM] pick_first client=({x},{y}) -> {msg}")
                    time.sleep(0.8)
                    return StageResult.IN_PROGRESS

            if self.state.team_change_phase == "confirm" and scene.now - ctx.last_team_change_at >= 0.6:
                if scene.team_select.get("found"):
                    x, y = scene.team_select["confirm_point"]
                else:
                    x = int(scene.frame.shape[1] * self.config["TEAM_SELECT_CONFIRM_CLICK_RATIO"][0])
                    y = int(scene.frame.shape[0] * self.config["TEAM_SELECT_CONFIRM_CLICK_RATIO"][1])
                ok, msg = self.actions["do_foreground_click"](scene.hwnd, x, y)
                ctx.last_team_change_at = scene.now
                if ok:
                    self.state.team_change_completed_for_scene = True
                    self.state.reset()
                    write_status(writer, ctx, login_stage, self.state, force=True, state="team_change", last_action="team_confirm", practice_click_count=ctx.practice_click_count)
                    emit("team", f"[TEAM] confirm client=({x},{y}) -> {msg}")
                    time.sleep(1.5)
                    return StageResult.IN_PROGRESS

            if not scene.team_select.get("found") and self.state.team_change_phase in ("scroll_top", "pick_first", "confirm") and scene.now - ctx.last_team_change_at > 4.0:
                self.state.reset()

        if scene.hits:
            btn_name, score, (x, y), scale, _ = scene.hits[0]
            write_status(writer, ctx, login_stage, self.state, state="main_loop", last_button=btn_name, practice_click_count=ctx.practice_click_count)
            if scene.now - ctx.last_click_at[btn_name] >= self.config["CLICK_COOLDOWN"]:
                ok, msg = self.actions["do_foreground_click"](scene.hwnd, x, y)
                ctx.last_click_at[btn_name] = scene.now
                if ok:
                    if btn_name == "practice":
                        self.state.team_change_completed_for_scene = False
                        ctx.practice_click_count += 1
                        write_status(writer, ctx, login_stage, self.state, force=True, state="main_loop", last_action="click_practice", last_button=btn_name, practice_click_count=ctx.practice_click_count)
                        emit("action", f"[ACT] practice #{ctx.practice_click_count}/{self.config['PRACTICE_CLICK_LIMIT']} score={score:.3f} scale={scale:.2f} pos=({x},{y}) -> {msg}", archive_tag="action_practice", log_fields={"button": btn_name, "score": round(score, 4), "scale": scale, "client_x": x, "client_y": y})
                        if ctx.practice_click_count >= self.config["PRACTICE_CLICK_LIMIT"]:
                            write_status(writer, ctx, login_stage, self.state, force=True, state="done", last_action="shutdown", last_button="practice", practice_click_count=ctx.practice_click_count)
                            emit("done", f"[DONE] Practice clicked {ctx.practice_click_count} times, shutting down in {self.config['SHUTDOWN_DELAY_SECONDS']}s")
                            subprocess.run(["shutdown", "/s", "/t", str(self.config["SHUTDOWN_DELAY_SECONDS"])], check=False)
                            return StageResult.DONE
                    else:
                        self.state.team_change_completed_for_scene = False
                        write_status(writer, ctx, login_stage, self.state, force=True, state="main_loop", last_action=f"click_{btn_name}", last_button=btn_name, practice_click_count=ctx.practice_click_count)
                        emit("action", f"[ACT] {btn_name} score={score:.3f} scale={scale:.2f} pos=({x},{y}) -> {msg}", archive_tag=f"action_{btn_name}", log_fields={"button": btn_name, "score": round(score, 4), "scale": scale, "client_x": x, "client_y": y})
                else:
                    emit("warn", f"[WARN] {btn_name} score={score:.3f} pos=({x},{y}) -> {msg}", archive_tag=f"warn_{btn_name}")
            else:
                print(f"[SKIP] {btn_name} cooldown score={score:.3f}", end="\r", flush=True)
            time.sleep(self.config["SCAN_INTERVAL"])
            return StageResult.IN_PROGRESS

        if scene.popup and scene.boot_score < self.config["BOOT_THRESHOLD"] and scene.popup.get("score", -1.0) >= self.config["POPUP_ACCEPT_SCORE"] and scene.now - ctx.last_popup_click_at >= self.config["POPUP_CLICK_COOLDOWN"]:
            x, y = scene.popup["center"]
            ok, msg = self.actions["do_foreground_click"](scene.hwnd, x, y)
            ctx.last_popup_click_at = scene.now
            write_status(writer, ctx, login_stage, self.state, force=True, state="popup", last_action="popup_blue_button", practice_click_count=ctx.practice_click_count)
            if ok:
                self.state.team_change_completed_for_scene = False
                emit("popup", f"[POPUP] blue_button score={scene.popup['score']:.3f} bbox={scene.popup['bbox']} client=({x},{y}) -> {msg}", archive_tag="popup_blue", log_fields={"score": round(scene.popup['score'], 4), "bbox": scene.popup["bbox"], "client_x": x, "client_y": y})
            else:
                emit("warn", f"[POPUP][WARN] bbox={scene.popup['bbox']} client=({x},{y}) -> {msg}", archive_tag="popup_warn")
            time.sleep(1.2)
            return StageResult.IN_PROGRESS

        if self.config["ENABLE_EDGE_FALLBACK"] and scene.now - ctx.last_edge_click_at >= self.config["EDGE_CLICK_COOLDOWN"]:
            ok, msg = self.actions["click_current_cursor"](scene.hwnd)
            ctx.last_edge_click_at = scene.now
            write_status(writer, ctx, login_stage, self.state, force=True, state="fallback", last_action="mouse_click", practice_click_count=ctx.practice_click_count)
            print(f"[FALLBACK] mouse_click -> {msg}")
            time.sleep(1.0)
            return StageResult.IN_PROGRESS

        write_status(writer, ctx, login_stage, self.state, state="world_scanning", last_action="scan_world_league", practice_click_count=ctx.practice_click_count)
        return StageResult.IN_PROGRESS
