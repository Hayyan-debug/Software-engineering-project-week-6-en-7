from __future__ import annotations

import pygame

from src.audio import AudioManager
from src.combat.bow import Bow
from src.entities.fighter import Fighter
from src.render.spritesheet import SpritesheetHandler


class BowFighter(Fighter):
    """Ranged attacker. Slower on ground but good air mobility."""

    WALK_SPEED = 250
    JUMP_FORCE = -600
    WEIGHT = 0.85
    COLOR = (100, 220, 130)

    def __init__(
        self,
        x: float,
        y: float,
        player_id: int,
        audio_manager: AudioManager | None = None,
        is_local_player: bool = True,
    ):
        super().__init__(
            x,
            y,
            player_id,
            audio_manager=audio_manager,
            is_local_player=is_local_player,
        )
        self.weapon = Bow()
        self.bow_sprite_handler = SpritesheetHandler("assets/BowSpriteSheet.png", cols=4, rows=3)
        self.bow_idle_frame = 0
        self.bow_attack_frames = [1, 2, 3, 4]
        self.bow_scale = 0.20
        self.bow_hand_offset_right = (0, 24)
        self.bow_hand_offset_left = (0, 24)

    def special_move(self, direction: int) -> None:
        """Fire a bow projectile."""
        if self.weapon is None:
            return
        attacks = self.weapon.try_attack(self.rect, self.facing_right)
        if attacks:
            self.pending_attacks.extend(attacks)
            self.anim_state = "attack"
            self.anim_frame = 0
            self.attack_timer = self.attack_duration

    def draw_character(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        super().draw_character(surface, cam_x, cam_y)
        self._draw_bow(surface, cam_x, cam_y)

    def _draw_bow(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        if self.attack_timer > 0 and self.bow_attack_frames:
            attack_progress = 1.0 - (self.attack_timer / max(self.attack_duration, 0.001))
            attack_progress = max(0.0, min(attack_progress, 0.999))
            frame_slot = int(attack_progress * len(self.bow_attack_frames))
            frame_idx = self.bow_attack_frames[frame_slot]
        else:
            frame_idx = self.bow_idle_frame

        bow = self.bow_sprite_handler.get_frame(frame_idx)
        bw = max(1, int(self.bow_sprite_handler.frame_w * self.bow_scale))
        bh = max(1, int(self.bow_sprite_handler.frame_h * self.bow_scale))
        bow = pygame.transform.scale(bow, (bw, bh))

        if not self.facing_right:
            bow = pygame.transform.flip(bow, True, False)

        rx = int(self.x) - cam_x
        ry = int(self.y) - cam_y
        if self.facing_right:
            hand_x = rx + self.bow_hand_offset_right[0]
            hand_y = ry + self.bow_hand_offset_right[1]
            draw_x = hand_x
        else:
            hand_x = rx + self.bow_hand_offset_left[0]
            hand_y = ry + self.bow_hand_offset_left[1]
            draw_x = hand_x - bw

        draw_y = hand_y - int(bh * 0.45)
        surface.blit(bow, (draw_x, draw_y))
