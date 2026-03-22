"""Hammer fighter entity with heavy melee attacks and high durability."""

from __future__ import annotations

import pygame

from src.audio import AudioManager
from src.combat.hammer import Hammer
from src.entities.fighter import Fighter
from src.render.spritesheet import SpritesheetHandler


class HammerFighter(Fighter):
    """Heavy brawler. Slower but hits hard and is very hard to knock back."""

    WALK_SPEED = 220
    JUMP_FORCE = -550
    WEIGHT = 1.4
    COLOR = (220, 100, 100)

    def __init__(
        self,
        x: float,
        y: float,
        player_id: int,
        audio_manager: AudioManager | None = None,
        is_local_player: bool = True,
    ):
        """Initialize hammer fighter stats, weapon, and hammer sprite setup."""
        super().__init__(
            x,
            y,
            player_id,
            audio_manager=audio_manager,
            is_local_player=is_local_player,
        )
        self.weapon = Hammer()
        self.hammer_sprite_handler = SpritesheetHandler("assets/hammer_spritesheet.png", cols=4, rows=3)
        self.hammer_idle_frame = 0
        self.hammer_attack_frames = [1, 2, 3, 4, 5, 6, 7]
        self.hammer_scale = 0.26
        self.hammer_hand_offset_right = (19, 9)
        self.hammer_hand_offset_left = (18, 8)

    def special_move(self, direction: int) -> None:
        """Heavy hammer slam with wind-up then impact."""
        if self.shielding:
            return
        if self.weapon is None:
            return
        if not self.weapon.can_attack():
            return
        if isinstance(self.weapon, Hammer):
            self.weapon.set_attack_context(self.on_ground)
        self.weapon.try_attack(self.rect, self.facing_right)
        self.anim_state = "attack"
        self.anim_frame = 0
        self.anim_timer = 0.0
        self.attack_timer = self.attack_duration

    def draw_character(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Draw base fighter sprite and hammer overlay."""
        super().draw_character(surface, cam_x, cam_y)
        self._draw_hammer(surface, cam_x, cam_y)

    def _draw_hammer(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Draw hammer sprite frame aligned to the fighter hand position."""
        if self.attack_timer > 0 and self.hammer_attack_frames:
            attack_progress = 1.0 - (self.attack_timer / max(self.attack_duration, 0.001))
            attack_progress = max(0.0, min(attack_progress, 0.999))
            frame_slot = int(attack_progress * len(self.hammer_attack_frames))
            frame_idx = self.hammer_attack_frames[frame_slot]
        else:
            frame_idx = self.hammer_idle_frame

        hammer = self.hammer_sprite_handler.get_frame(frame_idx)
        hw = max(1, int(self.hammer_sprite_handler.frame_w * self.hammer_scale))
        hh = max(1, int(self.hammer_sprite_handler.frame_h * self.hammer_scale))
        hammer = pygame.transform.scale(hammer, (hw, hh))

        if not self.facing_right:
            hammer = pygame.transform.flip(hammer, True, False)

        rx = int(self.x) - cam_x
        ry = int(self.y) - cam_y
        if self.facing_right:
            hand_x = rx + self.hammer_hand_offset_right[0]
            hand_y = ry + self.hammer_hand_offset_right[1]
            draw_x = hand_x
        else:
            hand_x = rx + self.hammer_hand_offset_left[0]
            hand_y = ry + self.hammer_hand_offset_left[1]
            draw_x = hand_x - hw

        draw_y = hand_y - int(hh * 0.45)
        surface.blit(hammer, (draw_x, draw_y))
