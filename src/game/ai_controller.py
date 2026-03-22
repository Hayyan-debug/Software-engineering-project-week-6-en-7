"""Basic enemy AI controller for offline solo matches."""

from __future__ import annotations

import random

from src.entities.fighter import Fighter


CHASE_DISTANCE = 260
MELEE_ATTACK_DISTANCE = 95
RANGED_ATTACK_DISTANCE = 320
ATTACK_VERTICAL_TOLERANCE = 95
JUMP_VERTICAL_GAP = 65
JUMP_COOLDOWN = 0.9
DASH_COOLDOWN = 1.2
SHIELD_COOLDOWN = 1.0
SHIELD_DURATION = 0.22
ATTACK_REACTION_TIME = 0.16
ATTACK_REACTION_JITTER = 0.09
STUCK_X_EPSILON = 2.0
STUCK_TIMEOUT = 0.65
RETREAT_DISTANCE = 140


class EnemyAIController:
    """Simple aggressive chaser AI with minimal anti-stuck behavior."""

    def __init__(self) -> None:
        self.rng = random.Random()
        self.attack_timer = 0.0
        self.jump_timer = 0.0
        self.dash_timer = 0.0
        self.shield_timer = 0.0
        self.shield_cooldown_timer = 0.0
        self.stuck_timer = 0.0
        self._last_x: float | None = None
        self._strafe_dir = 1

    def update(self, controlled_fighter: Fighter, target_fighter: Fighter, dt: float, tiles: list[object]) -> None:
        """Apply one frame of AI actions to the controlled fighter."""
        _ = tiles  # Reserved for future map-aware behavior.

        if controlled_fighter.is_dead:
            return

        self._tick_timers(dt)

        dx = target_fighter.rect.centerx - controlled_fighter.rect.centerx
        dy = target_fighter.rect.centery - controlled_fighter.rect.centery
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        direction_to_target = 1 if dx >= 0 else -1
        is_ranged = bool(controlled_fighter.weapon and controlled_fighter.weapon.name == "Bow")
        attack_distance = RANGED_ATTACK_DISTANCE if is_ranged else MELEE_ATTACK_DISTANCE

        # Release shield when the brief defensive window ends.
        if self.shield_timer <= 0.0 and controlled_fighter.shielding:
            controlled_fighter.set_shielding(False)

        self._update_stuck_tracking(controlled_fighter, dt)
        self._try_jump(controlled_fighter, target_fighter, direction_to_target, abs_dy)
        self._try_dash(controlled_fighter, direction_to_target, abs_dx, attack_distance)
        self._try_shield(controlled_fighter, target_fighter, abs_dx, abs_dy, attack_distance)

        move_direction = self._movement_direction(
            controlled_fighter=controlled_fighter,
            direction_to_target=direction_to_target,
            abs_dx=abs_dx,
            is_ranged=is_ranged,
            attack_distance=attack_distance,
        )
        controlled_fighter.move(move_direction)

        # Ensure the AI faces the target before attacks.
        if abs_dx > 5:
            controlled_fighter.facing_right = direction_to_target > 0

        self._try_attack(controlled_fighter, abs_dx, abs_dy)

    def _tick_timers(self, dt: float) -> None:
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.jump_timer = max(0.0, self.jump_timer - dt)
        self.dash_timer = max(0.0, self.dash_timer - dt)
        self.shield_timer = max(0.0, self.shield_timer - dt)
        self.shield_cooldown_timer = max(0.0, self.shield_cooldown_timer - dt)

    def _update_stuck_tracking(self, controlled_fighter: Fighter, dt: float) -> None:
        if self._last_x is None:
            self._last_x = controlled_fighter.x
            return
        if (
            abs(controlled_fighter.x - self._last_x) <= STUCK_X_EPSILON
            and abs(controlled_fighter.kb_vx) < 15
            and not controlled_fighter.dashing
        ):
            self.stuck_timer += dt
        else:
            self.stuck_timer = 0.0
        self._last_x = controlled_fighter.x

    def _try_jump(
        self,
        controlled_fighter: Fighter,
        target_fighter: Fighter,
        direction_to_target: int,
        abs_dy: float,
    ) -> None:
        if self.jump_timer > 0 or controlled_fighter.shielding:
            return
        if controlled_fighter.on_ground and target_fighter.rect.centery < controlled_fighter.rect.centery - JUMP_VERTICAL_GAP:
            controlled_fighter.jump()
            self.jump_timer = JUMP_COOLDOWN
            return
        if self.stuck_timer >= STUCK_TIMEOUT:
            controlled_fighter.move(direction_to_target)
            controlled_fighter.jump()
            self.jump_timer = JUMP_COOLDOWN
            self.stuck_timer = 0.0
            return
        if not controlled_fighter.on_ground and abs_dy < 24 and self.rng.random() < 0.01:
            controlled_fighter.jump()
            self.jump_timer = JUMP_COOLDOWN

    def _try_dash(
        self,
        controlled_fighter: Fighter,
        direction_to_target: int,
        abs_dx: float,
        attack_distance: float,
    ) -> None:
        if self.dash_timer > 0 or controlled_fighter.shielding:
            return
        if not controlled_fighter.on_ground:
            return
        if controlled_fighter.dash_cooldown > 0 or controlled_fighter.dashing:
            return
        if attack_distance + 40 < abs_dx < CHASE_DISTANCE + 120:
            controlled_fighter.dash(direction_to_target)
            self.dash_timer = DASH_COOLDOWN

    def _try_shield(
        self,
        controlled_fighter: Fighter,
        target_fighter: Fighter,
        abs_dx: float,
        abs_dy: float,
        attack_distance: float,
    ) -> None:
        if self.shield_timer > 0:
            controlled_fighter.set_shielding(True)
            return
        if self.shield_cooldown_timer > 0:
            return
        if not controlled_fighter.on_ground:
            return
        if target_fighter.attack_timer <= 0:
            return
        close_enough = abs_dx <= max(70.0, attack_distance * 0.75)
        if close_enough and abs_dy <= ATTACK_VERTICAL_TOLERANCE:
            controlled_fighter.set_shielding(True)
            self.shield_timer = SHIELD_DURATION
            self.shield_cooldown_timer = SHIELD_COOLDOWN

    def _movement_direction(
        self,
        controlled_fighter: Fighter,
        direction_to_target: int,
        abs_dx: float,
        is_ranged: bool,
        attack_distance: float,
    ) -> int:
        if controlled_fighter.shielding:
            return 0
        if abs_dx > CHASE_DISTANCE:
            return direction_to_target
        if abs_dx > attack_distance:
            return direction_to_target
        if is_ranged and abs_dx < RETREAT_DISTANCE:
            return -direction_to_target
        if self.rng.random() < 0.02:
            self._strafe_dir *= -1
        return self._strafe_dir

    def _try_attack(self, controlled_fighter: Fighter, abs_dx: float, abs_dy: float) -> None:
        if controlled_fighter.shielding:
            return
        if controlled_fighter.weapon is None:
            return
        if self.attack_timer > 0:
            return
        if not controlled_fighter.weapon.can_attack():
            return

        is_ranged = controlled_fighter.weapon.name == "Bow"
        attack_distance = RANGED_ATTACK_DISTANCE if is_ranged else MELEE_ATTACK_DISTANCE
        if abs_dx > attack_distance or abs_dy > ATTACK_VERTICAL_TOLERANCE:
            return

        controlled_fighter.special_move(1 if controlled_fighter.facing_right else -1)
        self.attack_timer = ATTACK_REACTION_TIME + self.rng.uniform(0.0, ATTACK_REACTION_JITTER)
