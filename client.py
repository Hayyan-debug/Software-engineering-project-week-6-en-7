"""
client.py - Gauntlet Galaxy
Gameplay & Physics module (Person B: Finn)

Responsibilities:
- Input capture & local prediction
- Rendering loop
- Movement physics (run, jump, dash, knockback)
- Gravity, wall-jumping
- Collision with tiles and other players
"""

import pygame
import sys
from abc import ABC, abstractmethod
import asyncio

from src.audio import AudioManager, get_shared_audio_manager
from src.combat.bow import Bow
from src.combat.hammer import Hammer
from src.combat.projectile import Projectile
from src.combat.sword import Sword
from src.effects.effects import HitEffect, create_hit_effect, draw_hit_effects, update_hit_effects
from src.effects.hitstop import HitStopState, is_hit_stopped, trigger_hit_stop, update_hit_stop
from src.effects.screenshake import ScreenShakeState, get_screen_shake_offset, trigger_screen_shake, update_screen_shake
from src.game.arena import Tile, build_arena
from src.game.hud import HUD
from src.game.input import InputHandler
from src.network.network_client import NetworkClient
from src.render.spritesheet import SpritesheetHandler

# Constants


WIDTH, HEIGHT = 1280, 720
FPS = 60

# Map Mapping (ID -> Asset Name)
ARENA_MAPS = {
    0: "map_aethercleft.png",
    1: "map_nebulashards.png",
    2: "map_chronosgears.png",
    3: "map_gravitywell.png",
    4: "map_cometcauseway.png",
    5: "map_voidvortex.png",
}

# Physics
GRAVITY = 1800          # px/s²  — tune freely
TERMINAL_VELOCITY = 900 # px/s   — max fall speed
JUMP_FORCE = -620       # px/s   — initial upward velocity on jump
COYOTE_TIME = 0.10      # s      — grace window after walking off a ledge
JUMP_BUFFER = 0.10      # s      — jump queued before landing still works
DASH_SPEED = 900        # px/s
DASH_DURATION = 0.15    # s
DASH_COOLDOWN = 0.8     # s
WALK_SPEED = 280        # px/s
KNOCKBACK_FRICTION = 0.94   # multiplied per frame (applied to kb velocity)
MOVE_SFX_WALK_COOLDOWN = 0.22
MOVE_SFX_JUMP_COOLDOWN = 0.08
MOVE_SFX_DASH_COOLDOWN = 0.08
MOVE_SFX_LAND_COOLDOWN = 0.12
MOVE_SFX_WALK_SPEED_THRESHOLD = 40.0

# Knockback thresholds (Smash-style percentage)
KO_PERCENTAGE = 120     # above this, knockback can kill

# Colors (fallback if assets missing)
WHITE      = (255, 255, 255)
BLACK      = (0,   0,   0  )
RED        = (220, 60,  60 )
BLUE       = (60,  120, 220)
GREEN      = (80,  200, 80 )
ORANGE     = (255, 180, 80 )
YELLOW     = (255, 230, 100)
BG_COLOR   = (20,  20,  35 )

# Base character class (polymorphism requirement from assignment)


class Fighter(ABC):
    """
    Abstract base for every playable fighter.
    Subclasses differ in stats and special moves but share all physics logic.
    """

    # --- Override these in subclasses ---
    WALK_SPEED:   float = WALK_SPEED
    JUMP_FORCE:   float = JUMP_FORCE
    WEIGHT:       float = 1.0        # heavier = less knockback received
    COLOR:        tuple = WHITE

    def __init__(
        self,
        x: float,
        y: float,
        player_id: int,
        audio_manager: AudioManager | None = None,
        is_local_player: bool = True,
    ):
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
        self.width  = 40
        self.height = 60

        # State flags
        self.on_ground    = False
        self.facing_right = True
        self.is_dead      = False
        self.damage_pct   = 0.0      # Smash-style damage percentage

        # Jump mechanics
        self.coyote_timer  = 0.0
        self.jump_buffer   = 0.0
        self.jumps_left    = 2       # double-jump

        # Sprite & Animation setup
        sheet_path = "assets/spritesheet_luna.png" if player_id == 0 else "assets/spritesheet_raven.png"
        self.sprite_handler = SpritesheetHandler(sheet_path)
        
        self.anim_state = "idle"
        self.anim_frame = 0
        self.anim_timer = 0.0
        self.anim_speed = 0.15 # seconds per frame

        # Dash mechanics
        self.dashing         = False
        self.dash_timer      = 0.0
        self.dash_cooldown   = 0.0
        self.dash_direction  = 1
        
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


  
    #  Abstract interface                                                  #


    @abstractmethod
    def special_move(self, direction: int) -> None:
        """Weapon-specific special action (sword slash, arrow shot, etc.)."""

    def consume_pending_attacks(self) -> list[object]:
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
            "run":  [2, 3, 4, 5],
            "jump": [6, 7],
            "fall": [8, 9],
            "dash": [10],
            "hurt": [16],
            "attack": [12, 13],
            "shield": [17]
        }
        frames = anims.get(self.anim_state, [0])
        frame_idx = frames[self.anim_frame % len(frames)]
        
        sprite = self.sprite_handler.get_frame(frame_idx)
        
        # Flip if facing left
        if not self.facing_right:
            sprite = pygame.transform.flip(sprite, True, False)
        
        # Scale to match fighter height (60px)
        # Original frames are ~124px tall, let's keep aspect ratio roughly
        scale = self.height / self.sprite_handler.frame_h * 1.8 # 1.8x for extra juice
        sw = int(self.sprite_handler.frame_w * scale)
        sh = int(self.sprite_handler.frame_h * scale)
        sprite = pygame.transform.scale(sprite, (sw, sh))
        
        # Draw centered horizontally, feet on bottom of rect
        draw_x = rx + self.width // 2 - sw // 2
        draw_y = ry + self.height - sh + 5 # slight offset for feet depth
        
        surface.blit(sprite, (draw_x, draw_y))


    #  Physics update — called once per frame                             #

    def update(self, dt: float, tiles: list["Tile"]) -> None:
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

        self._apply_knockback()
        self._move_and_collide(dt, tiles)
        self._check_ko()
        self._handle_movement_sfx(was_on_ground, was_dashing)

        # Sync rect
        self.rect.topleft = (int(self.x), int(self.y))
        self._update_animation(dt)

    def _update_animation(self, dt: float) -> None:
        # Determine state
        prev_state = self.anim_state
        if self.attack_timer > 0:
            self.anim_state = "attack"
        elif self.damage_pct > 100 and self.kb_vx != 0: # Hit stun / high knockback
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
            "run":  [2, 3, 4, 5],
            "jump": [6, 7],
            "fall": [8, 9],
            "dash": [10],
            "hurt": [16],
            "attack": [12, 13], # triggered by special_move normally
            "shield": [17]
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
        if not self.on_ground:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)
        self.jump_buffer   = max(0.0, self.jump_buffer   - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.attack_timer  = max(0.0, self.attack_timer  - dt)

        if self.dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0:
                self.dashing = False
                self.vx = self.dash_direction * self.WALK_SPEED * 0.4

    def _apply_gravity(self, dt: float) -> None:
        self.vy += GRAVITY * dt
        self.vy = min(self.vy, TERMINAL_VELOCITY)

    def _apply_knockback(self) -> None:
        self.kb_vx *= KNOCKBACK_FRICTION
        self.kb_vy *= KNOCKBACK_FRICTION
        if abs(self.kb_vx) < 1:
            self.kb_vx = 0
        if abs(self.kb_vy) < 1:
            self.kb_vy = 0

    def _move_and_collide(self, dt: float, tiles: list["Tile"]) -> None:
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
                if total_vy > 0:                  # falling ➔ land
                    self.rect.bottom = tile.rect.top
                    self.vy    = 0
                    self.kb_vy = 0
                    self.on_ground  = True
                    self.jumps_left = 2
                elif total_vy < 0:                # rising ➔ hit ceiling
                    self.rect.top = tile.rect.bottom
                    self.vy    = 0
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
        if (self.x < -300 or self.x > WIDTH + 300 or
                self.y < -400 or self.y > HEIGHT + 200):
            self.is_dead = True

    def _movement_time(self) -> float:
        return pygame.time.get_ticks() / 1000.0

    def _try_play_movement_sfx(self, event: str) -> bool:
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
        if not was_on_ground and self.on_ground:
            self._try_play_movement_sfx("land")
        if not was_dashing and self.dashing:
            self._try_play_movement_sfx("dash")
        if (
            self.on_ground
            and not self.dashing
            and abs(self.vx) >= self._movement_walk_speed_threshold
        ):
            self._try_play_movement_sfx("walk")

    def _handle_remote_state_sfx(
        self, was_on_ground: bool, was_dashing: bool, previous_vy: float
    ) -> None:
        if was_on_ground and not self.on_ground and self.vy < -5 and previous_vy >= -5:
            self._try_play_movement_sfx("jump")
        self._handle_movement_sfx(was_on_ground, was_dashing)

    #  Input-driven actions                                                #
    

    def move(self, direction: int) -> None:
        """direction: -1 left, 0 stop, +1 right"""
        if self.dashing:
            return
        self.vx = direction * self.WALK_SPEED
        if direction != 0:
            self.facing_right = direction > 0

    def jump(self) -> None:
        """Called when the jump button is pressed."""
        can_jump = self.on_ground or self.coyote_timer > 0
        if can_jump:
            self._do_jump()
        elif self.jumps_left > 0:
            self._do_jump()
        else:
            # Buffer the jump
            self.jump_buffer = JUMP_BUFFER

    def _do_jump(self) -> None:
        self.vy = self.JUMP_FORCE
        self.on_ground    = False
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
        if self.dash_cooldown > 0 or self.dashing:
            return
        self.dashing        = True
        self.dash_timer     = DASH_DURATION
        self.dash_cooldown  = DASH_COOLDOWN
        self.dash_direction = direction if direction != 0 else (1 if self.facing_right else -1)
        self.vx  = self.dash_direction * DASH_SPEED
        self.vy  = 0
        self.kb_vx = 0
        self.kb_vy = 0

    def receive_knockback(self, source_x: float, power: float) -> None:
        """
        Apply Smash-style knockback.
        Higher damage_pct ➔ more knockback received.
        """
        scale = (1 + self.damage_pct / 50) / self.WEIGHT
        direction = 1 if self.x >= source_x else -1
        self.kb_vx = direction * power * scale
        self.kb_vy = -power * scale * 0.6   # upward component

    def respawn(self, x: float, y: float) -> None:
        self.x, self.y     = x, y
        self.vx = self.vy  = 0.0
        self.kb_vx = self.kb_vy = 0.0
        self.is_dead       = False
        self.damage_pct    = 0.0
        self.jumps_left    = 2

   
    #  Serialisation for networking                                        #
  

    def to_dict(self) -> dict:
        return {
            "id":          self.player_id,
            "x":           self.x,
            "y":           self.y,
            "vx":          self.vx,
            "vy":          self.vy,
            "kb_vx":       self.kb_vx,
            "kb_vy":       self.kb_vy,
            "facing":      self.facing_right,
            "damage_pct":  self.damage_pct,
            "is_dead":     self.is_dead,
            "dashing":     self.dashing,
            "anim_state":  self.anim_state,
            "anim_frame":  self.anim_frame,
            "attack_timer": self.attack_timer,
            "on_ground":   self.on_ground,
        }

    def from_dict(self, data: dict) -> None:
        """Apply a server snapshot (used for the remote player)."""
        was_on_ground = self.on_ground
        was_dashing = self.dashing
        previous_vy = self.vy
        was_attacking = self.attack_timer > 0 or self.anim_state == "attack"

        self.x            = data.get("x",            self.x)
        self.y            = data.get("y",            self.y)
        self.vx           = data.get("vx",           self.vx)
        self.vy           = data.get("vy",           self.vy)
        self.kb_vx        = data.get("kb_vx",        self.kb_vx)
        self.kb_vy        = data.get("kb_vy",        self.kb_vy)
        self.facing_right = data.get("facing",       self.facing_right)
        self.damage_pct   = data.get("damage_pct",   self.damage_pct)
        self.is_dead      = data.get("is_dead",      self.is_dead)
        self.dashing      = data.get("dashing",      self.dashing)
        self.anim_state   = data.get("anim_state",   self.anim_state)
        self.anim_frame   = data.get("anim_frame",   self.anim_frame)
        self.attack_timer = data.get("attack_timer", self.attack_timer)
        self.on_ground    = data.get("on_ground",    self.on_ground)
        self.rect.topleft = (int(self.x), int(self.y))

        is_attacking = self.attack_timer > 0 or self.anim_state == "attack"
        if not was_attacking and is_attacking and self.audio_manager and self.weapon:
            self.audio_manager.play_combat_attack_sfx(
                self.weapon.name,
                opponent=not self.is_local_player,
            )

        self._handle_remote_state_sfx(was_on_ground, was_dashing, previous_vy)

 
    #  Shared draw helpers                                                 #


    def draw(self, surface: pygame.Surface, cam_x: int = 0, cam_y: int = 0) -> None:
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


# 
# Concrete fighter subclasses  (one per weapon type)


class SwordFighter(Fighter):
    """Fast, close-range attacker. Slightly lighter."""
    WALK_SPEED = 300
    JUMP_FORCE = -650
    WEIGHT     = 0.9
    COLOR      = (100, 180, 255)

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
        self.weapon = Sword()
        self.sword_sprite_handler = SpritesheetHandler("assets/SwordSpriteSheet.png", cols=4, rows=3)
        self.sword_idle_frame = 0
        self.sword_attack_frames = [1, 2, 3, 4]
        self.sword_scale = 0.22
        self.sword_hand_offset_right = (20, 10)
        self.sword_hand_offset_left = (20, 10)

    def special_move(self, direction: int) -> None:
        """Sword swing attack."""
        if self.weapon is None:
            return
        hitboxes = self.weapon.try_attack(self.rect, self.facing_right)
        if hitboxes:
            self.anim_state = "attack"
            self.anim_frame = 0
            self.anim_timer = 0.0
            self.attack_timer = self.attack_duration


    def draw_character(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        super().draw_character(surface, cam_x, cam_y)
        self._draw_sword(surface, cam_x, cam_y)

    def _draw_sword(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
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


class BowFighter(Fighter):
    """Ranged attacker. Slower on ground but good air mobility."""
    WALK_SPEED = 250
    JUMP_FORCE = -600
    WEIGHT     = 0.85
    COLOR      = (100, 220, 130)

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


class HammerFighter(Fighter):
    """Heavy brawler. Slower but hits hard and is very hard to knock back."""
    WALK_SPEED = 220
    JUMP_FORCE = -550
    WEIGHT     = 1.4
    COLOR      = (220, 100, 100)

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
        self.weapon = Hammer()
        self.hammer_sprite_handler = SpritesheetHandler("assets/hammer_spritesheet.png", cols=4, rows=3)
        self.hammer_idle_frame = 0
        self.hammer_attack_frames = [1, 2, 3, 4, 5, 6, 7]
        self.hammer_scale = 0.26
        self.hammer_hand_offset_right = (19, 9)
        self.hammer_hand_offset_left = (18, 8)

    def special_move(self, direction: int) -> None:
        """Heavy hammer slam with wind-up then impact."""
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
        super().draw_character(surface, cam_x, cam_y)
        self._draw_hammer(surface, cam_x, cam_y)

    def _draw_hammer(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
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


# Main game loop


class Game:
    """
    Top-level game object.
    Handles the rendering loop and wires everything together.
    """

    def __init__(self, arena_id: int = 0,
                 fighter_cls_local=None,
                 fighter_cls_remote=None,
                 net: NetworkClient | None = None,
                 audio_manager: AudioManager | None = None,
                 local_player_id: int = 0):

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Gauntlet Galaxy")
        self.clock = pygame.time.Clock()

        self.tiles = build_arena(arena_id)

        # Background loading
        self.bg_image = None
        bg_filename = ARENA_MAPS.get(arena_id)
        if bg_filename:
            import os
            path = os.path.join("assets", "maps", bg_filename)
            try:
                self.bg_image = pygame.image.load(path).convert()
                self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
            except Exception as e:
                print(f"Could not load map background {path}: {e}")

        remote_player_id = 1 if local_player_id == 0 else 0
        if fighter_cls_local is None: fighter_cls_local = SwordFighter
        if fighter_cls_remote is None: fighter_cls_remote = HammerFighter

        self.audio_manager = audio_manager
        self.local_fighter = fighter_cls_local(
            300,
            400,
            player_id=local_player_id,
            audio_manager=self.audio_manager,
            is_local_player=True,
        )
        self.remote_fighter = fighter_cls_remote(
            900,
            400,
            player_id=remote_player_id,
            audio_manager=self.audio_manager,
            is_local_player=False,
        )
        
        # We need fighters ordered by player_id to render HUD correctly
        if local_player_id == 0:
            self.fighters = [self.local_fighter, self.remote_fighter]
        else:
            self.fighters = [self.remote_fighter, self.local_fighter]

        self.input_handler = InputHandler("wasd", audio_manager=self.audio_manager)
        self.hud           = HUD(self.fighters)
        self.net           = net
        self._weapon_hit_registry: dict[int, set[int]] = {}
        self.projectiles: list[tuple[Fighter, Projectile]] = []
        self.hit_effects: list[HitEffect] = []
        self.hit_stop = HitStopState()
        self.screen_shake = ScreenShakeState()

        # Background (solid color fallback if no asset)
        self.bg_color = BG_COLOR

        # Star field for background
        import random
        self.stars = [(random.randint(0, WIDTH), random.randint(0, HEIGHT),
                       random.random()) for _ in range(120)]

    async def run(self) -> None:
        """Main loop."""
        if self.audio_manager is not None:
            self.audio_manager.play_music("main_theme")

        running = True
        while running:
            # Yield control for pygbag/browser
            await asyncio.sleep(0)
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)  # cap dt to avoid tunneling

            # --- Events ---
            events = []
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                # Return to menu on Enter if game is over
                if self.hud.winner is not None and event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    running = False
                events.append(event)

            keys = pygame.key.get_pressed()
            self.hit_stop = update_hit_stop(self.hit_stop, dt)
            self.screen_shake = update_screen_shake(self.screen_shake, dt)
            stopped = is_hit_stopped(self.hit_stop)

            # --- Input ---
            if not stopped:
                self.input_handler.process(self.local_fighter, keys, events)
                self._spawn_projectiles_from_attacks(self.local_fighter,
                                                     self.local_fighter.consume_pending_attacks())

                # Physics update — only local fighter when networked
                self.local_fighter.update(dt, self.tiles)
                if not (self.net and self.net.connected):
                    # Offline mode: also run physics for remote fighter
                    self.remote_fighter.update(dt, self.tiles)
                    self._spawn_projectiles_from_attacks(self.remote_fighter,
                                                         self.remote_fighter.consume_pending_attacks())

                # --- Knockback on player collision ---
                self._check_player_collision()
                self._resolve_weapon_hits()
                self._update_and_resolve_projectiles(dt)
                self.hit_effects = update_hit_effects(self.hit_effects, dt)

                # --- Respawn & Stock Loss ---
                for fighter in self.fighters:
                    if fighter.is_dead:
                        if self.audio_manager is not None:
                            self.audio_manager.play_ko_sfx()
                        self.hud.lose_stock(fighter.player_id)
                        # Immediately stop being dead so we don't spam lose_stock
                        fighter.is_dead = False
                        
                        # Only Authority (the local owner) actually computes the respawn coords
                        if fighter is self.local_fighter or not (self.net and self.net.connected):
                            fighter.respawn(640, 200)

                # --- Update HUD timer ---
                self.hud.update(dt)

            # --- Networking ---
            if self.net and self.net.connected:
                state = self.local_fighter.to_dict()
                state["stocks"] = self.hud.stocks[self.local_fighter.player_id]
                state["hit_events"] = self.local_fighter.pending_hit_events
                self.net.send_state(state)
                # clear after sending
                self.local_fighter.pending_hit_events = []
                
                snapshot = self.net.get_opponent_state()
                if snapshot:
                    self.remote_fighter.from_dict(snapshot)
                    if "stocks" in snapshot:
                        new_stock = snapshot["stocks"]
                        if new_stock < self.hud.stocks[self.remote_fighter.player_id]:
                            self.hud.stocks[self.remote_fighter.player_id] = new_stock
                            if new_stock <= 0:
                                self.hud.set_winner(self.local_fighter.player_id)
                    if "hit_events" in snapshot:
                        for event in snapshot["hit_events"]:
                            # The remote player is telling us they hit us.
                            # We take the damage gracefully because they are the authority on their weapon connecting.
                            self.local_fighter.damage_pct += event["damage"]
                            self.local_fighter.receive_knockback(event["attacker_x"], event["kb"])
                            self.hit_effects.append(create_hit_effect(*self.local_fighter.rect.center))
                            
                            trigger_hit_stop(self.hit_stop, event.get("weapon_name", "Sword"))
                            trigger_screen_shake(self.screen_shake, event.get("weapon_name", "Sword"))
                            if self.audio_manager:
                                self.audio_manager.play_combat_hit_sfx(
                                    event.get("weapon_name", "Sword")
                                )
                # Handle opponent disconnect
                if self.net.opponent_disconnected:
                    self.hud.set_winner(self.local_fighter.player_id)

            # --- Render ---
            self._draw(dt)

        # Loop ends -> Return to menu (caller handles cleanup or restart)

    def _check_player_collision(self) -> None:
        """Simple AABB player-vs-player collision with light knockback."""
        lf = self.local_fighter
        rf = self.remote_fighter
        if lf.rect.colliderect(rf.rect):
            # Push apart
            overlap_x = (lf.rect.centerx - rf.rect.centerx)
            push = 4.0
            lf.x += push if overlap_x >= 0 else -push
            rf.x -= push if overlap_x >= 0 else -push

    def _resolve_weapon_hits(self) -> None:
        """Apply weapon hitbox damage + knockback with one hit per swing."""
        is_networked = bool(self.net and self.net.connected)
        for attacker in self.fighters:
            weapon = attacker.weapon
            if weapon is None:
                continue

            attacker_key = id(attacker)
            active_hitboxes = weapon.get_hitboxes()
            active = len(active_hitboxes) > 0

            # New swing starts when hitboxes become active again.
            if active and attacker_key not in self._weapon_hit_registry:
                self._weapon_hit_registry[attacker_key] = set()
            if not active and attacker_key in self._weapon_hit_registry:
                del self._weapon_hit_registry[attacker_key]
                continue
            if not active:
                continue

            hit_targets = self._weapon_hit_registry[attacker_key]
            for target in self.fighters:
                if target is attacker:
                    continue
                target_key = id(target)
                if target_key in hit_targets:
                    continue
                if any(hitbox.colliderect(target.rect) for hitbox in active_hitboxes):
                    if is_networked and target is self.remote_fighter:
                        # Register the hit we effectively scored on the network opponent
                        # The network opponent has absolute authority over their damage, so we must SEND this!
                        if not hasattr(self.local_fighter, "pending_hit_events"):
                            self.local_fighter.pending_hit_events = []
                            
                        self.local_fighter.pending_hit_events.append({
                            "damage": weapon.damage,
                            "kb": weapon.knockback,
                            "attacker_x": attacker.rect.centerx,
                            "weapon_name": weapon.name
                        })
                    else:
                        # Offline / AI hits processed normally
                        target.damage_pct += weapon.damage
                        target.receive_knockback(attacker.rect.centerx, weapon.knockback)
                        
                    self.hit_effects.append(create_hit_effect(*target.rect.center))
                    trigger_hit_stop(self.hit_stop, weapon.name)
                    trigger_screen_shake(self.screen_shake, weapon.name)
                    if self.audio_manager is not None:
                        self.audio_manager.play_combat_hit_sfx(weapon.name)
                    hit_targets.add(target_key)

    def _spawn_projectiles_from_attacks(self, attacker: Fighter, attacks: list[object]) -> None:
        for attack in attacks:
            if isinstance(attack, Projectile):
                self.projectiles.append((attacker, attack))

    def _update_and_resolve_projectiles(self, dt: float) -> None:
        is_networked = bool(self.net and self.net.connected)
        remaining: list[tuple[Fighter, Projectile]] = []
        for owner, projectile in self.projectiles:
            projectile.update(dt)
            if not projectile.alive:
                continue

            hit_tile = any(projectile.rect.colliderect(tile.rect) for tile in self.tiles)
            if hit_tile:
                continue

            hit_target = False
            for target in self.fighters:
                if target is owner:
                    continue
                if projectile.rect.colliderect(target.rect):
                    owner_weapon_name = owner.weapon.name if owner.weapon is not None else "Bow"
                    if is_networked and target is self.remote_fighter:
                        if not hasattr(self.local_fighter, "pending_hit_events"):
                            self.local_fighter.pending_hit_events = []
                        self.local_fighter.pending_hit_events.append({
                            "damage": projectile.damage,
                            "kb": projectile.knockback,
                            "attacker_x": owner.rect.centerx,
                            "weapon_name": owner_weapon_name
                        })
                    else:
                        target.damage_pct += projectile.damage
                        target.receive_knockback(owner.rect.centerx, projectile.knockback)
                        
                    self.hit_effects.append(create_hit_effect(*target.rect.center))
                    trigger_hit_stop(self.hit_stop, owner_weapon_name)
                    trigger_screen_shake(self.screen_shake, owner_weapon_name)
                    if self.audio_manager is not None:
                        self.audio_manager.play_combat_hit_sfx(owner_weapon_name)
                    hit_target = True
                    break

            if not hit_target:
                remaining.append((owner, projectile))

        self.projectiles = remaining

    def _draw(self, dt: float) -> None:
        shake_x, shake_y = get_screen_shake_offset(self.screen_shake)
        world_cam_x = -shake_x
        world_cam_y = -shake_y

        # Background
        if self.bg_image:
            self.screen.blit(self.bg_image, (shake_x, shake_y))
        else:
            self.screen.fill(self.bg_color)
            self._draw_stars(world_cam_x, world_cam_y)

        # Tiles (invisible collision tiles for map art)
        # for tile in self.tiles:
        #     tile.draw(self.screen)

        # Fighters
        for fighter in self.fighters:
            fighter.draw(self.screen, world_cam_x, world_cam_y)

        # Projectiles
        for _owner, projectile in self.projectiles:
            world_projectile = projectile.rect.move(shake_x, shake_y)
            pygame.draw.rect(self.screen, ORANGE, world_projectile, border_radius=2)

        # Hit effects
        draw_hit_effects(self.screen, self.hit_effects, world_cam_x, world_cam_y)

        # HUD
        self.hud.draw(self.screen)

        pygame.display.flip()

    def _draw_stars(self, cam_x: int = 0, cam_y: int = 0) -> None:
        for sx, sy, brightness in self.stars:
            radius = 1 if brightness < 0.5 else 2
            alpha  = int(brightness * 200)
            color  = (alpha, alpha, alpha)
            pygame.draw.circle(self.screen, color, (sx - cam_x, sy - cam_y), radius)



# Entry point


def main() -> None:
    pygame.init()
    audio_manager = get_shared_audio_manager()
    audio_manager.initialize()
    audio_manager.preload()

    # Attempt to connect to server (optional — game runs offline too)
    net = NetworkClient(host="localhost", port=5555)
    connected = net.connect()
    if not connected:
        print("[client] No server found — running in local/offline mode.")
        net = None

    # TODO: replace with actual character-select result from startmenu.py
    arena_id         = 0
    fighter_cls_local  = SwordFighter
    fighter_cls_remote = HammerFighter

    game = Game(
        arena_id=arena_id,
        fighter_cls_local=fighter_cls_local,
        fighter_cls_remote=fighter_cls_remote,
        net=net,
        audio_manager=audio_manager,
    )
    game.run()


if __name__ == "__main__":
    main()
