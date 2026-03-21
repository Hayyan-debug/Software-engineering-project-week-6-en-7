"""
startmenu.py - Gauntlet Galaxy
UI, Menus & HUD module (Person C: Thijs)

Responsibilities:
- Start Menu with button navigation
- Matchmaking / Looking-for-teammate screen
- Weapon Select screen (3 weapons per player)
- Arena Vote screen (6 arenas to choose from)
- Screen transitions & navigational flow
"""

import pygame
import sys
import math
import os
import asyncio

from src.audio import get_shared_audio_manager

# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 1280, 720
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (150, 150, 150)
DARK_GRAY = (50, 50, 50)
LIGHT_BLUE = (153, 230, 255)
BLUE_BORDER = (50, 150, 200)
ORANGE = (255, 180, 80)
ORANGE_BORDER = (200, 100, 20)
YELLOW = (255, 230, 100)
RED = (220, 60, 60)
GREEN = (80, 200, 80)
CYAN = (0, 220, 255)
BG_COLOR = (20, 20, 35)
PANEL_BG = (10, 15, 30, 200)
SELECTED_GLOW = (0, 180, 255)
CONFIRM_GREEN = (40, 200, 100)
CONFIRM_GREEN_BORDER = (20, 150, 60)

# Setup screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Gauntlet Galaxy")
clock = pygame.time.Clock()

audio_manager = get_shared_audio_manager()
audio_manager.initialize()
audio_manager.preload()


def play_ui_sfx(name: str) -> None:
    audio_manager.play_sfx(name)


# ── Asset loading ──────────────────────────────────────────────────────────

def load_image(filename, size=None):
    path = os.path.join("assets", filename)
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            return pygame.transform.scale(img, size)
        return pygame.transform.scale(img, (WIDTH, HEIGHT))
    except Exception as e:
        print(f"Could not load {path}: {e}")
        surf = pygame.Surface(size or (WIDTH, HEIGHT), pygame.SRCALPHA)
        if "platforms" not in filename:
            surf.fill(BG_COLOR)
        return surf


# Load map data for battle lobby
chronos_bg = load_image("chronoscleftsmap.png")

# Load animated background frames
anim_background_frames = []
anim_frame_dir = os.path.join("assets", "anim_frames")
if os.path.exists(anim_frame_dir):
    frame_files = sorted([f for f in os.listdir(anim_frame_dir) if f.startswith("frame_") and f.endswith(".png")])
    for f in frame_files:
        try:
            full_path = os.path.join(anim_frame_dir, f)
            frame_img = pygame.image.load(full_path).convert()
            frame_img = pygame.transform.scale(frame_img, (WIDTH, HEIGHT))
            anim_background_frames.append(frame_img)
        except Exception as e:
            print(f"Could not load animation frame {f}: {e}")
if not anim_background_frames:
    # Use static fallback if frames folder is empty
    fallback = load_image("animbackground.png").convert()
    anim_background_frames = [fallback]



# Spritesheets for portraits
try:
    luna_sheet = pygame.image.load(os.path.join("assets", "spritesheet_luna.png")).convert_alpha()
    raven_sheet = pygame.image.load(os.path.join("assets", "spritesheet_raven.png")).convert_alpha()
    # Extract first frame (idle) for portraits
    luna_portrait = luna_sheet.subsurface(pygame.Rect(0, 0, luna_sheet.get_width() // 6, luna_sheet.get_height() // 3))
    raven_portrait = raven_sheet.subsurface(pygame.Rect(0, 0, raven_sheet.get_width() // 6, raven_sheet.get_height() // 3))
    luna_portrait = pygame.transform.scale(luna_portrait, (110, 110))
    raven_portrait = pygame.transform.scale(raven_portrait, (110, 110))
except Exception as e:
    print(f"Could not load spritesheets in startmenu: {e}")
    luna_portrait = None
    raven_portrait = None


# Fonts
try:
    font_title_large = pygame.font.SysFont("impact", 130)
    font_title_small = pygame.font.SysFont("impact", 110)
    font_header = pygame.font.SysFont("impact", 48)
    font_subheader = pygame.font.SysFont("impact", 36)
    font_prompt = pygame.font.SysFont("impact", 45)
    font_button = pygame.font.SysFont("impact", 35)
    font_label = pygame.font.SysFont("impact", 28)
    font_small = pygame.font.SysFont("consolas", 20, bold=True)
    font_tiny = pygame.font.SysFont("consolas", 16, bold=True)
    font_hud_big = pygame.font.SysFont("impact", 60)
    font_hud_med = pygame.font.SysFont("impact", 38)
    font_hud_timer = pygame.font.SysFont("impact", 80)
    font_winner = pygame.font.SysFont("impact", 90)
except Exception:
    font_title_large = pygame.font.Font(None, 140)
    font_title_small = pygame.font.Font(None, 120)
    font_header = pygame.font.Font(None, 52)
    font_subheader = pygame.font.Font(None, 40)
    font_prompt = pygame.font.Font(None, 50)
    font_button = pygame.font.Font(None, 40)
    font_label = pygame.font.Font(None, 32)
    font_small = pygame.font.Font(None, 24)
    font_tiny = pygame.font.Font(None, 18)
    font_hud_big = pygame.font.Font(None, 64)
    font_hud_med = pygame.font.Font(None, 42)
    font_hud_timer = pygame.font.Font(None, 84)
    font_winner = pygame.font.Font(None, 94)


# ── Drawing Utilities ──────────────────────────────────────────────────────

def draw_text_with_outlines(surface, text, font, font_color, inner_outline, outer_outline, x, y):
    text_surf = font.render(text, True, font_color)
    inner_surf = font.render(text, True, inner_outline)
    outer_surf = font.render(text, True, outer_outline)

    for ox in range(-5, 6):
        for oy in range(-5, 6):
            if abs(ox) + abs(oy) > 6:
                continue
            rect = outer_surf.get_rect(center=(x + ox, y + oy + 3))
            surface.blit(outer_surf, rect)

    for ox in range(-2, 3):
        for oy in range(-2, 3):
            if abs(ox) + abs(oy) > 2:
                continue
            rect = inner_surf.get_rect(center=(x + ox, y + oy))
            surface.blit(inner_surf, rect)

    rect = text_surf.get_rect(center=(x, y))
    surface.blit(text_surf, rect)


def draw_outlined_text(surface, text, font, color, x, y, outline_color=BLACK, outline_width=2, anchor="center"):
    """Simpler outline text helper."""
    outline_surf = font.render(text, True, outline_color)
    text_surf = font.render(text, True, color)

    for ox in range(-outline_width, outline_width + 1):
        for oy in range(-outline_width, outline_width + 1):
            if ox == 0 and oy == 0:
                continue
            if anchor == "center":
                r = outline_surf.get_rect(center=(x + ox, y + oy))
            elif anchor == "topleft":
                r = outline_surf.get_rect(topleft=(x + ox, y + oy))
            elif anchor == "midleft":
                r = outline_surf.get_rect(midleft=(x + ox, y + oy))
            surface.blit(outline_surf, r)

    if anchor == "center":
        r = text_surf.get_rect(center=(x, y))
    elif anchor == "topleft":
        r = text_surf.get_rect(topleft=(x, y))
    elif anchor == "midleft":
        r = text_surf.get_rect(midleft=(x, y))
    surface.blit(text_surf, r)


def draw_panel(surface, rect, alpha=200, border_color=LIGHT_BLUE, border_width=2):
    """Draw a semi-transparent dark panel with a glowing border."""
    s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    s.fill((10, 15, 30, alpha))
    surface.blit(s, (rect[0], rect[1]))
    pygame.draw.rect(surface, border_color, rect, border_width, border_radius=4)


def draw_glow_rect(surface, rect, color, intensity=30):
    """Draw a glowing rectangle effect."""
    for i in range(3):
        expand = i * 3
        glow_rect = (rect[0] - expand, rect[1] - expand,
                     rect[2] + expand * 2, rect[3] + expand * 2)
        glow_color = (color[0], color[1], color[2], intensity - i * 8)
        s = pygame.Surface((glow_rect[2], glow_rect[3]), pygame.SRCALPHA)
        pygame.draw.rect(s, glow_color, s.get_rect(), border_radius=6)
        surface.blit(s, (glow_rect[0], glow_rect[1]))


# ── Transition Effect ──────────────────────────────────────────────────────

class ScreenTransition:
    """Handles smooth fade-in/out transitions between screens."""

    def __init__(self):
        self.active = False
        self.progress = 0.0
        self.speed = 3.0  # transitions per second
        self.fading_out = True
        self.callback = None
        self.overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    def start(self, callback=None):
        """Start a fade-out → callback → fade-in transition."""
        self.active = True
        self.progress = 0.0
        self.fading_out = True
        self.callback = callback

    def update(self, dt):
        if not self.active:
            return
        self.progress += self.speed * dt
        if self.progress >= 1.0:
            if self.fading_out:
                # Reached full black — execute callback and start fade-in
                self.fading_out = False
                self.progress = 0.0
                if self.callback:
                    self.callback()
            else:
                # Fade-in complete
                self.active = False
                self.progress = 0.0

    def draw(self, surface):
        if not self.active:
            return
        if self.fading_out:
            alpha = int(self.progress * 255)
        else:
            alpha = int((1.0 - self.progress) * 255)
        alpha = max(0, min(255, alpha))
        self.overlay.fill((0, 0, 0, alpha))
        surface.blit(self.overlay, (0, 0))


# ── Button Classes ─────────────────────────────────────────────────────────

class MenuButton:
    """Start-menu style button with hover/select effects."""

    def __init__(self, text, x, y, width, height, selected=False):
        self.text = text
        self.rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
        self.selected = selected

    def draw(self, surface, time):
        pulse = math.sin(time * 5) * 0.5 + 0.5

        if self.selected:
            bg_color = (15 + int(pulse * 10), 35 + int(pulse * 15), 65 + int(pulse * 25))
            border_color = (130 + int(pulse * 60), 220, 255)
            text_color = WHITE
            border_width = 4
        else:
            bg_color = (20, 30, 45)
            border_color = (80, 80, 100)
            text_color = (200, 200, 200)
            border_width = 2

        # Shadow
        shadow_rect = self.rect.copy()
        shadow_rect.y += 6
        pygame.draw.rect(surface, (10, 10, 15), shadow_rect, border_radius=8)

        # Main body
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=8)

        # Glossy highlight
        highlight = pygame.Surface((self.rect.width - 8, self.rect.height // 2 - 4), pygame.SRCALPHA)
        pygame.draw.rect(highlight, (255, 255, 255, 15), highlight.get_rect(), border_radius=4)
        surface.blit(highlight, (self.rect.x + 4, self.rect.y + 4))

        # Border
        pygame.draw.rect(surface, border_color, self.rect, border_width, border_radius=8)

        # Text
        text_shadow = font_button.render(self.text, True, BLACK)
        text_surf = font_button.render(self.text, True, text_color)

        text_x = self.rect.centerx
        if self.selected:
            text_x += 15

        shadow_rect_text = text_shadow.get_rect(center=(text_x + 2, self.rect.centery + 2))
        surface.blit(text_shadow, shadow_rect_text)

        text_rect = text_surf.get_rect(center=(text_x, self.rect.centery))

        if self.selected:
            arrow = font_button.render(">>", True, YELLOW)
            arrow_rect = arrow.get_rect(midright=(text_rect.left - 10, text_rect.centery))
            arrow_shadow = font_button.render(">>", True, BLACK)
            arr_sh_rect = arrow_shadow.get_rect(midright=(text_rect.left - 10 + 2, text_rect.centery + 2))
            surface.blit(arrow_shadow, arr_sh_rect)
            surface.blit(arrow, arrow_rect)

        surface.blit(text_surf, text_rect)


class WeaponCard:
    """A selectable weapon card for the weapon-select screen."""

    WEAPONS = {
        "Aether Blade": {"color": (100, 180, 255), "type": "sword", "desc": "Fast slashes, forward lunge"},
        "Galaxy Bow": {"color": (100, 220, 130), "type": "bow", "desc": "Ranged shots, back-hop dodge"},
        "Void Hammer": {"color": (220, 100, 100), "type": "hammer", "desc": "Heavy hits, ground slam"},
    }

    def __init__(self, name, x, y, width=160, height=140):
        self.name = name
        self.rect = pygame.Rect(x, y, width, height)
        self.info = self.WEAPONS.get(name, {"color": WHITE, "type": "sword", "desc": ""})
        self.selected = False
        self.hover = False

    def draw(self, surface, time):
        pulse = math.sin(time * 4) * 0.5 + 0.5

        if self.selected:
            border_color = YELLOW
            bg_alpha = 220
            border_w = 4
            # Draw glow effect
            draw_glow_rect(surface, (self.rect.x, self.rect.y, self.rect.w, self.rect.h), YELLOW, 25)
        elif self.hover:
            border_color = LIGHT_BLUE
            bg_alpha = 180
            border_w = 3
        else:
            border_color = (80, 80, 100)
            bg_alpha = 140
            border_w = 2

        # Background
        s = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        s.fill((15, 20, 35, bg_alpha))
        surface.blit(s, self.rect.topleft)

        # Draw weapon icon (stylized shape)
        icon_cx = self.rect.centerx
        icon_cy = self.rect.y + 55
        wtype = self.info["type"]
        wcolor = self.info["color"]

        if wtype == "sword":
            # Sword shape
            pygame.draw.rect(surface, wcolor, (icon_cx - 4, icon_cy - 30, 8, 50), border_radius=2)
            pygame.draw.rect(surface, YELLOW, (icon_cx - 16, icon_cy + 12, 32, 6), border_radius=2)
            pygame.draw.polygon(surface, (200, 220, 255),
                                [(icon_cx, icon_cy - 35), (icon_cx - 6, icon_cy - 25), (icon_cx + 6, icon_cy - 25)])
        elif wtype == "bow":
            # Bow shape
            pygame.draw.arc(surface, wcolor,
                            (icon_cx - 20, icon_cy - 30, 25, 60),
                            math.pi * 0.25, math.pi * 0.75, 4)
            pygame.draw.line(surface, wcolor, (icon_cx - 8, icon_cy - 25), (icon_cx - 8, icon_cy + 25), 2)
            # Arrow
            pygame.draw.line(surface, ORANGE, (icon_cx - 5, icon_cy), (icon_cx + 25, icon_cy), 3)
            pygame.draw.polygon(surface, ORANGE,
                                [(icon_cx + 25, icon_cy), (icon_cx + 18, icon_cy - 5), (icon_cx + 18, icon_cy + 5)])
        elif wtype == "hammer":
            # Hammer shape
            pygame.draw.rect(surface, (140, 100, 70), (icon_cx - 3, icon_cy - 10, 6, 40), border_radius=2)
            pygame.draw.rect(surface, wcolor, (icon_cx - 18, icon_cy - 25, 36, 20), border_radius=4)

        # Border
        pygame.draw.rect(surface, border_color, self.rect, border_w, border_radius=6)

        # Weapon name
        draw_outlined_text(surface, self.name, font_tiny, WHITE, self.rect.centerx, self.rect.bottom - 22)

        # Selected check mark
        if self.selected:
            check_color = (int(pulse * 50 + 200), 255, int(pulse * 50 + 200))
            draw_outlined_text(surface, "✓", font_label, check_color, self.rect.right - 16, self.rect.top + 16)


class ArenaCard:
    """A selectable arena card for the arena vote screen."""

    ARENAS = [
        {"name": "Aether Cleft", "color": (200, 80, 50), "id": 0},
        {"name": "Nebula Shards", "color": (120, 80, 200), "id": 1},
        {"name": "Chronos Gears", "color": (180, 150, 80), "id": 2},
        {"name": "Gravity Well", "color": (80, 60, 180), "id": 3},
        {"name": "Comet Causeway", "color": (100, 160, 200), "id": 4},
        {"name": "Void Vortex", "color": (150, 50, 180), "id": 5},
    ]

    def __init__(self, arena_info, x, y, width=180, height=140):
        self.name = arena_info["name"]
        self.arena_id = arena_info["id"]
        self.color = arena_info["color"]
        self.rect = pygame.Rect(x, y, width, height)
        self.votes = 0
        self.selected = False
        self.hover = False
        
        # Load map preview image
        img_name = f"map_{self.name.lower().replace(' ', '')}.png"
        path = os.path.join("assets", "maps", img_name)
        try:
            self.image = pygame.image.load(path).convert_alpha()
            self.image = pygame.transform.scale(self.image, (width, height))
            # Darken the image a bit for readability
            darken = pygame.Surface((width, height), pygame.SRCALPHA)
            darken.fill((0, 0, 0, 60))
            self.image.blit(darken, (0, 0))
        except Exception:
            self.image = None

    def draw(self, surface, time):
        if self.selected:
            border_color = CYAN
            border_w = 4
            draw_glow_rect(surface, (self.rect.x, self.rect.y, self.rect.w, self.rect.h), CYAN, 25)
        elif self.hover:
            border_color = LIGHT_BLUE
            border_w = 3
        else:
            border_color = (60, 70, 90)
            border_w = 2

        # Background
        if self.image:
            surface.blit(self.image, self.rect)
        else:
            # Fallback gradient
            s = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
            for row in range(self.rect.h):
                t = row / self.rect.h
                r = int(self.color[0] * (1.0 - t * 0.7))
                g = int(self.color[1] * (1.0 - t * 0.7))
                b = int(self.color[2] * (1.0 - t * 0.7))
                alpha = 160 if self.selected else 120
                pygame.draw.line(s, (r, g, b, alpha), (0, row), (self.rect.w, row))
            surface.blit(s, self.rect.topleft)

        # Border
        pygame.draw.rect(surface, border_color, self.rect, border_w, border_radius=6)
        # Arena name
        draw_outlined_text(surface, self.name, font_tiny, WHITE, self.rect.centerx, self.rect.bottom - 18)

        # Vote count badge
        if self.votes > 0:
            badge_x = self.rect.right - 22
            badge_y = self.rect.top + 18
            pygame.draw.circle(surface, (0, 0, 0, 180), (badge_x, badge_y), 14)
            pygame.draw.circle(surface, CYAN, (badge_x, badge_y), 14, 2)
            draw_outlined_text(surface, str(self.votes), font_tiny, WHITE, badge_x, badge_y)


class PlayerDisplay:
    """Draws a player portrait + weapon selection in the lobby."""
    PLAYER_COLORS = [
        {"hair": (80, 160, 255), "armor": (100, 180, 255), "name": "LUNA"},
        {"hair": (60, 140, 80), "armor": (80, 180, 100), "name": "RAVEN"},
        {"hair": (200, 80, 80), "armor": (220, 100, 100), "name": "BLAZE"},
        {"hair": (200, 160, 60), "armor": (220, 180, 80), "name": "SPARK"},
    ]

    def __init__(self, player_id, x, y, width=520, height=200):
        self.player_id = player_id
        self.rect = pygame.Rect(x, y, width, height)
        self.info = self.PLAYER_COLORS[player_id % len(self.PLAYER_COLORS)]
        card_y = y + 55
        card_x_start = x + 140
        card_spacing = 10
        card_w, card_h = 115, 110
        weapon_names = list(WeaponCard.WEAPONS.keys())
        self.weapon_cards = []
        for i, wname in enumerate(weapon_names):
            cx = card_x_start + i * (card_w + card_spacing)
            card = WeaponCard(wname, cx, card_y, card_w, card_h)
            self.weapon_cards.append(card)
        self.selected_weapon = 0
        self.weapon_cards[0].selected = True
        self.confirmed = False

    def select_weapon(self, index):
        for card in self.weapon_cards:
            card.selected = False
        self.selected_weapon = index % len(self.weapon_cards)
        self.weapon_cards[self.selected_weapon].selected = True

    def draw(self, surface, time):
        draw_panel(surface, (self.rect.x, self.rect.y, self.rect.w, self.rect.h),
                   alpha=180, border_color=LIGHT_BLUE if not self.confirmed else CONFIRM_GREEN)
        portrait_x = self.rect.x + 15
        portrait_y = self.rect.y + 15
        portrait_w, portrait_h = 110, self.rect.h - 30
        portrait_rect = (portrait_x, portrait_y, portrait_w, portrait_h)
        pygame.draw.rect(surface, (15, 20, 35), portrait_rect, border_radius=6)
        pygame.draw.rect(surface, self.info["armor"], portrait_rect, 2, border_radius=6)
        face_cx = portrait_x + portrait_w // 2
        face_cy = portrait_y + 50
        sprite = luna_portrait if self.player_id == 0 else raven_portrait
        if sprite:
            sx = face_cx - sprite.get_width() // 2
            sy = face_cy - 40
            surface.blit(sprite, (sx, sy))
        else:
            pygame.draw.circle(surface, (220, 190, 160), (face_cx, face_cy), 22)
            pygame.draw.ellipse(surface, self.info["hair"], (face_cx - 24, face_cy - 26, 48, 28))
        draw_outlined_text(surface, self.info["name"], font_label, WHITE,
                           portrait_x + portrait_w // 2, self.rect.bottom - 22)
        header_x = self.rect.x + 140
        header_y = self.rect.y + 15
        draw_outlined_text(surface, "CHOOSE PRIMARY WEAPON", font_small, LIGHT_BLUE,
                           header_x + 180, header_y + 8)

        # Weapon cards
        for card in self.weapon_cards:
            card.draw(surface, time)

        # Confirmed overlay
        if self.confirmed:
            s = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
            s.fill((0, 20, 0, 60))
            surface.blit(s, self.rect.topleft)
            draw_outlined_text(surface, "READY!", font_subheader, CONFIRM_GREEN,
                               self.rect.centerx, self.rect.centery, outline_width=3)


# ── Game HUD (used during gameplay) ────────────────────────────────────────

class GameHUD:
    """
    Full in-game HUD matching the concept art:
    - Player portraits with health bars (left & right)
    - Center timer
    - Stock counter
    - Arena name banner
    - Winner announcement overlay
    """

    def __init__(self, player_names=None, stocks=3):
        self.player_names = player_names or ["LUNA", "RAVEN"]
        self.stocks = [stocks, stocks]
        self.damage_pcts = [0.0, 0.0]
        self.timer = 120.0  # 2-minute match
        self.arena_name = "AETHER CLEFT"
        self.winner = None
        self.winner_timer = 0.0
        self.player_colors = [(100, 180, 255), (100, 220, 130)]

    def update(self, dt, fighters=None):
        """Update HUD state from fighter data."""
        if self.timer > 0 and self.winner is None:
            self.timer -= dt

        if fighters:
            for i, f in enumerate(fighters[:2]):
                self.damage_pcts[i] = f.damage_pct

        if self.winner is not None:
            self.winner_timer += dt

    def set_winner(self, player_index):
        self.winner = player_index
        self.winner_timer = 0.0

    def draw(self, surface, time):
        self._draw_player_hud(surface, time, 0, left=True)
        self._draw_player_hud(surface, time, 1, left=False)
        self._draw_timer(surface, time)
        self._draw_stocks(surface)
        self._draw_arena_banner(surface)

        if self.winner is not None:
            self._draw_winner_overlay(surface, time)

    def _draw_player_hud(self, surface, time, player_idx, left=True):
        """Draw a single player's HUD panel (portrait + health bar)."""
        panel_w = 320
        panel_h = 80
        margin = 20

        if left:
            px = margin
        else:
            px = WIDTH - panel_w - margin
        py = 15

        # Panel background
        draw_panel(surface, (px, py, panel_w, panel_h), alpha=200, border_color=(60, 70, 90))

        # Portrait box
        portrait_size = 56
        port_x = px + 8 if left else px + panel_w - portrait_size - 8
        port_y = py + (panel_h - portrait_size) // 2

        pygame.draw.rect(surface, (20, 25, 40), (port_x, port_y, portrait_size, portrait_size), border_radius=6)
        pygame.draw.rect(surface, self.player_colors[player_idx],
                         (port_x, port_y, portrait_size, portrait_size), 2, border_radius=6)

        # Mini portrait face
        face_cx = port_x + portrait_size // 2
        face_cy = port_y + portrait_size // 2
        pygame.draw.circle(surface, (220, 190, 160), (face_cx, face_cy - 3), 14)
        hair_colors = [(80, 160, 255), (60, 140, 80)]
        pygame.draw.ellipse(surface, hair_colors[player_idx],
                            (face_cx - 16, face_cy - 18, 32, 16))
        pygame.draw.circle(surface, BLACK, (face_cx - 4, face_cy - 1), 3)
        pygame.draw.circle(surface, BLACK, (face_cx + 4, face_cy - 1), 3)

        # Player name
        name = self.player_names[player_idx]
        if left:
            name_x = port_x + portrait_size + 12
        else:
            name_x = port_x - 12
        name_anchor = "midleft" if left else "midleft"
        draw_outlined_text(surface, name, font_label, WHITE,
                           name_x if left else px + 10, py + 18,
                           anchor="midleft")

        # Health bar
        bar_w = 180
        bar_h = 18
        if left:
            bar_x = port_x + portrait_size + 12
        else:
            bar_x = px + 10
        bar_y = py + 42

        # Bar background
        pygame.draw.rect(surface, (30, 30, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=3)

        # Bar fill (color changes with damage)
        pct = self.damage_pcts[player_idx]
        fill_ratio = max(0, 1.0 - pct / 150.0)
        if pct < 40:
            bar_color = GREEN
        elif pct < 80:
            bar_color = YELLOW
        elif pct < 120:
            bar_color = ORANGE
        else:
            bar_color = RED

        fill_w = int(bar_w * fill_ratio)
        if fill_w > 0:
            pygame.draw.rect(surface, bar_color, (bar_x, bar_y, fill_w, bar_h), border_radius=3)
            # Glossy bar highlight
            pygame.draw.rect(surface, tuple(min(255, c + 60) for c in bar_color),
                             (bar_x, bar_y, fill_w, bar_h // 2), border_radius=3)

        # Bar border
        pygame.draw.rect(surface, (100, 110, 130), (bar_x, bar_y, bar_w, bar_h), 2, border_radius=3)

        # Damage percentage text
        pct_text = f"{int(pct)}%"
        if pct < 60:
            pct_color = WHITE
        elif pct < 120:
            pct_color = ORANGE
        else:
            pct_color = RED

        draw_outlined_text(surface, pct_text, font_label, pct_color,
                           bar_x + bar_w + 20, bar_y + bar_h // 2)

    def _draw_timer(self, surface, time):
        """Draw the match timer in the center top."""
        minutes = int(self.timer) // 60
        seconds = int(self.timer) % 60
        timer_text = f"{minutes}:{seconds:02d}"

        # Timer glow when low
        if self.timer < 30:
            pulse = math.sin(time * 6) * 0.5 + 0.5
            color = (255, int(100 + pulse * 100), int(pulse * 80))
        else:
            color = WHITE

        draw_text_with_outlines(surface, timer_text, font_hud_timer, color, WHITE, BLACK,
                                WIDTH // 2, 55)

    def _draw_stocks(self, surface):
        """Draw stock (lives) counter below the timer."""
        stocks_text = f"STOCKS: {self.stocks[0]} vs {self.stocks[1]}"
        draw_outlined_text(surface, stocks_text, font_small, LIGHT_BLUE,
                           WIDTH // 2, 100)

    def _draw_arena_banner(self, surface):
        """Draw the arena name at the bottom center."""
        banner_w = 300
        banner_h = 36
        bx = WIDTH // 2 - banner_w // 2
        by = HEIGHT - 40

        # Banner background
        s = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        surface.blit(s, (bx, by))
        pygame.draw.rect(surface, (80, 90, 110), (bx, by, banner_w, banner_h), 2, border_radius=4)

        draw_outlined_text(surface, self.arena_name, font_small, LIGHT_BLUE,
                           WIDTH // 2, by + banner_h // 2)

    def _draw_winner_overlay(self, surface, time):
        """Draw the winner announcement with dramatic effect."""
        # Darken background
        alpha = min(180, int(self.winner_timer * 200))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        surface.blit(overlay, (0, 0))

        if self.winner_timer > 0.5:
            # Winner text with pulse
            pulse = math.sin(time * 3) * 0.3 + 0.7
            name = self.player_names[self.winner]
            winner_color = self.player_colors[self.winner]

            # Scale effect
            scale = min(1.0, (self.winner_timer - 0.5) * 3.0)

            draw_text_with_outlines(surface, f"{name} WINS!", font_winner,
                                    YELLOW, WHITE, BLACK, WIDTH // 2, HEIGHT // 2 - 30)

            if self.winner_timer > 1.5:
                draw_outlined_text(surface, "PRESS ENTER TO CONTINUE", font_label,
                                   (int(pulse * 255), int(pulse * 255), int(pulse * 255)),
                                   WIDTH // 2, HEIGHT // 2 + 60)


# ── Screen: Start Menu ────────────────────────────────────────────────────

async def screen_start_menu():
    """The main start menu screen. Returns the action chosen."""
    buttons = [
        MenuButton("START GAME", WIDTH // 2, 560, 240, 55),
        MenuButton("NEW PROFILE", WIDTH // 2, 560, 240, 55),
        MenuButton("OPTIONS", WIDTH // 2, 560, 220, 55),
        MenuButton("CREDITS", WIDTH // 2, 560, 220, 55),
    ]

    # Position buttons horizontally like in the concept
    total_btn_width = 240 + 240 + 220 + 220 + 3 * 30
    start_x = (WIDTH - total_btn_width) // 2
    offsets = [0, 270, 510, 730]
    widths = [240, 240, 220, 220]
    for i, btn in enumerate(buttons):
        cx = start_x + offsets[i] + widths[i] // 2
        btn.rect = pygame.Rect(cx - widths[i] // 2, 620, widths[i], 55)

    selected = 0
    buttons[selected].selected = True
    pulse_timer = 0
    transition = ScreenTransition()
    result = [None]

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        pulse_timer += dt
        transition.update(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"
            elif event.type == pygame.KEYDOWN and not transition.active:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    buttons[selected].selected = False
                    selected = (selected - 1) % len(buttons)
                    buttons[selected].selected = True
                    play_ui_sfx("ui_move")
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    buttons[selected].selected = False
                    selected = (selected + 1) % len(buttons)
                    buttons[selected].selected = True
                    play_ui_sfx("ui_move")
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    play_ui_sfx("ui_confirm")
                    if selected == 0:
                        result[0] = "START_GAME"
                        transition.start(lambda: None)
                    elif selected == 3:
                        result[0] = "CREDITS"
        # Yield control for pygbag/browser
        await asyncio.sleep(0)

        # Draw
        # Cycle through background frames for animation (~15 FPS)
        frame_idx = int(pulse_timer * 15) % len(anim_background_frames)
        screen.blit(anim_background_frames[frame_idx], (0, 0))

        # Version label
        version_surf = font_small.render("VERSION 1.0", True, (150, 160, 180))
        screen.blit(version_surf, (20, 20))

        # Title
        draw_text_with_outlines(screen, "GAUNTLET", font_title_large, LIGHT_BLUE, WHITE, BLACK, WIDTH // 2, 170)
        draw_text_with_outlines(screen, "GALAXY", font_title_small, ORANGE, YELLOW, BLACK, WIDTH // 2, 280)

        # Prompt text (pulsing)
        pulse_alpha = int((math.sin(pulse_timer * 4) * 0.2 + 0.8) * 255)
        prompt_text = "[START] PRESS ANY BUTTON"
        prompt_surf = font_prompt.render(prompt_text, True, ORANGE)
        prompt_outline = font_prompt.render(prompt_text, True, BLACK)
        prompt_surf.set_alpha(pulse_alpha)
        prompt_outline.set_alpha(pulse_alpha)
        prompt_rect = prompt_surf.get_rect(center=(WIDTH // 2, 480))
        screen.blit(prompt_outline, (prompt_rect.x + 3, prompt_rect.y + 3))
        screen.blit(prompt_surf, prompt_rect)

        # Bottom buttons
        for btn in buttons:
            btn.draw(screen, pulse_timer)

        # Footer
        draw_outlined_text(screen, "A CONFIRM", font_tiny, GRAY, WIDTH // 2, HEIGHT - 22)

        transition.draw(screen)
        pygame.display.flip()

        if result[0] and not transition.active:
            return result[0]

    return "QUIT"


# ── Screen: Credits ──────────────────────────────────────────────────────────

async def screen_credits():
    """Simple credits screen with back button."""
    running = True
    pulse_timer = 0
    while running:
        await asyncio.sleep(0)
        dt = clock.tick(FPS) / 1000.0
        pulse_timer += dt
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                play_ui_sfx("ui_exit")
                running = False
        
        # Simple draw
        screen.fill(BG_COLOR)
        draw_outlined_text(screen, "GAUNTLET GALAXY", font_title_small, WHITE, WIDTH // 2, 120)
        draw_outlined_text(screen, "BY THIJS, HAYYAN & FINN", font_subheader, LIGHT_BLUE, WIDTH // 2, 220)
        draw_outlined_text(screen, "BUILT WITH PYGAME", font_label, GRAY, WIDTH // 2, 340)
        draw_outlined_text(screen, "PRESS ESC TO RETURN", font_tiny, WHITE, WIDTH // 2, HEIGHT - 100)
        pygame.display.flip()


# ── Screen: Matchmaking ────────────────────────────────────────────────────

async def screen_matchmaking():
    """Matchmaking / looking-for-teammate screen. Returns when teammate found."""
    state_timer = 0
    pulse_timer = 0
    teammate_found = False
    transition = ScreenTransition()
    done = [False]

    running = True
    while running:
        # Yield control for pygbag/browser
        await asyncio.sleep(0)
        dt = clock.tick(FPS) / 1000.0
        pulse_timer += dt
        state_timer += dt
        transition.update(dt)

        if state_timer > 2.0:
            teammate_found = True

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"
            elif event.type == pygame.KEYDOWN and not transition.active:
                if teammate_found and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    play_ui_sfx("ui_confirm")
                    done[0] = True
                    transition.start(lambda: None)

        # Draw
        # Cycle through background frames for animation (~15 FPS)
        frame_idx = int(pulse_timer * 15) % len(anim_background_frames)
        screen.blit(anim_background_frames[frame_idx], (0, 0))

        if not teammate_found:
            pulse_alpha = int((math.sin(pulse_timer * 6) * 0.3 + 0.7) * 255)
            match_txt = "SEARCHING FOR PLAYERS..."
        else:
            pulse_alpha = 255
            match_txt = "TEAMMATE FOUND!"

        # Header panel
        panel_height = 80
        s = pygame.Surface((WIDTH, panel_height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 160))
        screen.blit(s, (0, 40))
        pygame.draw.line(screen, LIGHT_BLUE, (0, 40), (WIDTH, 40), 2)
        pygame.draw.line(screen, LIGHT_BLUE, (0, 40 + panel_height), (WIDTH, 40 + panel_height), 2)

        color = LIGHT_BLUE if not teammate_found else ORANGE
        match_surf = font_prompt.render(match_txt, True, color)
        match_outline = font_prompt.render(match_txt, True, BLACK)
        match_surf.set_alpha(pulse_alpha)
        match_outline.set_alpha(pulse_alpha)
        match_rect = match_surf.get_rect(center=(WIDTH // 2, 40 + panel_height // 2))
        screen.blit(match_outline, (match_rect.x + 3, match_rect.y + 3))
        screen.blit(match_surf, match_rect)

        if teammate_found:
            # Animation timing: pop up over 0.6 seconds
            progress = min(1.0, (state_timer - 2.0) * 1.6)
            alpha = int(progress * 255)
            
            # Pop up vertical offset (slides from below)
            pop_offset = int((1.0 - progress) * 80)
            
            # Draw Luna (P1)
            if luna_portrait:
                luna_p = luna_portrait.copy()
                luna_p.set_alpha(alpha)
                lx = 320 - luna_p.get_width() // 2
                ly = 510 - luna_p.get_height() // 2 + pop_offset
                screen.blit(luna_p, (lx, ly))

            # Draw Raven (P2)
            if raven_portrait:
                raven_p = raven_portrait.copy()
                raven_p.set_alpha(alpha)
                rx = 960 - raven_p.get_width() // 2
                ry = 510 - raven_p.get_height() // 2 + pop_offset
                screen.blit(raven_p, (rx, ry))

            continue_btn = MenuButton("CONTINUE TO LOBBY", WIDTH // 2, 600, 360, 60, selected=True)
            continue_btn.draw(screen, pulse_timer)

        transition.draw(screen)
        pygame.display.flip()

        if done[0] and not transition.active:
            return "LOBBY"

    return "QUIT"


# ── Screen: Battle Lobby (Weapon Select + Arena Vote) ──────────────────────

async def screen_battle_lobby():
    """Combined weapon select + arena vote screen. Returns selections."""
    # Player displays (2 players)
    p1_display = PlayerDisplay(0, 40, 100, 520, 200)
    p2_display = PlayerDisplay(1, 40, 320, 520, 200)

    # Arena cards
    arenas = []
    arena_start_x = 620
    arena_start_y = 100
    card_w, card_h = 190, 140
    gap = 15
    for i, arena_info in enumerate(ArenaCard.ARENAS):
        row = i // 2
        col = i % 2
        ax = arena_start_x + col * (card_w + gap)
        ay = arena_start_y + row * (card_h + gap)
        arenas.append(ArenaCard(arena_info, ax, ay, card_w, card_h))

    # Selection state
    focus = "p1_weapon"  # p1_weapon → p2_weapon → arena → confirm
    p1_weapon_idx = 0
    p2_weapon_idx = 0
    arena_idx = 0
    arenas[0].selected = True
    arenas[0].votes = 1

    deploy_timer = 60.0
    vote_count = 0
    total_votes = 2

    pulse_timer = 0
    transition = ScreenTransition()
    result = [None]

    # Confirm button
    confirm_ready = False

    running = True
    while running:
        # Yield control for pygbag/browser
        await asyncio.sleep(0)
        dt = clock.tick(FPS) / 1000.0
        pulse_timer += dt
        deploy_timer -= dt
        transition.update(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN and not transition.active:
                if focus == "p1_weapon":
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        p1_weapon_idx = (p1_weapon_idx - 1) % 3
                        p1_display.select_weapon(p1_weapon_idx)
                        play_ui_sfx("ui_move")
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        p1_weapon_idx = (p1_weapon_idx + 1) % 3
                        p1_display.select_weapon(p1_weapon_idx)
                        play_ui_sfx("ui_move")
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        p1_display.confirmed = True
                        play_ui_sfx("ui_confirm")
                        focus = "p2_weapon"

                elif focus == "p2_weapon":
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        p2_weapon_idx = (p2_weapon_idx - 1) % 3
                        p2_display.select_weapon(p2_weapon_idx)
                        play_ui_sfx("ui_move")
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        p2_weapon_idx = (p2_weapon_idx + 1) % 3
                        p2_display.select_weapon(p2_weapon_idx)
                        play_ui_sfx("ui_move")
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        p2_display.confirmed = True
                        play_ui_sfx("ui_confirm")
                        focus = "arena"

                elif focus == "arena":
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        arenas[arena_idx].selected = False
                        arena_idx = (arena_idx - 1) % len(arenas)
                        arenas[arena_idx].selected = True
                        play_ui_sfx("ui_move")
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        arenas[arena_idx].selected = False
                        arena_idx = (arena_idx + 1) % len(arenas)
                        arenas[arena_idx].selected = True
                        play_ui_sfx("ui_move")
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        arenas[arena_idx].selected = False
                        arena_idx = (arena_idx - 2) % len(arenas)
                        arenas[arena_idx].selected = True
                        play_ui_sfx("ui_move")
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        arenas[arena_idx].selected = False
                        arena_idx = (arena_idx + 2) % len(arenas)
                        arenas[arena_idx].selected = True
                        play_ui_sfx("ui_move")
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        # Vote for this arena
                        arenas[arena_idx].votes += 1
                        vote_count += 1
                        play_ui_sfx("ui_confirm")
                        focus = "confirm"
                        confirm_ready = True

                elif focus == "confirm":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        # Map weapon index to fighter class name
                        weapon_names = list(WeaponCard.WEAPONS.keys())
                        weapon_types = [WeaponCard.WEAPONS[w]["type"] for w in weapon_names]

                        result[0] = {
                            "p1_weapon": weapon_types[p1_weapon_idx],
                            "p2_weapon": weapon_types[p2_weapon_idx],
                            "arena_id": arenas[arena_idx].arena_id,
                            "arena_name": arenas[arena_idx].name,
                        }
                        play_ui_sfx("ui_confirm")
                        transition.start(lambda: None)

                # Back button (B/Escape)
                if event.key == pygame.K_ESCAPE:
                    play_ui_sfx("ui_back")
                    if focus == "p2_weapon":
                        p1_display.confirmed = False
                        focus = "p1_weapon"
                    elif focus == "arena":
                        p2_display.confirmed = False
                        focus = "p2_weapon"
                    elif focus == "confirm":
                        focus = "arena"

        # ── Draw ──
        # Cycle through background frames for animation (~15 FPS)
        frame_idx = int(pulse_timer * 15) % len(anim_background_frames)
        screen.blit(anim_background_frames[frame_idx], (0, 0))

        # Dim overlay
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 100))
        screen.blit(dim, (0, 0))

        # Top bar
        draw_panel(screen, (0, 0, WIDTH, 50), alpha=230, border_color=(60, 70, 90))
        draw_outlined_text(screen, "GAUNTLET GALAXY - BATTLE LOBBY", font_label, LIGHT_BLUE, 220, 25,
                           anchor="center")

        # Deploy timer
        deploy_min = int(deploy_timer) // 60
        deploy_sec = int(deploy_timer) % 60
        timer_color = WHITE if deploy_timer > 15 else RED
        draw_outlined_text(screen, f"DEPLOY IN: {deploy_min}:{deploy_sec:02d}", font_label, timer_color,
                           WIDTH - 120, 25)

        # Players ready count
        ready_count = sum([p1_display.confirmed, p2_display.confirmed])
        draw_outlined_text(screen, f"PLAYERS READY: {ready_count}/2", font_small, LIGHT_BLUE,
                           WIDTH // 2, 70)

        # Left side: Team loadout
        draw_outlined_text(screen, "TEAM LOADOUT", font_subheader, WHITE, 300, 78, outline_width=3)
        p1_display.draw(screen, pulse_timer)
        p2_display.draw(screen, pulse_timer)

        # Right side: Stage select
        draw_outlined_text(screen, "STAGE SELECT", font_subheader, WHITE, 810, 78, outline_width=3)
        for arena in arenas:
            arena.draw(screen, pulse_timer)

        # Vote info
        draw_outlined_text(screen, f"VOTES CAST: {vote_count} / {total_votes}", font_small, LIGHT_BLUE,
                           730, HEIGHT - 100)
        draw_outlined_text(screen, f"VOTE ENDS: 0:{int(deploy_timer):02d}", font_small, ORANGE,
                           930, HEIGHT - 100)

        # Bottom bar - Confirm button
        draw_panel(screen, (0, HEIGHT - 70, WIDTH, 70), alpha=230, border_color=(60, 70, 90))

        # Input hints
        draw_outlined_text(screen, "A CONFIRM", font_tiny, GRAY, 80, HEIGHT - 40)
        draw_outlined_text(screen, "B BACK", font_tiny, GRAY, 200, HEIGHT - 40)

        # Big confirm button
        if confirm_ready:
            pulse = math.sin(pulse_timer * 5) * 0.5 + 0.5
            btn_color = (40 + int(pulse * 30), 180 + int(pulse * 40), 80 + int(pulse * 30))
            btn_rect = pygame.Rect(WIDTH // 2 - 200, HEIGHT - 65, 400, 55)
            pygame.draw.rect(screen, btn_color, btn_rect, border_radius=6)
            pygame.draw.rect(screen, WHITE, btn_rect, 3, border_radius=6)
            draw_outlined_text(screen, "CONFIRM SELECTIONS", font_button, WHITE,
                               WIDTH // 2, HEIGHT - 38)

        # Focus indicator (show what's being selected)
        focus_labels = {
            "p1_weapon": "Select weapon for LUNA (← → then ENTER)",
            "p2_weapon": "Select weapon for RAVEN (← → then ENTER)",
            "arena": "Vote for an arena (← → ↑ ↓ then ENTER)",
            "confirm": "Press ENTER to start battle!",
        }
        draw_outlined_text(screen, focus_labels.get(focus, ""), font_small,
                           YELLOW, WIDTH // 2, HEIGHT - 80)

        # START READY hint
        draw_outlined_text(screen, "START READY", font_tiny, GRAY, WIDTH - 80, HEIGHT - 40)

        transition.draw(screen)
        pygame.display.flip()

        if result[0] and not transition.active:
            return result[0]

    return None


# ── Main Flow ──────────────────────────────────────────────────────────────

async def main_menu():
    """Complete game flow: Start Menu → Matchmaking → Lobby → Game."""
    audio_manager.play_music("menu_theme_1")

    # STEP 1: Start Menu
    action = await screen_start_menu()
    if action == "QUIT":
        pygame.quit()
        sys.exit()

    if action == "CREDITS":
        await screen_credits()
        # After credits, go back to start
        await main_menu()
        return

    # STEP 2: Matchmaking
    result = await screen_matchmaking()
    if result == "QUIT":
        pygame.quit()
        sys.exit()

    # STEP 3: Battle Lobby (weapon select + arena vote)
    selections = await screen_battle_lobby()
    if selections is None:
        pygame.quit()
        sys.exit()

    print(f"Game starting with selections: {selections}")

    # STEP 4: Launch the actual game with the selections
    # Map weapon type to fighter class
    weapon_map = {
        "sword": "SwordFighter",
        "bow": "BowFighter",
        "hammer": "HammerFighter",
    }

    try:
        from client import SwordFighter, BowFighter, HammerFighter, Game, NetworkClient

        fighter_classes = {
            "sword": SwordFighter,
            "bow": BowFighter,
            "hammer": HammerFighter,
        }

        # Attempt network connection
        net = NetworkClient(host="localhost", port=5555)
        connected = net.connect()
        if not connected:
            print("[client] No server found — running in local/offline mode.")
            net = None

        game = Game(
            arena_id=selections["arena_id"],
            fighter_cls_local=fighter_classes[selections["p1_weapon"]],
            fighter_cls_remote=fighter_classes[selections["p2_weapon"]],
            net=net,
            audio_manager=audio_manager,
        )

        # Configure the HUD arena name from lobby selection
        game.hud.arena_name = selections["arena_name"].upper()

        await game.run()

    except ImportError as e:
        print(f"Could not import client module: {e}")
        print("Game would start with:", selections)

    pygame.quit()
    sys.exit()


async def main_menu_async():
    await main_menu()


if __name__ == "__main__":
    asyncio.run(main_menu())
