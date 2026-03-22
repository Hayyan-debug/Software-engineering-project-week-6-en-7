"""Sword fighter entity with fast melee-focused behavior."""

from __future__ import annotations

import pygame

from src.audio import AudioManager
from src.combat.sword import Sword
from src.entities.fighter import Fighter
from src.render.spritesheet import SpritesheetHandler


class SwordFighter(Fighter):
    """Fast, close-range attacker. Slightly lighter."""

    WALK_SPEED = 300
    JUMP_FORCE = -650
    WEIGHT = 0.9
    COLOR = (100, 180, 255)

    def __init__(
        self,
        x: float,
        y: float,
        player_id: int,
        audio_manager: AudioManager | None = None,
        is_local_player: bool = True,
    ):
        """Initialize sword fighter stats, weapon, and sword sprite setup."""
        super().__init__(
            x,
            y,
            player_id,
            audio_manager=audio_manager,
            is_local_player=is_local_player,
        )
        self.weapon = Sword()
        self.sword_sprite_handler = SpritesheetHandler("assets/SwordSpriteSheet.png", cols=4, rows=3)
        self.sword_idle_frame = 0
        self.sword_attack_frames = [1, 2, 3, 4]
        self.sword_scale = 0.22
        self.sword_hand_offset_right = (20, 10)
        self.sword_hand_offset_left = (20, 10)

    def special_move(self, direction: int) -> None:
        """Sword swing attack."""
        if self.shielding:
            return
        if self.weapon is None:
            return
        hitboxes = self.weapon.try_attack(self.rect, self.facing_right)
        if hitboxes:
            self.anim_state = "attack"
            self.anim_frame = 0
            self.anim_timer = 0.0
            self.attack_timer = self.attack_duration

    def draw_character(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Draw base fighter sprite and sword overlay."""
        super().draw_character(surface, cam_x, cam_y)
        self._draw_sword(surface, cam_x, cam_y)

    def _draw_sword(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Draw sword sprite frame aligned to the fighter hand position."""
        if self.attack_timer > 0 and self.sword_attack_frames:
            attack_progress = 1.0 - (self.attack_timer / max(self.attack_duration, 0.001))
            attack_progress = max(0.0, min(attack_progress, 0.999))
            frame_slot = int(attack_progress * len(self.sword_attack_frames))
            frame_idx = self.sword_attack_frames[frame_slot]
        else:
            frame_idx = self.sword_idle_frame

        sword = self.sword_sprite_handler.get_frame(frame_idx)
        sw = max(1, int(self.sword_sprite_handler.frame_w * self.sword_scale))
        sh = max(1, int(self.sword_sprite_handler.frame_h * self.sword_scale))
        sword = pygame.transform.scale(sword, (sw, sh))

        if not self.facing_right:
            sword = pygame.transform.flip(sword, True, False)

        rx = int(self.x) - cam_x
        ry = int(self.y) - cam_y
        if self.facing_right:
            hand_x = rx + self.sword_hand_offset_right[0]
            hand_y = ry + self.sword_hand_offset_right[1]
            draw_x = hand_x
        else:
            hand_x = rx + self.sword_hand_offset_left[0]
            hand_y = ry + self.sword_hand_offset_left[1]
            draw_x = hand_x - sw

        draw_y = hand_y - int(sh * 0.45)
        surface.blit(sword, (draw_x, draw_y))
