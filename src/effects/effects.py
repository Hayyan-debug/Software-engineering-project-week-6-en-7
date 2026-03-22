from __future__ import annotations

from dataclasses import dataclass
import random

import pygame


Color = tuple[int, int, int]

PARTICLE_BASE_COUNT = 12
PARTICLE_COMBO_BONUS_STEP = 2
PARTICLE_COMBO_BONUS_MAX = 10
PARTICLE_BLOCKED_SCALE = 0.45


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


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    age: float
    duration: float
    size: float
    color: Color
    alpha: int
    gravity: float = 280.0
    drag: float = 2.0


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


def create_hit_particles(
    x: int,
    y: int,
    weapon_name: str,
    combo_count: int = 1,
    blocked: bool = False,
) -> list[Particle]:
    palette = _particle_palette(weapon_name)
    combo_bonus = min(max(0, combo_count - 1) * PARTICLE_COMBO_BONUS_STEP, PARTICLE_COMBO_BONUS_MAX)
    count = PARTICLE_BASE_COUNT + combo_bonus
    if blocked:
        count = max(4, int(count * PARTICLE_BLOCKED_SCALE))

    particles: list[Particle] = []
    for _ in range(count):
        color = random.choice(palette)
        speed_min = 80.0 if blocked else 130.0
        speed_max = 210.0 if blocked else 340.0
        speed = random.uniform(speed_min, speed_max)
        vx = random.uniform(-1.0, 1.0) * speed
        vy = random.uniform(-1.0, 1.0) * speed
        particles.append(
            Particle(
                x=float(x),
                y=float(y),
                vx=vx,
                vy=vy,
                age=0.0,
                duration=random.uniform(0.18, 0.32),
                size=random.uniform(1.6, 3.8),
                color=color,
                alpha=255,
                gravity=220.0 if blocked else 300.0,
                drag=3.0 if blocked else 2.2,
            )
        )
    return particles


def update_hit_effects(effects: list[HitEffect], dt: float) -> list[HitEffect]:
    alive: list[HitEffect] = []
    for effect in effects:
        effect.age += dt
        if effect.age < effect.duration:
            alive.append(effect)
    return alive


def update_particles(particles: list[Particle], dt: float) -> list[Particle]:
    alive: list[Particle] = []
    for particle in particles:
        particle.age += dt
        if particle.age >= particle.duration:
            continue

        damping = max(0.0, 1.0 - particle.drag * dt)
        particle.vx *= damping
        particle.vy = (particle.vy * damping) + (particle.gravity * dt)

        particle.x += particle.vx * dt
        particle.y += particle.vy * dt

        progress = particle.age / max(particle.duration, 0.001)
        particle.alpha = max(0, int(255 * (1.0 - progress)))
        alive.append(particle)
    return alive


def draw_hit_effects(surface: pygame.Surface, effects: list[HitEffect], cam_x: int = 0, cam_y: int = 0) -> None:
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

        surface.blit(
            ring_surface,
            (int(effect.x) - cam_x - ring_center[0], int(effect.y) - cam_y - ring_center[1]),
        )


def draw_particles(surface: pygame.Surface, particles: list[Particle], cam_x: int = 0, cam_y: int = 0) -> None:
    for particle in particles:
        if particle.alpha <= 0 or particle.size <= 0:
            continue
        radius = max(1, int(particle.size))
        particle_surface = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
        center = (particle_surface.get_width() // 2, particle_surface.get_height() // 2)
        pygame.draw.circle(particle_surface, (*particle.color, particle.alpha), center, radius)
        surface.blit(
            particle_surface,
            (int(particle.x) - cam_x - center[0], int(particle.y) - cam_y - center[1]),
        )


def _particle_palette(weapon_name: str) -> tuple[Color, ...]:
    weapon_key = weapon_name.lower().strip()
    if weapon_key == "sword":
        return ((120, 245, 255), (180, 255, 255), (95, 205, 255))
    if weapon_key == "bow":
        return ((255, 190, 90), (255, 150, 60), (255, 220, 120))
    if weapon_key == "hammer":
        return ((255, 110, 80), (255, 165, 70), (230, 90, 70))
    return ((255, 230, 140), (255, 255, 255), (255, 180, 100))


def _lerp_color(a: Color, b: Color, t: float) -> Color:
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )
