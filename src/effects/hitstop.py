"""Hit-stop timing helpers for short combat freeze effects."""

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
    """Tracks remaining freeze time for hit-stop."""

    remaining_time: float = 0.0


def trigger_hit_stop(
    state: HitStopState,
    weapon_name: str,
    combo_count: int = 1,
    durations: dict[str, float] | None = None,
) -> None:
    """Start or extend hit-stop duration based on weapon and combo count."""
    table = durations if durations is not None else DEFAULT_HITSTOP_DURATIONS
    duration = table.get(weapon_name.lower(), table["sword"])
    if combo_count >= 2:
        combo_bonus = COMBO_HITSTOP_BONUS_START + (combo_count - 2) * COMBO_HITSTOP_BONUS_STEP
        duration += min(COMBO_HITSTOP_BONUS_MAX, combo_bonus)
    # Never shorten an active hit stop when a lighter follow-up lands.
    state.remaining_time = max(state.remaining_time, duration)


def update_hit_stop(state: HitStopState, dt: float) -> HitStopState:
    """Decrease remaining hit-stop time by `dt` seconds."""
    state.remaining_time = max(0.0, state.remaining_time - dt)
    return state


def is_hit_stopped(state: HitStopState) -> bool:
    """Return True while hit-stop is still active."""
    return state.remaining_time > 0.0
