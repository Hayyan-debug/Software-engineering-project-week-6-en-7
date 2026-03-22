"""Core match loop orchestration: input, simulation, networking, and rendering."""

import asyncio

import pygame

from src.audio import AudioManager
from src.combat.projectile import Projectile
from src.entities.fighter import Fighter
from src.entities.hammer_fighter import HammerFighter
from src.entities.sword_fighter import SwordFighter
from src.effects.effects import (
    HitEffect,
    Particle,
    create_hit_effect,
    create_hit_particles,
    draw_hit_effects,
    draw_particles,
    update_hit_effects,
    update_particles,
)
from src.effects.hitstop import HitStopState, is_hit_stopped, trigger_hit_stop, update_hit_stop
from src.effects.screenshake import ScreenShakeState, get_screen_shake_offset, trigger_screen_shake, update_screen_shake
from src.game.arena import build_arena
from src.game.hud import HUD
from src.game.input import InputHandler
from src.network.network_client import NetworkClient


WIDTH, HEIGHT = 1280, 720
FPS = 60

ARENA_MAPS = {
    0: "map_aethercleft.png",
    1: "map_nebulashards.png",
    2: "map_chronosgears.png",
    3: "map_gravitywell.png",
    4: "map_cometcauseway.png",
    5: "map_voidvortex.png",
}

ORANGE = (255, 180, 80)
BG_COLOR = (20, 20, 35)
COMBO_TIMEOUT = 0.8
COMBO_BONUS_PER_HIT = 0.10
COMBO_MAX_BONUS = 0.50
COMBO_POPUP_DURATION = 0.5
COMBO_POPUP_RISE_SPEED = 45.0


class Game:
    """
    Top-level game object.
    Handles the rendering loop and wires everything together.
    """

    def __init__(
        self,
        arena_id: int = 0,
        fighter_cls_local=None,
        fighter_cls_remote=None,
        net: NetworkClient | None = None,
        audio_manager: AudioManager | None = None,
        local_player_id: int = 0,
    ):
        """Set up arena, fighters, HUD, effects, and optional network state."""
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
        if fighter_cls_local is None:
            fighter_cls_local = SwordFighter
        if fighter_cls_remote is None:
            fighter_cls_remote = HammerFighter

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
        self.hud = HUD(self.fighters)
        self.net = net
        self._weapon_hit_registry: dict[int, set[int]] = {}
        self.projectiles: list[tuple[Fighter, Projectile]] = []
        self.hit_effects: list[HitEffect] = []
        self.particles: list[Particle] = []
        self.hit_stop = HitStopState()
        self.screen_shake = ScreenShakeState()
        self.combo_state: dict[int, dict[str, float | int | bool]] = {}
        self.combo_popups: list[dict[str, float | str]] = []
        if not pygame.font.get_init():
            pygame.font.init()
        self.combo_font = pygame.font.SysFont("impact", 34)

        # Background (solid color fallback if no asset)
        self.bg_color = BG_COLOR

        # Star field for background
        import random

        self.stars = [
            (random.randint(0, WIDTH), random.randint(0, HEIGHT), random.random()) for _ in range(120)
        ]

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
            self._update_combo_state(dt)
            self._update_combo_popups(dt)
            stopped = is_hit_stopped(self.hit_stop)

            # --- Input ---
            if not stopped:
                self.input_handler.process(self.local_fighter, keys, events)
                self._spawn_projectiles_from_attacks(
                    self.local_fighter,
                    self.local_fighter.consume_pending_attacks(),
                )

                # Physics update — only local fighter when networked
                self.local_fighter.update(dt, self.tiles)
                if not (self.net and self.net.connected):
                    # Offline mode: also run physics for remote fighter
                    self.remote_fighter.update(dt, self.tiles)
                    self._spawn_projectiles_from_attacks(
                        self.remote_fighter,
                        self.remote_fighter.consume_pending_attacks(),
                    )

                # --- Knockback on player collision ---
                self._check_player_collision()
                self._resolve_weapon_hits()
                self._update_and_resolve_projectiles(dt)
                self.hit_effects = update_hit_effects(self.hit_effects, dt)
                self.particles = update_particles(self.particles, dt)

                # --- Respawn & Stock Loss ---
                for fighter in self.fighters:
                    if fighter.is_dead:
                        self._break_combo(fighter)
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
                            if self.local_fighter.shielding:
                                self.particles.extend(
                                    create_hit_particles(
                                        self.local_fighter.rect.centerx,
                                        self.local_fighter.rect.centery,
                                        event.get("weapon_name", "Sword"),
                                        combo_count=int(event.get("combo_count", 1)),
                                        blocked=True,
                                    )
                                )
                                self._break_combo(self.remote_fighter)
                                continue
                            self.local_fighter.damage_pct += event["damage"]
                            self.local_fighter.receive_knockback(event["attacker_x"], event["kb"])
                            self._break_combo(self.local_fighter)
                            self._record_combo_popup(
                                self.local_fighter.rect.centerx,
                                self.local_fighter.rect.top,
                                int(event.get("combo_count", 1)),
                            )
                            self.hit_effects.append(create_hit_effect(*self.local_fighter.rect.center))
                            self.particles.extend(
                                create_hit_particles(
                                    self.local_fighter.rect.centerx,
                                    self.local_fighter.rect.centery,
                                    event.get("weapon_name", "Sword"),
                                    combo_count=int(event.get("combo_count", 1)),
                                    blocked=False,
                                )
                            )

                            trigger_hit_stop(
                                self.hit_stop,
                                event.get("weapon_name", "Sword"),
                                combo_count=int(event.get("combo_count", 1)),
                            )
                            trigger_screen_shake(self.screen_shake, event.get("weapon_name", "Sword"))
                            if self.audio_manager:
                                self.audio_manager.play_combat_hit_sfx(event.get("weapon_name", "Sword"))
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
            overlap_x = lf.rect.centerx - rf.rect.centerx
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
                    blocked = target.shielding
                    hit_combo_count = 1
                    if blocked:
                        self._break_combo(attacker)
                    else:
                        combo_count, combo_mult = self._advance_combo(attacker)
                        hit_combo_count = combo_count
                        scaled_damage = weapon.damage * combo_mult
                        scaled_knockback = weapon.knockback * combo_mult
                        self._break_combo(target)
                        self._record_combo_popup(target.rect.centerx, target.rect.top, combo_count)

                    if not blocked and is_networked and target is self.remote_fighter:
                        # Register the hit we effectively scored on the network opponent
                        # The network opponent has absolute authority over their damage, so we must SEND this!
                        if not hasattr(self.local_fighter, "pending_hit_events"):
                            self.local_fighter.pending_hit_events = []

                        self.local_fighter.pending_hit_events.append(
                            {
                                "damage": scaled_damage,
                                "kb": scaled_knockback,
                                "attacker_x": attacker.rect.centerx,
                                "weapon_name": weapon.name,
                                "combo_count": combo_count,
                                "combo_mult": combo_mult,
                            }
                        )
                    elif not blocked:
                        # Offline / AI hits processed normally
                        target.damage_pct += scaled_damage
                        target.receive_knockback(attacker.rect.centerx, scaled_knockback)

                    self.hit_effects.append(create_hit_effect(*target.rect.center))
                    self.particles.extend(
                        create_hit_particles(
                            target.rect.centerx,
                            target.rect.centery,
                            weapon.name,
                            combo_count=hit_combo_count,
                            blocked=blocked,
                        )
                    )
                    trigger_hit_stop(self.hit_stop, weapon.name, combo_count=hit_combo_count)
                    trigger_screen_shake(self.screen_shake, weapon.name)
                    if self.audio_manager is not None:
                        self.audio_manager.play_combat_hit_sfx(weapon.name)
                    hit_targets.add(target_key)

    def _spawn_projectiles_from_attacks(self, attacker: Fighter, attacks: list[object]) -> None:
        """Collect projectile attacks emitted by a fighter this frame."""
        for attack in attacks:
            if isinstance(attack, Projectile):
                self.projectiles.append((attacker, attack))

    def _update_and_resolve_projectiles(self, dt: float) -> None:
        """Update projectiles and resolve tile/fighter collisions."""
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
                    blocked = target.shielding
                    hit_combo_count = 1
                    if blocked:
                        self._break_combo(owner)
                    else:
                        combo_count, combo_mult = self._advance_combo(owner)
                        hit_combo_count = combo_count
                        scaled_damage = projectile.damage * combo_mult
                        scaled_knockback = projectile.knockback * combo_mult
                        self._break_combo(target)
                        self._record_combo_popup(target.rect.centerx, target.rect.top, combo_count)

                    if not blocked and is_networked and target is self.remote_fighter:
                        if not hasattr(self.local_fighter, "pending_hit_events"):
                            self.local_fighter.pending_hit_events = []
                        self.local_fighter.pending_hit_events.append(
                            {
                                "damage": scaled_damage,
                                "kb": scaled_knockback,
                                "attacker_x": owner.rect.centerx,
                                "weapon_name": owner_weapon_name,
                                "combo_count": combo_count,
                                "combo_mult": combo_mult,
                            }
                        )
                    elif not blocked:
                        target.damage_pct += scaled_damage
                        target.receive_knockback(owner.rect.centerx, scaled_knockback)

                    self.hit_effects.append(create_hit_effect(*target.rect.center))
                    self.particles.extend(
                        create_hit_particles(
                            target.rect.centerx,
                            target.rect.centery,
                            owner_weapon_name,
                            combo_count=hit_combo_count,
                            blocked=blocked,
                        )
                    )
                    trigger_hit_stop(self.hit_stop, owner_weapon_name, combo_count=hit_combo_count)
                    trigger_screen_shake(self.screen_shake, owner_weapon_name)
                    if self.audio_manager is not None:
                        self.audio_manager.play_combat_hit_sfx(owner_weapon_name)
                    hit_target = True
                    break

            if not hit_target:
                remaining.append((owner, projectile))

        self.projectiles = remaining

    def _draw(self, dt: float) -> None:
        """Render the full frame: world, VFX, popups, and HUD."""
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
        draw_particles(self.screen, self.particles, world_cam_x, world_cam_y)
        self._draw_combo_popups(self.screen, world_cam_x, world_cam_y)

        # HUD
        self.hud.draw(self.screen)

        pygame.display.flip()

    def _draw_stars(self, cam_x: int = 0, cam_y: int = 0) -> None:
        """Draw background stars for the solid-color fallback scene."""
        for sx, sy, brightness in self.stars:
            radius = 1 if brightness < 0.5 else 2
            alpha = int(brightness * 200)
            color = (alpha, alpha, alpha)
            pygame.draw.circle(self.screen, color, (sx - cam_x, sy - cam_y), radius)

    def _combo_entry(self, fighter: Fighter) -> dict[str, float | int | bool]:
        """Return or create combo tracking state for a fighter."""
        key = id(fighter)
        if key not in self.combo_state:
            self.combo_state[key] = {"count": 0, "active": False, "time_left": 0.0}
        return self.combo_state[key]

    def _combo_multiplier(self, combo_count: int) -> float:
        """Compute damage/knockback multiplier from combo count."""
        bonus = min(COMBO_MAX_BONUS, max(0, combo_count - 1) * COMBO_BONUS_PER_HIT)
        return 1.0 + bonus

    def _advance_combo(self, attacker: Fighter) -> tuple[int, float]:
        """Advance attacker combo state and return count plus multiplier."""
        entry = self._combo_entry(attacker)
        if bool(entry["active"]) and float(entry["time_left"]) > 0:
            entry["count"] = int(entry["count"]) + 1
        else:
            entry["count"] = 1
        entry["active"] = True
        entry["time_left"] = COMBO_TIMEOUT
        combo_count = int(entry["count"])
        return combo_count, self._combo_multiplier(combo_count)

    def _break_combo(self, fighter: Fighter) -> None:
        """Reset combo state for a fighter."""
        entry = self._combo_entry(fighter)
        entry["count"] = 0
        entry["active"] = False
        entry["time_left"] = 0.0

    def _update_combo_state(self, dt: float) -> None:
        """Tick combo timers and expire inactive combo chains."""
        for entry in self.combo_state.values():
            if not bool(entry["active"]):
                continue
            entry["time_left"] = max(0.0, float(entry["time_left"]) - dt)
            if float(entry["time_left"]) <= 0.0:
                entry["count"] = 0
                entry["active"] = False

    def _record_combo_popup(self, x: int, y: int, combo_count: int) -> None:
        """Create a floating combo popup for multi-hit sequences."""
        if combo_count < 2:
            return
        self.combo_popups.append(
            {
                "x": float(x),
                "y": float(y),
                "time_left": COMBO_POPUP_DURATION,
                "duration": COMBO_POPUP_DURATION,
                "text": f"{combo_count} HIT!",
            }
        )
        if self.audio_manager is not None:
            self.audio_manager.play_combo_sfx()

    def _update_combo_popups(self, dt: float) -> None:
        """Move and expire active combo popups over time."""
        remaining: list[dict[str, float | str]] = []
        for popup in self.combo_popups:
            time_left = max(0.0, float(popup["time_left"]) - dt)
            if time_left <= 0.0:
                continue
            popup["time_left"] = time_left
            popup["y"] = float(popup["y"]) - (COMBO_POPUP_RISE_SPEED * dt)
            remaining.append(popup)
        self.combo_popups = remaining

    def _draw_combo_popups(self, surface: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """Draw active combo popups with fade-out alpha."""
        for popup in self.combo_popups:
            text = str(popup["text"])
            surf = self.combo_font.render(text, True, (255, 235, 120))
            alpha_ratio = float(popup["time_left"]) / max(float(popup["duration"]), 0.001)
            surf.set_alpha(int(255 * alpha_ratio))
            draw_x = int(float(popup["x"])) - cam_x - (surf.get_width() // 2)
            draw_y = int(float(popup["y"])) - cam_y - surf.get_height()
            surface.blit(surf, (draw_x, draw_y))
