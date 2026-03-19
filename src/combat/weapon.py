from __future__ import annotations
import pygame
from abc import ABC, abstractmethod



class Weapon(ABC):
    """Base weapon class with shared attributes and attack interface."""

    def __init__(
        self,
        name: str,
        damage: float,
        cooldown: float,
        knockback: float,
    ) -> None:
        self.name = name
        self.damage = damage
        self.cooldown = cooldown
        self.knockback = knockback
        self._cooldown_timer = 0.0

    def update(self, dt: float) -> None:
        self._cooldown_timer = max(0.0, self._cooldown_timer - dt)

    def can_attack(self) -> bool:
        return self._cooldown_timer <= 0.0

    def try_attack(
        self,
        owner_rect: pygame.Rect,
        facing_right: bool,
    ) -> list[pygame.Rect]:
        """Attempts an attack and returns active hitbox(es)."""
        if not self.can_attack():
            return []
        self._cooldown_timer = self.cooldown
        return self.attack(owner_rect, facing_right)

    @abstractmethod
    def attack(self, owner_rect: pygame.Rect, facing_right: bool) -> list[pygame.Rect]:
        """Perform attack and return newly created hitbox(es)."""