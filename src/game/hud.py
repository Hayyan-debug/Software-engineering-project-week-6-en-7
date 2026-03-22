import math

import pygame


KO_PERCENTAGE = 120
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 60, 60)
GREEN = (80, 200, 80)
ORANGE = (255, 180, 80)
YELLOW = (255, 230, 100)


class HUD:
    """
    Enhanced HUD with health bars, timer, stocks, and winner banners.
    Includes character portraits from the spritesheets.
    """

    PLAYER_COLORS = [(120, 180, 255), (100, 220, 130), (220, 100, 100)]
    PLAYER_NAMES = ["LUNA", "RAVEN", "TITAN"]

    def __init__(self, fighters: list["Fighter"], match_time: float = 120.0):
        self.fighters = fighters
        self.match_timer = match_time
        self.stocks = [3 for _ in fighters]
        self.winner = None
        self.winner_timer = 0.0
        self.arena_name = "AETHER CLEFT"
        self.time_acc = 0.0

        # Pre-render fonts
        pygame.font.init()
        self.font_timer = pygame.font.SysFont("impact", 48)
        self.font_label = pygame.font.SysFont("impact", 22)
        self.font_tiny = pygame.font.SysFont("impact", 18)
        self.font_winner = pygame.font.SysFont("impact", 86)

    def update(self, dt: float) -> None:
        self.time_acc += dt
        if self.match_timer > 0 and self.winner is None:
            self.match_timer -= dt
        if self.winner is not None:
            self.winner_timer += dt

    def set_winner(self, player_index: int) -> None:
        self.winner = player_index
        self.winner_timer = 0.0

    def lose_stock(self, player_index: int) -> None:
        if player_index < len(self.stocks):
            self.stocks[player_index] = max(0, self.stocks[player_index] - 1)
            if self.stocks[player_index] <= 0:
                # The OTHER player wins
                winner = 1 - player_index if len(self.fighters) == 2 else 0
                self.set_winner(winner)

    def draw(self, surface: pygame.Surface) -> None:
        width, _ = surface.get_size()
        self._draw_player_panel(surface, 0, width, left=True)
        if len(self.fighters) > 1:
            self._draw_player_panel(surface, 1, width, left=False)
        self._draw_timer(surface, width)
        self._draw_stocks(surface, width)
        self._draw_arena_banner(surface, width)
        if self.winner is not None:
            self._draw_winner_overlay(surface, width)

    def _draw_outlined(
        self,
        surface,
        text,
        font,
        color,
        x,
        y,
        outline=BLACK,
        ow=2,
        anchor="center",
    ):
        """Helper to draw outlined text."""
        outline_s = font.render(text, True, outline)
        text_s = font.render(text, True, color)
        for ox in range(-ow, ow + 1):
            for oy in range(-ow, ow + 1):
                if ox == 0 and oy == 0:
                    continue
                if anchor == "center":
                    r = outline_s.get_rect(center=(x + ox, y + oy))
                elif anchor == "midleft":
                    r = outline_s.get_rect(midleft=(x + ox, y + oy))
                else:
                    r = outline_s.get_rect(topleft=(x + ox, y + oy))
                surface.blit(outline_s, r)
        if anchor == "center":
            r = text_s.get_rect(center=(x, y))
        elif anchor == "midleft":
            r = text_s.get_rect(midleft=(x, y))
        else:
            r = text_s.get_rect(topleft=(x, y))
        surface.blit(text_s, r)

    def _draw_player_panel(self, surface, idx, width, left=True):
        """Draw an individual player's top HUD panel."""
        f = self.fighters[idx] if idx < len(self.fighters) else None
        if f is None:
            return

        panel_w, panel_h = 320, 80
        margin = 20
        px = margin if left else width - panel_w - margin
        py = 15

        # Panel bg
        s = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        s.fill((10, 15, 30, 200))
        surface.blit(s, (px, py))
        border_c = self.PLAYER_COLORS[idx % len(self.PLAYER_COLORS)]
        pygame.draw.rect(surface, (60, 70, 90), (px, py, panel_w, panel_h), 2, border_radius=4)

        # Portrait
        ps = 56
        port_x = px + 8 if left else px + panel_w - ps - 8
        port_y = py + (panel_h - ps) // 2
        pygame.draw.rect(surface, (20, 25, 40), (port_x, port_y, ps, ps), border_radius=6)
        pygame.draw.rect(surface, border_c, (port_x, port_y, ps, ps), 2, border_radius=6)

        # Draw character face from spritesheet (frame 0 is idle)
        portrait = f.sprite_handler.get_frame(0)
        # Crop head slightly if possible, or just scale the whole thing down
        sf = min(ps / f.sprite_handler.frame_w, ps / f.sprite_handler.frame_h) * 1.5
        portrait = pygame.transform.scale(
            portrait,
            (int(f.sprite_handler.frame_w * sf), int(f.sprite_handler.frame_h * sf)),
        )
        if not f.facing_right and left:  # Flip for the left panel if character faces right by default
            portrait = pygame.transform.flip(portrait, True, False)

        # Center in portrait box
        ix = port_x + ps // 2 - portrait.get_width() // 2
        iy = port_y + ps // 2 - portrait.get_height() // 2
        surface.blit(portrait, (ix, iy), special_flags=pygame.BLEND_ALPHA_SDL2)

        # Name
        name = self.PLAYER_NAMES[idx % len(self.PLAYER_NAMES)]
        name_x = port_x + ps + 12 if left else px + 10
        self._draw_outlined(surface, name, self.font_label, WHITE, name_x, py + 18, anchor="midleft")

        # Health bar
        bar_w, bar_h = 180, 18
        bar_x = port_x + ps + 12 if left else px + 10
        bar_y = py + 42

        pygame.draw.rect(surface, (30, 30, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=3)

        pct = f.damage_pct
        fill_ratio = max(0, 1.0 - pct / 150.0)
        bar_c = GREEN if pct < 40 else YELLOW if pct < 80 else ORANGE if pct < KO_PERCENTAGE else RED

        fill_w = int(bar_w * fill_ratio)
        if fill_w > 0:
            pygame.draw.rect(surface, bar_c, (bar_x, bar_y, fill_w, bar_h), border_radius=3)
        pygame.draw.rect(surface, (100, 110, 130), (bar_x, bar_y, bar_w, bar_h), 2, border_radius=3)

        # Percentage text
        pct_color = WHITE if pct < 60 else (ORANGE if pct < KO_PERCENTAGE else RED)
        self._draw_outlined(
            surface,
            f"{int(pct)}%",
            self.font_label,
            pct_color,
            bar_x + bar_w + 22,
            bar_y + bar_h // 2,
        )

    def _draw_timer(self, surface, width):
        minutes = int(self.match_timer) // 60
        seconds = int(self.match_timer) % 60
        t_text = f"{minutes}:{seconds:02d}"
        color = WHITE
        if self.match_timer < 30:
            pulse = math.sin(self.time_acc * 6) * 0.5 + 0.5
            color = (255, int(100 + pulse * 100), int(pulse * 80))
        ts = self.font_timer.render(t_text, True, color)
        surface.blit(ts, ts.get_rect(center=(width // 2, 48)))

    def _draw_stocks(self, surface, width):
        s1 = self.stocks[0] if len(self.stocks) > 0 else 0
        s2 = self.stocks[1] if len(self.stocks) > 1 else 0
        self._draw_outlined(surface, f"STOCKS: {s1} vs {s2}", self.font_tiny, (153, 230, 255), width // 2, 90)

    def _draw_arena_banner(self, surface, width):
        bw, bh = 300, 34
        _, height = surface.get_size()
        bx, by = width // 2 - bw // 2, height - 38
        s = pygame.Surface((bw, bh), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        surface.blit(s, (bx, by))
        pygame.draw.rect(surface, (80, 90, 110), (bx, by, bw, bh), 2, border_radius=4)
        self._draw_outlined(surface, self.arena_name, self.font_tiny, (153, 230, 255), width // 2, by + bh // 2)

    def _draw_winner_overlay(self, surface, width):
        _, height = surface.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))
        name = self.PLAYER_NAMES[self.winner % len(self.PLAYER_NAMES)]
        self._draw_outlined(surface, f"{name} WINS!", self.font_winner, YELLOW, width // 2, height // 2 - 30)
        self._draw_outlined(
            surface,
            "PRESS ENTER TO CONTINUE",
            self.font_label,
            WHITE,
            width // 2,
            height // 2 + 50,
        )
