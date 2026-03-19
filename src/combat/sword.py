import pygame
from .weapon import Weapon

class Sword(Weapon):
    def __init__(self):
        super().__init__(name="Sword", damage=10, cooldown=20, knockback=100)
        self.swing_duration = 10   # frames
        self.swing_timer = 0
        self.active_hitbox = None

    def attack(self, owner_rect, facing_right):
        self.swing_timer = self.swing_duration

        offset = 40 if facing_right else -40

        self.active_hitbox = pygame.Rect(
            owner_rect.x + offset,
            owner_rect.y,
            50,
            30
        )

        return [self.active_hitbox]

    def update(self, dt):
        super().update(dt)

        if self.swing_timer > 0:
            self.swing_timer -= 1
        else:
            self.active_hitbox = None

    def get_hitboxes(self):
        if self.active_hitbox:
            return [self.active_hitbox]
        return []