"""Sword weapon implementation with a short-lived melee hitbox."""

import pygame
from .weapon import Weapon

class Sword(Weapon):
    """Fast close-range weapon that spawns one swing hitbox."""

    def __init__(self):
        """Set sword stats and swing state."""
        super().__init__(name="Sword", damage=10, cooldown=0.35, knockback=250)
        self.swing_duration = 0.12
        self.swing_timer = 0.0
        self.active_hitbox = None

    def attack(self, owner_rect, facing_right):
        """Create and return the sword hitbox in front of the owner."""
        self.swing_timer = self.swing_duration

        hitbox_width = 50
        hitbox_height = 30
        offset = owner_rect.width if facing_right else -hitbox_width

        self.active_hitbox = pygame.Rect(
            owner_rect.x + offset,
            owner_rect.y + owner_rect.height // 3,
            hitbox_width,
            hitbox_height
        )

        return [self.active_hitbox]

    def update(self, dt):
        """Update cooldown and clear the hitbox after the swing ends."""
        super().update(dt)

        if self.swing_timer > 0:
            self.swing_timer -= dt
        else:
            self.active_hitbox = None

    def get_hitboxes(self):
        """Return currently active sword hitboxes."""
        if self.active_hitbox:
            return [self.active_hitbox]
        return []
