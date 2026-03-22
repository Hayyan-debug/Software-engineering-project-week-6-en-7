"""Public exports for gameplay effect systems (particles, hit-stop, shake)."""

from .effects import (
    HitEffect,
    HitEffectPalette,
    Particle,
    create_hit_effect,
    create_hit_particles,
    draw_hit_effects,
    draw_particles,
    update_hit_effects,
    update_particles,
)
from .hitstop import HitStopState, is_hit_stopped, trigger_hit_stop, update_hit_stop
from .screenshake import ScreenShakeState, get_screen_shake_offset, trigger_screen_shake, update_screen_shake

__all__ = [
    "HitEffect",
    "HitEffectPalette",
    "Particle",
    "create_hit_effect",
    "create_hit_particles",
    "draw_hit_effects",
    "draw_particles",
    "update_hit_effects",
    "update_particles",
    "HitStopState",
    "is_hit_stopped",
    "trigger_hit_stop",
    "update_hit_stop",
    "ScreenShakeState",
    "get_screen_shake_offset",
    "trigger_screen_shake",
    "update_screen_shake",
]
