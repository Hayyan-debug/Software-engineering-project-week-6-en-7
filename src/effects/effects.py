from __future__ import annotations

from dataclasses import dataclass

import pygame


Color = tuple[int, int, int]


@dataclass
class HitEffectPalette:
    outer_start: Color = (255, 80, 90)
    outer_end: Color = (255, 220, 110)
    inner_ring: Color = (120, 225, 255)
    flash: Color = (255, 255, 255)


@dataclass
class HitEffect:
    x: float
    y: float
    age: float
    duration: float
    start_radius: float
    end_radius: float
    palette: HitEffectPalette


def create_hit_effect(x: int, y: int, palette: HitEffectPalette | None = None) -> HitEffect:
    return HitEffect(
        x=float(x),
        y=float(y),
        age=0.0,
        duration=0.16,
        start_radius=8.0,
        end_radius=34.0,
        palette=palette if palette is not None else HitEffectPalette(),
    )


def update_hit_effects(effects: list[HitEffect], dt: float) -> list[HitEffect]:
    alive: list[HitEffect] = []
    for effect in effects:
        effect.age += dt
        if effect.age < effect.duration:
            alive.append(effect)
    return alive


def draw_hit_effects(surface: pygame.Surface, effects: list[HitEffect]) -> None:
    for effect in effects:
        duration = max(effect.duration, 0.001)
        progress = min(1.0, effect.age / duration)
        fade = 1.0 - progress

        radius = int(effect.start_radius + (effect.end_radius - effect.start_radius) * progress)
        flash_radius = max(2, int(8 * fade))
        outer_width = max(1, int(4 * fade))
        inner_radius = max(2, int(radius * 0.62))
        inner_width = max(1, int(3 * fade))

        alpha = int(255 * fade)
        if alpha <= 0 or radius <= 0:
            continue

        ring_surface = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
        ring_center = (ring_surface.get_width() // 2, ring_surface.get_height() // 2)

        outer_color = _lerp_color(effect.palette.outer_start, effect.palette.outer_end, progress)
        pygame.draw.circle(ring_surface, (*outer_color, alpha), ring_center, radius, outer_width)
        pygame.draw.circle(
            ring_surface, (*effect.palette.inner_ring, int(alpha * 0.9)), ring_center, inner_radius, inner_width
        )
        pygame.draw.circle(ring_surface, (*effect.palette.flash, int(alpha * 0.65)), ring_center, flash_radius)

        surface.blit(ring_surface, (int(effect.x) - ring_center[0], int(effect.y) - ring_center[1]))


def _lerp_color(a: Color, b: Color, t: float) -> Color:
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )
