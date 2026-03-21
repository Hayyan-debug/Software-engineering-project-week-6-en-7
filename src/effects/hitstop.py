from __future__ import annotations

from dataclasses import dataclass


DEFAULT_HITSTOP_DURATIONS: dict[str, float] = {
    "bow": 0.06,
    "sword": 0.08,
    "hammer": 0.12,
}


@dataclass
class HitStopState:
    remaining_time: float = 0.0


def trigger_hit_stop(
    state: HitStopState,
    weapon_name: str,
    durations: dict[str, float] | None = None,
) -> None:
    table = durations if durations is not None else DEFAULT_HITSTOP_DURATIONS
    duration = table.get(weapon_name.lower(), table["sword"])
    # Never shorten an active hit stop when a lighter follow-up lands.
    state.remaining_time = max(state.remaining_time, duration)


def update_hit_stop(state: HitStopState, dt: float) -> HitStopState:
    state.remaining_time = max(0.0, state.remaining_time - dt)
    return state


def is_hit_stopped(state: HitStopState) -> bool:
    return state.remaining_time > 0.0

