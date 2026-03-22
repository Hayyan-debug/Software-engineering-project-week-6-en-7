from __future__ import annotations

import pygame

from src.audio import AudioManager


class InputHandler:
    """
    Maps keyboard state -> actions for a single local player.
    Supports two control schemes (WASD or Arrow keys) to allow local testing.
    """

    SCHEMES = {
        "wasd": {
            "left": pygame.K_a,
            "right": pygame.K_d,
            "jump": pygame.K_w,
            "dash": pygame.K_LSHIFT,
            "special": pygame.K_f,
        },
        "arrows": {
            "left": pygame.K_LEFT,
            "right": pygame.K_RIGHT,
            "jump": pygame.K_UP,
            "dash": pygame.K_RSHIFT,
            "special": pygame.K_SLASH,
        },
    }

    def __init__(self, scheme: str = "wasd", audio_manager: AudioManager | None = None):
        self.keys = self.SCHEMES[scheme]
        self._prev_keys: set = set()
        self.audio_manager = audio_manager

    def process(self, fighter, keys_down, events: list) -> None:
        """Apply keyboard state to the fighter this frame."""
        pressed = set()

        # --- Held keys -> continuous actions ---
        direction = 0
        if keys_down[self.keys["left"]]:
            direction -= 1
            pressed.add("left")
        if keys_down[self.keys["right"]]:
            direction += 1
            pressed.add("right")
        fighter.move(direction)

        # --- Pressed-this-frame keys -> one-shot actions ---
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == self.keys["jump"]:
                    fighter.jump()
                if event.key == self.keys["dash"]:
                    fighter.dash(direction if direction != 0 else (1 if fighter.facing_right else -1))
                if event.key == self.keys["special"]:
                    if self.audio_manager is not None and fighter.weapon and fighter.weapon.can_attack():
                        self.audio_manager.play_combat_attack_sfx(
                            fighter.weapon.name,
                            opponent=not fighter.is_local_player,
                        )
                    fighter.special_move(1 if fighter.facing_right else -1)

        # Consume buffered jump on landing
        fighter.try_buffered_jump()
        self._prev_keys = pressed
