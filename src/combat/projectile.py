from __future__ import annotations

import pygame


class Projectile:
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
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rect.topleft = (int(self.x), int(self.y))
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
