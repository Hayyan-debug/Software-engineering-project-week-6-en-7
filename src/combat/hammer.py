"""Hammer weapon implementation with a wind-up followed by impact."""

from __future__ import annotations

import pygame

from .weapon import Weapon


class Hammer(Weapon):
    """Slow heavy weapon with delayed impact and high knockback."""

    def __init__(self) -> None:
        """Set hammer stats and timers for wind-up/impact phases."""
        super().__init__(name="Hammer", damage=18, cooldown=0.75, knockback=450)
        self.base_damage = self.damage
        self.base_knockback = self.knockback
        self.windup_duration = 0.5
        self.impact_duration = 0.10
        self.windup_timer = 0.0
        self.impact_timer = 0.0
        self.pending_attack = False
        self.active_hitbox: pygame.Rect | None = None
        self.owner_snapshot_rect: pygame.Rect | None = None
        self.owner_facing = True
        self._attack_on_ground = True

    def set_attack_context(self, on_ground: bool) -> None:
        """Store whether the next attack starts from the ground."""
        self._attack_on_ground = on_ground

    def attack(self, owner_rect: pygame.Rect, facing_right: bool) -> list[object]:
        """Begin the attack wind-up and snapshot owner position/direction."""
        self.pending_attack = True
        self.windup_timer = self.windup_duration
        self.impact_timer = 0.0
        self.active_hitbox = None
        self.owner_snapshot_rect = owner_rect.copy()
        self.owner_facing = facing_right
        return []

    def update(self, dt: float) -> None:
        """Advance hammer state and handle wind-up and impact expiration."""
        super().update(dt)

        if self.pending_attack:
            self.windup_timer -= dt
            if self.windup_timer <= 0:
                self._start_impact()
            return

        if self.impact_timer > 0:
            self.impact_timer -= dt
            if self.impact_timer <= 0:
                self.active_hitbox = None
                self.damage = self.base_damage
                self.knockback = self.base_knockback

    def _start_impact(self) -> None:
        """Spawn the active impact hitbox when wind-up finishes."""
        self.pending_attack = False
        self.impact_timer = self.impact_duration

        if self.owner_snapshot_rect is None:
            self.active_hitbox = None
            return

        width = 150
        height = 50
        damage_scale = 1.0
        knockback_scale = 1.0
        if not self._attack_on_ground:
            width = 70
            height = 44
            damage_scale = 0.8
            knockback_scale = 0.8

        self.damage = self.base_damage * damage_scale
        self.knockback = self.base_knockback * knockback_scale

        owner_rect = self.owner_snapshot_rect
        forward_offset = 18 if self.owner_facing else -18
        center_x = owner_rect.centerx + forward_offset
        x = center_x - width // 2
        y = owner_rect.bottom - height // 2
        self.active_hitbox = pygame.Rect(x, y, width, height)

    def get_hitboxes(self) -> list[pygame.Rect]:
        """Return the active hammer impact hitbox if one exists."""
        if self.active_hitbox is not None:
            return [self.active_hitbox]
        return []
