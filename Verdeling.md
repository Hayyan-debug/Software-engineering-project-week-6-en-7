Person A handles server and netcode, Person B focuses on gameplay physics, Person C builds UI and menus, while Person D manages assets and combat effects. This enables parallel development with clear handoffs; use Git for shared code like Player.py.

## Person A: Server & Netcode (Hayyan)
- Server.py: Socket server, client auth (up to 4 players), game loop (inputs -> updates -> broadcast JSON states).
- Network Stability: Handling latency, heartbeat, and reconnection logic.

## Person B: Gameplay & Physics (Finn)
- Client.py basics: Input capture, local prediction, rendering loop.
- Mechanics: Movement (jump, dash, movement physics), collisions with tiles and players.
- Platforming: Gravity logic, wall jumping (if applicable), and arena interaction.

## Person C: UI, Menus & HUD (Thijs)
- Menus: Weapon select, arena vote screens (buttons, nav, visuals), Start Menu updates.
- HUD: Health bars, timers, score tracking, and winner banners.
- UX: Screen transitions and navigational flow.

## Person D: Assets, Combat & SFX (New Member)
- Assets: Sprite animations for players and weapons; Arena background layers.
- Combat VFX: Particle effects for hits, explosions, and special attacks.
- Audio: SFX for actions (jump, attack, hit) and background music implementation.
- Combat Logic: Weapon hitboxes, projectile math, and damage/knockback resolution.

## Shared & Integration
| Task | Who Leads | Notes |
|------|-----------|-------|
| Shared models (Player, Weapon, JSON protocols) | Person A | Define early; test formats. |
| Testing (local net, bots) | All | Weekly merges; localhost first.  |
| Polish (lag fix, sync) | Person A/B | Debug desync.  |
| Full integration | Person B | Run end-to-end flow. |

Sync daily on GitHub; Person B coordinates client-server links.