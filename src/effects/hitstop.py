from __future__ import annotations

from dataclasses import dataclass


DEFAULT_HITSTOP_DURATIONS: dict[str, float] = {
    "bow": 0.06,
    "sword": 0.08,
    "hammer": 0.12,
}
COMBO_HITSTOP_BONUS_START = 0.02
COMBO_HITSTOP_BONUS_STEP = 0.02
COMBO_HITSTOP_BONUS_MAX = 0.08


@dataclass
class HitStopState:
    remaining_time: float = 0.0


def trigger_hit_stop(
    state: HitStopState,
    weapon_name: str,
    combo_count: int = 1,
    durations: dict[str, float] | None = None,
) -> None:
    table = durations if durations is not None else DEFAULT_HITSTOP_DURATIONS
    duration = table.get(weapon_name.lower(), table["sword"])
    if combo_count >= 2:
        combo_bonus = COMBO_HITSTOP_BONUS_START + (combo_count - 2) * COMBO_HITSTOP_BONUS_STEP
        duration += min(COMBO_HITSTOP_BONUS_MAX, combo_bonus)
    # Never shorten an active hit stop when a lighter follow-up lands.
    state.remaining_time = max(state.remaining_time, duration)


def update_hit_stop(state: HitStopState, dt: float) -> HitStopState:
    state.remaining_time = max(0.0, state.remaining_time - dt)
    return state


def is_hit_stopped(state: HitStopState) -> bool:
    return state.remaining_time > 0.0
