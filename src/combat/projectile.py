"""Projectile model used by ranged combat attacks."""

from __future__ import annotations

import pygame


class Projectile:
    """Simple moving hit object with lifetime-based expiration."""

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        damage: float,
        knockback: float,
        lifetime: float,
        width: int = 18,
        height: int = 8,
    ) -> None:
        """Initialize projectile position, velocity, damage, and hitbox."""
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.damage = float(damage)
        self.knockback = float(knockback)
        self.lifetime = float(lifetime)
        self.alive = True
        self.rect = pygame.Rect(int(self.x), int(self.y), width, height)

    def update(self, dt: float) -> None:
        """Move the projectile and mark it dead once lifetime expires."""
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rect.topleft = (int(self.x), int(self.y))
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
