"""Bow weapon implementation that fires projectile attacks."""

from __future__ import annotations

import pygame

from .projectile import Projectile
from .weapon import Weapon


class Bow(Weapon):
    """Ranged weapon that creates moving projectiles."""

    def __init__(self) -> None:
        """Set bow stats and projectile defaults."""
        super().__init__(name="Bow", damage=8, cooldown=0.45, knockback=200)
        self.projectile_speed = 700.0
        self.projectile_lifetime = 1.2
        self.projectile_width = 18
        self.projectile_height = 8

    def attack(self, owner_rect: pygame.Rect, facing_right: bool) -> list[Projectile]:
        """Spawn and return one projectile traveling in the facing direction."""
        spawn_x = owner_rect.right if facing_right else owner_rect.left - self.projectile_width
        spawn_y = owner_rect.y + owner_rect.height // 2 - self.projectile_height // 2
        direction = 1 if facing_right else -1
        projectile = Projectile(
            x=spawn_x,
            y=spawn_y,
            vx=direction * self.projectile_speed,
            vy=0.0,
            damage=self.damage,
            knockback=self.knockback,
            lifetime=self.projectile_lifetime,
            width=self.projectile_width,
            height=self.projectile_height,
        )
        return [projectile]
