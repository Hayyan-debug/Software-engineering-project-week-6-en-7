"""Base fighter entity with shared movement, physics, and state sync logic."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import pygame

from src.audio import AudioManager
from src.render.spritesheet import SpritesheetHandler

if TYPE_CHECKING:
    from src.game.arena import Tile


GRAVITY = 1800
TERMINAL_VELOCITY = 900
JUMP_FORCE = -620
COYOTE_TIME = 0.10
JUMP_BUFFER = 0.10
DASH_SPEED = 900
DASH_DURATION = 0.15
DASH_COOLDOWN = 0.8
WALK_SPEED = 280
KNOCKBACK_FRICTION = 0.94
MOVE_SFX_WALK_COOLDOWN = 0.22
MOVE_SFX_JUMP_COOLDOWN = 0.08
MOVE_SFX_DASH_COOLDOWN = 0.08
MOVE_SFX_LAND_COOLDOWN = 0.12
MOVE_SFX_WALK_SPEED_THRESHOLD = 40.0
DUCK_FAST_FALL_MULTIPLIER = 2.0

WIDTH = 1280
HEIGHT = 720
KO_PERCENTAGE = 120

WHITE = (255, 255, 255)
RED = (220, 60, 60)
ORANGE = (255, 180, 80)
YELLOW = (255, 230, 100)


class Fighter(ABC):
    """
    Abstract base for every playable fighter.
    Subclasses differ in stats and special moves but share all physics logic.
    """

    # --- Override these in subclasses ---
    WALK_SPEED: float = WALK_SPEED
    JUMP_FORCE: float = JUMP_FORCE
    WEIGHT: float = 1.0  # heavier = less knockback received
    COLOR: tuple = WHITE

    def __init__(
        self,
        x: float,
        y: float,
        player_id: int,
        audio_manager: AudioManager | None = None,
        is_local_player: bool = True,
    ):
        """Initialize fighter state, movement systems, and animation data."""
        self.player_id = player_id
        self.audio_manager = audio_manager
        self.is_local_player = is_local_player

        # Position & velocity
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0

        # Knockback velocity (separate so it decays independently)
        self.kb_vx = 0.0
        self.kb_vy = 0.0

        # Dimensions
        self.width = 40
        self.height = 60

        # State flags
        self.on_ground = False
        self.facing_right = True
        self.is_dead = False
        self.damage_pct = 0.0  # Smash-style damage percentage
        self.ducking = False
        self.shielding = False

        # Jump mechanics
        self.coyote_timer = 0.0
        self.jump_buffer = 0.0
        self.jumps_left = 2  # double-jump

        # Sprite & Animation setup
        sheet_path = "assets/spritesheet_luna.png" if player_id == 0 else "assets/spritesheet_raven.png"
        self.sprite_handler = SpritesheetHandler(sheet_path)

        self.anim_state = "idle"
        self.anim_frame = 0
        self.anim_timer = 0.0
        self.anim_speed = 0.15  # seconds per frame

        # Dash mechanics
        self.dashing = False
        self.dash_timer = 0.0
        self.dash_cooldown = 0.0
        self.dash_direction = 1

        self.pending_hit_events = []  # Queue of hit events to send over network
        self._movement_sfx_next_allowed: dict[str, float] = {
            "walk": 0.0,
            "jump": 0.0,
            "dash": 0.0,
            "land": 0.0,
        }
        self._movement_sfx_cooldowns: dict[str, float] = {
            "walk": MOVE_SFX_WALK_COOLDOWN,
            "jump": MOVE_SFX_JUMP_COOLDOWN,
            "dash": MOVE_SFX_DASH_COOLDOWN,
            "land": MOVE_SFX_LAND_COOLDOWN,
        }
        self._movement_walk_speed_threshold = max(
            MOVE_SFX_WALK_SPEED_THRESHOLD, self.WALK_SPEED * 0.2
        )

        # Rect for collision (updated every frame)
        self.rect = pygame.Rect(int(self.x), int(self.y), self.width, self.height)

        # Animation state locks
        self.attack_timer = 0.0
        self.attack_duration = 0.4
        self.weapon = None
        self.pending_attacks: list[object] = []

    @abstractmethod
    def special_move(self, direction: int) -> None:
        """Weapon-specific special action (sword slash, arrow shot, etc.)."""

    def consume_pending_attacks(self) -> list[object]:
        """Return queued attacks and clear the pending queue."""
        attacks = self.pending_attacks
        self.pending_attacks = []
        return attacks

    def draw_character(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Draw the animated sprite."""
        rx = int(self.x) - cam_x
        ry = int(self.y) - cam_y

        # Animation data
        anims = {
            "idle": [0],
            "run": [2, 3, 4, 5],
            "jump": [6, 7],
            "fall": [8, 9],
            "duck": [8],
            "dash": [10],
            "hurt": [16],
            "attack": [12, 13],
            "shield": [17],
        }
        frames = anims.get(self.anim_state, [0])
        frame_idx = frames[self.anim_frame % len(frames)]

        sprite = self.sprite_handler.get_frame(frame_idx)

        # Flip if facing left
        if not self.facing_right:
            sprite = pygame.transform.flip(sprite, True, False)

        # Scale to match fighter height (60px)
        # Original frames are ~124px tall, let's keep aspect ratio roughly
        scale = self.height / self.sprite_handler.frame_h * 1.8  # 1.8x for extra juice
        sw = int(self.sprite_handler.frame_w * scale)
        sh = int(self.sprite_handler.frame_h * scale)
        sprite = pygame.transform.scale(sprite, (sw, sh))

        # Draw centered horizontally, feet on bottom of rect
        draw_x = rx + self.width // 2 - sw // 2
        draw_y = ry + self.height - sh + 5  # slight offset for feet depth

        surface.blit(sprite, (draw_x, draw_y))

    def update(self, dt: float, tiles: list[Tile]) -> None:
        """Main physics step."""
        was_on_ground = self.on_ground
        was_dashing = self.dashing

        self._update_timers(dt)
        if self.weapon is not None:
            self.weapon.update(dt)

        if self.dashing:
            self._update_dash(dt)
        else:
            self._apply_gravity(dt)
            self._apply_ducking_movement(dt)

        self._apply_knockback()
        self._move_and_collide(dt, tiles)
        if self.shielding and not self.on_ground:
            self.shielding = False
        self._check_ko()
        self._handle_movement_sfx(was_on_ground, was_dashing)

        # Sync rect
        self.rect.topleft = (int(self.x), int(self.y))
        self._update_animation(dt)

    def _update_animation(self, dt: float) -> None:
        """Update animation state and advance frame timing."""
        # Determine state
        prev_state = self.anim_state
        if self.shielding:
            self.anim_state = "shield"
        elif self.ducking:
            self.anim_state = "duck"
        elif self.attack_timer > 0:
            self.anim_state = "attack"
        elif self.damage_pct > 100 and self.kb_vx != 0:  # Hit stun / high knockback
            self.anim_state = "hurt"
        elif self.dashing:
            self.anim_state = "dash"
        elif not self.on_ground:
            if self.vy < -5:
                self.anim_state = "jump"
            elif self.vy > 5:
                self.anim_state = "fall"
            else:
                self.anim_state = "idle"
        elif abs(self.vx) > 10:
            self.anim_state = "run"
        else:
            self.anim_state = "idle"

        if self.anim_state != prev_state:
            self.anim_frame = 0
            self.anim_timer = 0.0

        # Update frame
        self.anim_timer += dt

        # Frame indices mapping (based on sheets)
        anims = {
            "idle": [0],
            "run": [2, 3, 4, 5],
            "jump": [6, 7],
            "fall": [8, 9],
            "duck": [8],
            "dash": [10],
            "hurt": [16],
            "attack": [12, 13],  # triggered by special_move normally
            "shield": [17],
        }

        frames = anims.get(self.anim_state, [0])

        # Adjust speed
        speed = self.anim_speed
        if self.anim_state == "run":
            speed = 0.1

        if self.anim_timer >= speed:
            self.anim_timer = 0.0
            self.anim_frame = (self.anim_frame + 1) % len(frames)

    def _update_timers(self, dt: float) -> None:
        """Tick movement, dash, jump, and attack timers."""
        if not self.on_ground:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)
        self.jump_buffer = max(0.0, self.jump_buffer - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.attack_timer = max(0.0, self.attack_timer - dt)

        if self.dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0:
                self.dashing = False
                self.vx = self.dash_direction * self.WALK_SPEED * 0.4

    def _apply_gravity(self, dt: float) -> None:
        """Apply gravity while respecting terminal fall speed."""
        self.vy += GRAVITY * dt
        self.vy = min(self.vy, TERMINAL_VELOCITY)

    def _apply_ducking_movement(self, dt: float) -> None:
        """Apply extra downward acceleration when fast-falling while ducking."""
        if self.ducking and not self.on_ground:
            extra_gravity = GRAVITY * (DUCK_FAST_FALL_MULTIPLIER - 1.0)
            self.vy += extra_gravity * dt
            self.vy = min(self.vy, TERMINAL_VELOCITY)

    def _apply_knockback(self) -> None:
        """Decay knockback velocity over time."""
        self.kb_vx *= KNOCKBACK_FRICTION
        self.kb_vy *= KNOCKBACK_FRICTION
        if abs(self.kb_vx) < 1:
            self.kb_vx = 0
        if abs(self.kb_vy) < 1:
            self.kb_vy = 0

    def _move_and_collide(self, dt: float, tiles: list[Tile]) -> None:
        """Move the fighter and resolve tile collisions on both axes."""
        total_vx = self.vx + self.kb_vx
        total_vy = self.vy + self.kb_vy

        # --- Horizontal ---
        self.x += total_vx * dt
        self.rect.x = int(self.x)
        for tile in tiles:
            if self.rect.colliderect(tile.rect):
                if total_vx > 0:
                    self.rect.right = tile.rect.left
                    self.kb_vx = 0
                elif total_vx < 0:
                    self.rect.left = tile.rect.right
                    self.kb_vx = 0
                self.x = float(self.rect.x)
                self.vx = 0

        # Vertical
        was_on_ground = self.on_ground
        self.on_ground = False

        self.y += total_vy * dt
        self.rect.y = int(self.y)
        for tile in tiles:
            if self.rect.colliderect(tile.rect):
                if total_vy > 0:  # falling -> land
                    self.rect.bottom = tile.rect.top
                    self.vy = 0
                    self.kb_vy = 0
                    self.on_ground = True
                    self.jumps_left = 2
                elif total_vy < 0:  # rising -> hit ceiling
                    self.rect.top = tile.rect.bottom
                    self.vy = 0
                    self.kb_vy = 0
                self.y = float(self.rect.y)

        # Snap to ground when exactly touching tile top (colliderect misses edge-touch)
        if not self.on_ground and total_vy >= 0:
            for tile in tiles:
                x_overlap = self.rect.right > tile.rect.left and self.rect.left < tile.rect.right
                touching_top = abs(self.rect.bottom - tile.rect.top) <= 1
                if x_overlap and touching_top:
                    self.on_ground = True
                    self.vy = 0
                    self.kb_vy = 0
                    self.rect.bottom = tile.rect.top
                    self.y = float(self.rect.y)
                    self.jumps_left = 2
                    break

        # Reset coyote timer when freshly landing
        if self.on_ground and not was_on_ground:
            self.coyote_timer = COYOTE_TIME

        # Start coyote countdown when leaving ground without jumping
        if was_on_ground and not self.on_ground and self.vy >= 0:
            self.coyote_timer = COYOTE_TIME

    def _check_ko(self) -> None:
        """Mark fighter as dead when blasted off-screen."""
        if self.x < -300 or self.x > WIDTH + 300 or self.y < -400 or self.y > HEIGHT + 200:
            self.is_dead = True

    def _movement_time(self) -> float:
        """Return current game time in seconds for SFX cooldown tracking."""
        return pygame.time.get_ticks() / 1000.0

    def _try_play_movement_sfx(self, event: str) -> bool:
        """Play a movement SFX event if cooldown and audio settings allow it."""
        if self.audio_manager is None:
            return False
        cooldown = self._movement_sfx_cooldowns.get(event, 0.0)
        now = self._movement_time()
        if now < self._movement_sfx_next_allowed.get(event, 0.0):
            return False
        self._movement_sfx_next_allowed[event] = now + cooldown
        return self.audio_manager.play_movement_sfx(
            event,
            opponent=not self.is_local_player,
        )

    def _handle_movement_sfx(self, was_on_ground: bool, was_dashing: bool) -> None:
        """Trigger local movement SFX transitions (land, dash, walk)."""
        if not was_on_ground and self.on_ground:
            self._try_play_movement_sfx("land")
        if not was_dashing and self.dashing:
            self._try_play_movement_sfx("dash")
        if self.on_ground and not self.dashing and abs(self.vx) >= self._movement_walk_speed_threshold:
            self._try_play_movement_sfx("walk")

    def _handle_remote_state_sfx(self, was_on_ground: bool, was_dashing: bool, previous_vy: float) -> None:
        """Trigger movement SFX for state changes received from snapshots."""
        if was_on_ground and not self.on_ground and self.vy < -5 and previous_vy >= -5:
            self._try_play_movement_sfx("jump")
        self._handle_movement_sfx(was_on_ground, was_dashing)

    def move(self, direction: int) -> None:
        """direction: -1 left, 0 stop, +1 right"""
        if self.dashing:
            return
        if self.shielding:
            self.vx = 0
            return
        if self.ducking and self.on_ground:
            self.vx = 0
            return
        self.vx = direction * self.WALK_SPEED
        if direction != 0:
            self.facing_right = direction > 0

    def set_shielding(self, is_shielding: bool) -> None:
        """Enable shielding only while grounded; stop horizontal movement."""
        self.shielding = is_shielding and self.on_ground
        if self.shielding:
            self.vx = 0

    def set_ducking(self, is_ducking: bool) -> None:
        """Set ducking state and halt movement when crouching on ground."""
        self.ducking = is_ducking
        if self.ducking and self.on_ground:
            self.vx = 0

    def jump(self) -> None:
        """Called when the jump button is pressed."""
        if self.shielding:
            return
        can_jump = self.on_ground or self.coyote_timer > 0
        if can_jump:
            self._do_jump()
        elif self.jumps_left > 0:
            self._do_jump()
        else:
            # Buffer the jump
            self.jump_buffer = JUMP_BUFFER

    def _do_jump(self) -> None:
        """Execute jump impulse and consume one jump charge."""
        self.vy = self.JUMP_FORCE
        self.on_ground = False
        self.coyote_timer = 0.0
        if self.jumps_left > 0:
            self.jumps_left -= 1
        self._try_play_movement_sfx("jump")

    def try_buffered_jump(self) -> None:
        """Called on landing to consume a buffered jump."""
        if self.jump_buffer > 0 and self.on_ground:
            self._do_jump()
            self.jump_buffer = 0.0

    def dash(self, direction: int) -> None:
        """Initiate a dash if off cooldown."""
        if self.shielding:
            return
        if self.dash_cooldown > 0 or self.dashing:
            return
        self.dashing = True
        self.dash_timer = DASH_DURATION
        self.dash_cooldown = DASH_COOLDOWN
        self.dash_direction = direction if direction != 0 else (1 if self.facing_right else -1)
        self.vx = self.dash_direction * DASH_SPEED
        self.vy = 0
        self.kb_vx = 0
        self.kb_vy = 0

    def receive_knockback(self, source_x: float, power: float) -> None:
        """
        Apply Smash-style knockback.
        Higher damage_pct -> more knockback received.
        """
        scale = (1 + self.damage_pct / 50) / self.WEIGHT
        direction = 1 if self.x >= source_x else -1
        self.kb_vx = direction * power * scale
        self.kb_vy = -power * scale * 0.6  # upward component

    def respawn(self, x: float, y: float) -> None:
        """Reset position and combat state after a KO."""
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.kb_vx = self.kb_vy = 0.0
        self.is_dead = False
        self.damage_pct = 0.0
        self.jumps_left = 2

    def to_dict(self) -> dict:
        """Serialize fighter state for networking."""
        return {
            "id": self.player_id,
            "x": self.x,
            "y": self.y,
            "vx": self.vx,
            "vy": self.vy,
            "kb_vx": self.kb_vx,
            "kb_vy": self.kb_vy,
            "facing": self.facing_right,
            "damage_pct": self.damage_pct,
            "is_dead": self.is_dead,
            "dashing": self.dashing,
            "anim_state": self.anim_state,
            "anim_frame": self.anim_frame,
            "attack_timer": self.attack_timer,
            "on_ground": self.on_ground,
            "ducking": self.ducking,
            "shielding": self.shielding,
        }

    def from_dict(self, data: dict) -> None:
        """Apply a server snapshot (used for the remote player)."""
        was_on_ground = self.on_ground
        was_dashing = self.dashing
        previous_vy = self.vy
        was_attacking = self.attack_timer > 0 or self.anim_state == "attack"

        self.x = data.get("x", self.x)
        self.y = data.get("y", self.y)
        self.vx = data.get("vx", self.vx)
        self.vy = data.get("vy", self.vy)
        self.kb_vx = data.get("kb_vx", self.kb_vx)
        self.kb_vy = data.get("kb_vy", self.kb_vy)
        self.facing_right = data.get("facing", self.facing_right)
        self.damage_pct = data.get("damage_pct", self.damage_pct)
        self.is_dead = data.get("is_dead", self.is_dead)
        self.dashing = data.get("dashing", self.dashing)
        self.anim_state = data.get("anim_state", self.anim_state)
        self.anim_frame = data.get("anim_frame", self.anim_frame)
        self.attack_timer = data.get("attack_timer", self.attack_timer)
        self.on_ground = data.get("on_ground", self.on_ground)
        self.ducking = data.get("ducking", self.ducking)
        self.shielding = data.get("shielding", self.shielding)
        self.rect.topleft = (int(self.x), int(self.y))

        is_attacking = self.attack_timer > 0 or self.anim_state == "attack"
        if not was_attacking and is_attacking and self.audio_manager and self.weapon:
            self.audio_manager.play_combat_attack_sfx(
                self.weapon.name,
                opponent=not self.is_local_player,
            )

        self._handle_remote_state_sfx(was_on_ground, was_dashing, previous_vy)

    def draw(self, surface: pygame.Surface, cam_x: int = 0, cam_y: int = 0) -> None:
        """Render fighter visuals and damage HUD."""
        self.draw_character(surface, cam_x, cam_y)
        self._draw_damage_hud(surface, cam_x, cam_y)

    def _draw_damage_hud(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Tiny damage % above the fighter."""
        font = pygame.font.SysFont("impact", 20)
        label = f"{int(self.damage_pct)}%"
        color = YELLOW if self.damage_pct < 60 else ORANGE if self.damage_pct < KO_PERCENTAGE else RED
        surf = font.render(label, True, color)
        px = int(self.x) - cam_x + self.width // 2 - surf.get_width() // 2
        py = int(self.y) - cam_y - 28
        surface.blit(surf, (px, py))
