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
import asyncio

from src.audio import AudioManager, get_shared_audio_manager
from src.combat.bow import Bow
from src.combat.hammer import Hammer
from src.combat.projectile import Projectile
from src.combat.sword import Sword
from src.entities.fighter import Fighter
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

# Colors (fallback if assets missing)
ORANGE     = (255, 180, 80 )
BG_COLOR   = (20,  20,  35 )

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
