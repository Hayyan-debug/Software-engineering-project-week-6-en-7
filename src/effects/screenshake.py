from __future__ import annotations

import math
from dataclasses import dataclass


DEFAULT_SCREENSHAKE_PROFILES: dict[str, tuple[float, float, float]] = {
    # weapon_name: (amplitude_px, duration_s, frequency_hz)
    "bow": (3.0, 0.08, 22.0),
    "sword": (5.0, 0.11, 20.0),
    "hammer": (8.0, 0.15, 17.0),
}


@dataclass
class ScreenShakeState:
    time_left: float = 0.0
    duration: float = 0.0
    amplitude: float = 0.0
    frequency: float = 20.0
    phase_x: float = 0.0
    phase_y: float = math.pi / 2.0


def trigger_screen_shake(
    state: ScreenShakeState,
    weapon_name: str,
    profiles: dict[str, tuple[float, float, float]] | None = None,
) -> None:
    table = profiles if profiles is not None else DEFAULT_SCREENSHAKE_PROFILES
    amp, dur, freq = table.get(weapon_name.lower(), table["sword"])

    # Never reduce an active shake if a lighter hit lands after a heavier one.
    state.time_left = max(state.time_left, dur)
    state.duration = max(state.duration, dur)
    state.amplitude = max(state.amplitude, amp)
    state.frequency = max(state.frequency, freq)


def update_screen_shake(state: ScreenShakeState, dt: float) -> ScreenShakeState:
    state.time_left = max(0.0, state.time_left - dt)
    if state.time_left <= 0.0:
        state.duration = 0.0
        state.amplitude = 0.0
    return state


def get_screen_shake_offset(state: ScreenShakeState) -> tuple[int, int]:
    if state.time_left <= 0.0 or state.duration <= 0.0 or state.amplitude <= 0.0:
        return (0, 0)

    progress = 1.0 - (state.time_left / max(state.duration, 0.001))
    amp_now = state.amplitude * (state.time_left / max(state.duration, 0.001))
    omega = 2.0 * math.pi * state.frequency
    t = progress * state.duration

    ox = int(round(amp_now * math.sin(state.phase_x + omega * t)))
    oy = int(round(amp_now * math.sin(state.phase_y + omega * t)))
    return (ox, oy)

