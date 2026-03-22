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
import socket
import time

from src.audio import get_shared_audio_manager
import server
from src.network.network_client import NetworkClient

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
PURPLE = (180, 80, 255)
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

# Weapon icons
weapon_icons = {}
try:
    sword_sheet = pygame.image.load(os.path.join("assets", "SwordSpriteSheet.png")).convert_alpha()
    bow_sheet = pygame.image.load(os.path.join("assets", "BowSpriteSheet.png")).convert_alpha()
    hammer_sheet = pygame.image.load(os.path.join("assets", "hammer_spritesheet.png")).convert_alpha()
    
    # Each is 4x3 (12 frames)
    def extract_icon(sheet, cols=4, rows=3):
        fw = sheet.get_width() // cols
        fh = sheet.get_height() // rows
        return sheet.subsurface(pygame.Rect(0, 0, fw, fh))

    weapon_icons["sword"] = pygame.transform.scale(extract_icon(sword_sheet), (80, 80))
    weapon_icons["bow"] = pygame.transform.scale(extract_icon(bow_sheet), (80, 80))
    weapon_icons["hammer"] = pygame.transform.scale(extract_icon(hammer_sheet), (80, 80))
except Exception as e:
    print(f"Could not load weapon icons: {e}")


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

def draw_panel(surface, rect, color=BLACK, alpha=200, border_color=GRAY, border_w=3, radius=10):
    s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alpha), s.get_rect(), border_radius=radius)
    if border_w > 0:
        pygame.draw.rect(s, border_color, s.get_rect(), width=border_w, border_radius=radius)
    surface.blit(s, (rect[0], rect[1]))

async def find_lan_host(room_key: str, port=5556, timeout=1.5) -> str | None:
    """Listens for a LAN UDP broadcast from a host for `timeout` seconds."""
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp.setblocking(False)
    try:
        udp.bind(('', port))
    except Exception:
        pass  # If we can't bind (e.g. port in use), we'll try listening anyway
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            data, addr = udp.recvfrom(1024)
            if data and data.decode().upper() == f"GAUNTLET_GALAXY|{room_key.upper()}":
                return addr[0]
        except BlockingIOError:
            pass  # No data yet
        except OSError:
            break
        await asyncio.sleep(0.05)
    return None

# ============================================================================
# MATCHMAKING SCREEN (Find opponent)
# ============================================================================


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

        # Draw weapon icon
        icon_cx = self.rect.centerx
        icon_cy = self.rect.y + 50
        wtype = self.info["type"]
        wcolor = self.info["color"]

        icon_img = weapon_icons.get(wtype)
        if icon_img:
            # Apply a slight scale when selected or hovered
            scale_mod = 1.0
            if self.selected:
                scale_mod = 1.15 + math.sin(time * 6) * 0.05
            elif self.hover:
                scale_mod = 1.08

            target_w = int(icon_img.get_width() * scale_mod)
            target_h = int(icon_img.get_height() * scale_mod)
            img = pygame.transform.scale(icon_img, (target_w, target_h))
            surface.blit(img, img.get_rect(center=(icon_cx, icon_cy)))
        else:
            # Fallback stylized shapes (Old temporary solution)
            if wtype == "sword":
                pygame.draw.rect(surface, wcolor, (icon_cx - 4, icon_cy - 30, 8, 50), border_radius=2)
                pygame.draw.rect(surface, YELLOW, (icon_cx - 16, icon_cy + 12, 32, 6), border_radius=2)
                pygame.draw.polygon(surface, (200, 220, 255),
                                    [(icon_cx, icon_cy - 35), (icon_cx - 6, icon_cy - 25), (icon_cx + 6, icon_cy - 25)])
            elif wtype == "bow":
                pygame.draw.arc(surface, wcolor, (icon_cx - 20, icon_cy - 30, 25, 60), 
                                math.pi * 0.25, math.pi * 0.75, 4)
                pygame.draw.line(surface, wcolor, (icon_cx - 8, icon_cy - 25), (icon_cx - 8, icon_cy + 25), 2)
                pygame.draw.line(surface, ORANGE, (icon_cx - 5, icon_cy), (icon_cx + 25, icon_cy), 3)
                pygame.draw.polygon(surface, ORANGE,
                                    [(icon_cx + 25, icon_cy), (icon_cx + 18, icon_cy - 5), (icon_cx + 18, icon_cy + 5)])
            elif wtype == "hammer":
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
        self.opp_selected = False
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
        if self.selected and getattr(self, "opp_selected", False):
            border_color = PURPLE
            border_w = 4
            draw_glow_rect(surface, (self.rect.x, self.rect.y, self.rect.w, self.rect.h), PURPLE, 25)
        elif self.selected:
            border_color = CYAN
            border_w = 4
            draw_glow_rect(surface, (self.rect.x, self.rect.y, self.rect.w, self.rect.h), CYAN, 25)
        elif getattr(self, "opp_selected", False):
            border_color = RED
            border_w = 4
            draw_glow_rect(surface, (self.rect.x, self.rect.y, self.rect.w, self.rect.h), RED, 25)
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
        MenuButton("CREDITS", WIDTH // 2, 560, 220, 55),
    ]

    # Position buttons horizontally like in the concept
    spacing = 30
    widths = [240, 220]
    total_btn_width = sum(widths) + (len(widths) - 1) * spacing
    start_x = (WIDTH - total_btn_width) // 2
    
    current_x = start_x
    for i, btn in enumerate(buttons):
        btn.rect = pygame.Rect(current_x, 620, widths[i], 55)
        current_x += widths[i] + spacing

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
                    elif selected == 1:
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
        prompt_text = "[ENTER] START GAME"
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
        draw_outlined_text(screen, "ENTER: CONFIRM", font_tiny, GRAY, WIDTH // 2, HEIGHT - 22)

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
    """Matchmaking screen — connects to server and waits for opponent."""
    import random
    import string

    state_timer = 0
    pulse_timer = 0
    teammate_found = False
    transition = ScreenTransition()
    done = [False]

    # Networking
    net = None
    connection_status = ""
    is_joiner = False
    solo_mode = False
    input_text = ""
    connect_failed = False
    reveal_timer = 0.0

    state = "menu"  # menu, create_wait, join_input, join_wait

    menu_buttons = [
        MenuButton("CREATE ROOM", WIDTH // 2, 240, 400, 60),
        MenuButton("JOIN ROOM", WIDTH // 2, 330, 400, 60),
        MenuButton("CONTINUE SOLO (F1)", WIDTH // 2, 420, 400, 60),
    ]
    menu_selected = 0
    menu_buttons[menu_selected].selected = True

    running = True
    while running:
        await asyncio.sleep(0)  # For async loop to breathe
        dt = clock.tick(FPS) / 1000.0
        pulse_timer += dt
        state_timer += dt
        transition.update(dt)

        # Handle joining connection below event loop so we don't block during event polling
        if state == "join_wait" and not teammate_found:
            room_key = input_text.strip()
            # Phase 1: Localhost (if testing or server is local)
            net_temp = NetworkClient(host="localhost", port=5555)
            connected = net_temp.connect(room_key=room_key)
            
            # Phase 2: LAN
            if not connected:
                host_ip = await find_lan_host(room_key)
                if host_ip and host_ip != "127.0.0.1":
                    net_temp = NetworkClient(host=host_ip, port=5555)
                    connected = net_temp.connect(room_key=room_key)

            if connected:
                net = net_temp
                connection_status = "CONNECTED!"
                state = "create_wait"
            else:
                connection_status = "FAILED TO FIND ROOM"
                connect_failed = True
                state = "join_input"

        # Check if server has paired us
        if net and net.connected and net.room_full and not teammate_found:
            teammate_found = True
            is_joiner = (net.player_id == 1)
            reveal_timer = 0.0
            play_ui_sfx("ui_confirm")

        if teammate_found:
            reveal_timer += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT", False, None, False
            elif event.type == pygame.KEYDOWN and not transition.active:
                if teammate_found:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        play_ui_sfx("ui_confirm")
                        done[0] = True
                        transition.start(lambda: None)
                elif state == "menu":
                    if event.key == pygame.K_ESCAPE:
                        return "QUIT", False, None, False
                    elif event.key == pygame.K_F1:
                        play_ui_sfx("ui_confirm")
                        return "LOBBY", False, None, True
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        menu_buttons[menu_selected].selected = False
                        menu_selected = (menu_selected - 1) % len(menu_buttons)
                        menu_buttons[menu_selected].selected = True
                        play_ui_sfx("ui_move")
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        menu_buttons[menu_selected].selected = False
                        menu_selected = (menu_selected + 1) % len(menu_buttons)
                        menu_buttons[menu_selected].selected = True
                        play_ui_sfx("ui_move")
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        play_ui_sfx("ui_confirm")
                        if menu_selected == 0:  # CREATE ROOM
                            rk = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
                            input_text = f"RM-{rk}"
                            try:
                                server.start_server_daemon(port=5555)
                                server.start_lan_broadcaster(input_text, port=5556)
                                # wait slightly for server bind
                                net_temp = NetworkClient(host="localhost", port=5555)
                                if net_temp.connect(room_key=input_text):
                                    net = net_temp
                                    connection_status = ""
                                    state = "create_wait"
                                else:
                                    connection_status = "FAILED TO CONNECT TO LOCAL SERVER"
                                    state = "join_input"
                            except Exception as e:
                                print("Failed to host:", e)
                                connection_status = "FAILED TO HOST"
                                connect_failed = True
                                state = "join_input"
                        elif menu_selected == 1:  # JOIN ROOM
                            input_text = ""
                            connection_status = "ENTER ROOM KEY"
                            connect_failed = False
                            state = "join_input"
                        elif menu_selected == 2:  # CONTINUE SOLO
                            return "LOBBY", False, None, True
                elif state == "join_input":
                    if event.key == pygame.K_ESCAPE:
                        state = "menu"
                        play_ui_sfx("ui_exit")
                    elif event.key == pygame.K_F1:
                        play_ui_sfx("ui_confirm")
                        return "LOBBY", False, None, True
                    elif event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                        play_ui_sfx("ui_move")
                    elif event.key == pygame.K_RETURN:
                        if input_text.strip():
                            input_text = input_text.strip().upper()
                            if not input_text.startswith("RM-"):
                                input_text = "RM-" + input_text
                            state = "join_wait"
                            connection_status = f"SEARCHING FOR ROOM {input_text}..."
                            # Processed below event loop
                    elif event.unicode and len(input_text) < 15 and event.unicode.isprintable():
                        input_text += event.unicode.upper()
                        play_ui_sfx("ui_move")
                elif state == "create_wait":
                    if event.key == pygame.K_ESCAPE:
                        # Cannot cancel easily since server is daemonized, but we can back out
                        net = None
                        state = "menu"
                        play_ui_sfx("ui_exit")

        # Draw Frame
        frame_idx = int(pulse_timer * 15) % len(anim_background_frames)
        screen.blit(anim_background_frames[frame_idx], (0, 0))

        if not teammate_found:
            pulse_alpha = int((math.sin(pulse_timer * 6) * 0.3 + 0.7) * 255)

            if state == "menu":
                match_txt = "MULTIPLAYER MATCHMAKING"
                for btn in menu_buttons:
                    btn.draw(screen, pulse_timer)
                draw_outlined_text(screen, "ENTER: SELECT   ESC: BACK", font_tiny, GRAY, WIDTH // 2, HEIGHT - 50)
            
            elif state in ("join_input", "join_wait"):
                match_txt = "JOIN ROOM"
                draw_outlined_text(screen, "ROOM KEY:", font_label, LIGHT_BLUE, WIDTH // 2, 200)
                field_w, field_h = 400, 60
                field_rect = (WIDTH // 2 - field_w // 2, 230, field_w, field_h)
                border_c = RED if connect_failed else CYAN
                draw_panel(screen, field_rect, alpha=150, border_color=border_c)

                cursor = "|" if int(pulse_timer * 2) % 2 == 0 and state == "join_input" else ""
                draw_outlined_text(screen, input_text + cursor, font_subheader, YELLOW, WIDTH // 2, 260)
                
                status_color = RED if connect_failed else WHITE
                draw_outlined_text(screen, connection_status, font_small, status_color, WIDTH // 2, 310)
                
                if state == "join_input":
                    draw_outlined_text(screen, "PRESS ENTER TO CONNECT", font_tiny, GRAY, WIDTH // 2, 350)
                    draw_outlined_text(screen, "PRESS ESC TO GO BACK", font_tiny, GRAY, WIDTH // 2, 380)

            elif state == "create_wait":
                match_txt = "WAITING FOR OPPONENT..."
                dots = "." * (int(pulse_timer * 2) % 4)
                draw_outlined_text(screen, f"ROOM KEY: {input_text}{dots}", font_label, GREEN, WIDTH // 2, 220)
                draw_outlined_text(screen, "SHARE THIS KEY WITH YOUR OPPONENT", font_small, LIGHT_BLUE, WIDTH // 2, 270)
                draw_outlined_text(screen, connection_status, font_small, WHITE, WIDTH // 2, 310)
                draw_outlined_text(screen, "PRESS ESC TO CANCEL", font_tiny, GRAY, WIDTH // 2, 360)
        else:
            pulse_alpha = 255
            match_txt = "TEAMMATE FOUND!"
            role_txt = "YOU ARE RAVEN (P2)" if is_joiner else "YOU ARE LUNA (P1)"
            draw_outlined_text(screen, role_txt, font_label, GREEN if is_joiner else CYAN, WIDTH // 2, 220)

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
            progress = min(1.0, reveal_timer * 1.6)
            alpha = int(progress * 255)
            pop_offset = int((1.0 - progress) * 80)

            if luna_portrait:
                luna_p = luna_portrait.copy()
                luna_p.set_alpha(alpha)
                lx = 400 - luna_p.get_width() // 2
                ly = 525 - luna_p.get_height() // 2 + pop_offset
                screen.blit(luna_p, (lx, ly))

            if raven_portrait:
                raven_p = raven_portrait.copy()
                raven_p.set_alpha(alpha)
                rx = 880 - raven_p.get_width() // 2
                ry = 525 - raven_p.get_height() // 2 + pop_offset
                screen.blit(raven_p, (rx, ry))

            continue_btn = MenuButton("CONTINUE TO LOBBY", WIDTH // 2, 600, 360, 60, selected=True)
            continue_btn.draw(screen, pulse_timer)

        transition.draw(screen)
        pygame.display.flip()

        if done[0] and not transition.active:
            return "LOBBY", is_joiner, net, solo_mode

    return "QUIT", False, None, False


# ── Screen: Battle Lobby (Weapon Select + Arena Vote) ──────────────────────

async def screen_battle_lobby(is_joiner: bool = False, net=None):
    """Combined weapon select + arena vote screen. Returns selections."""
    # Player roles: Host = Luna (P1, player_id 0), Joiner = Raven (P2, player_id 1)
    # Each player only selects their OWN weapon.

    # Player displays (2 players)
    p1_display = PlayerDisplay(0, 40, 100, 520, 200)
    p2_display = PlayerDisplay(1, 40, 320, 520, 200)

    my_display = p2_display if is_joiner else p1_display
    opp_display = p1_display if is_joiner else p2_display

    # Arena cards
    arenas = []
    arena_start_x = 840
    arena_start_y = 100
    card_w, card_h = 190, 140
    gap = 15
    for i, arena_info in enumerate(ArenaCard.ARENAS):
        row = i // 2
        col = i % 2
        ax = arena_start_x + col * (card_w + gap)
        ay = arena_start_y + row * (card_h + gap)
        arenas.append(ArenaCard(arena_info, ax, ay, card_w, card_h))

    # Selection state — only pick OWN weapon, then arena, then confirm
    focus = "my_weapon"  # my_weapon → arena → confirm
    my_weapon_idx = 0
    opp_weapon_idx = 0   # received from opponent
    arena_idx = 0
    arenas[0].selected = True

    deploy_timer = 60.0
    vote_count = 0
    total_votes = 2

    pulse_timer = 0
    sync_timer = 0.0
    transition = ScreenTransition()
    result = [None]
    confirm_ready = False
    waiting_for_opponent = False

    def send_selection():
        """Send current selections to server."""
        if net and net.connected:
            weapon_names = list(WeaponCard.WEAPONS.keys())
            weapon_types = [WeaponCard.WEAPONS[w]["type"] for w in weapon_names]
            net.send_lobby_selection({
                "weapon": weapon_types[my_weapon_idx],
                "arena_id": arenas[arena_idx].arena_id,
                "arena_name": arenas[arena_idx].name,
                "timer": deploy_timer,
            })

    running = True
    while running:
        await asyncio.sleep(0)
        dt = clock.tick(FPS) / 1000.0
        pulse_timer += dt
        deploy_timer -= dt
        sync_timer += dt
        transition.update(dt)

        # Host sends periodic sync
        if net and net.connected and not is_joiner:
            if sync_timer >= 1.0:
                sync_timer = 0.0
                send_selection()

        # Poll opponent lobby data
        if net and net.connected:
            opp_lobby = net.get_opponent_lobby()
            if opp_lobby:
                # Update opponent weapon display
                weapon_names = list(WeaponCard.WEAPONS.keys())
                weapon_types = [WeaponCard.WEAPONS[w]["type"] for w in weapon_names]
                opp_wep = opp_lobby.get("weapon", "")
                if opp_wep in weapon_types:
                    opp_weapon_idx = weapon_types.index(opp_wep)
                    opp_display.select_weapon(opp_weapon_idx)
                
                # Update opponent arena vote
                opp_arena_id = opp_lobby.get("arena_id")
                for a in arenas:
                    a.opp_selected = (a.arena_id == opp_arena_id)
                
                # Sync deploy timer if we are joiner
                if is_joiner and "timer" in opp_lobby:
                    if abs(deploy_timer - opp_lobby["timer"]) > 1.5:
                        deploy_timer = opp_lobby["timer"]

            # Check if opponent is ready
            if net.opponent_ready or net.all_ready:
                opp_display.confirmed = True

            # Auto-ready when timer runs out
            if deploy_timer <= 0 and not confirm_ready:
                confirm_ready = True
                focus = "confirm"
                if net and net.connected:
                    net.send_ready()
                    waiting_for_opponent = True
                play_ui_sfx("ui_confirm")

            start_condition = False
            if net and net.connected:
                start_condition = net.all_ready and confirm_ready
            else:
                start_condition = confirm_ready

            # Check if both ready -> start
            if start_condition or (deploy_timer <= 0 and opp_display.confirmed):
                if result[0] is None:
                    weapon_names = list(WeaponCard.WEAPONS.keys())
                    weapon_types = [WeaponCard.WEAPONS[w]["type"] for w in weapon_names]
                    my_weapon = weapon_types[my_weapon_idx]
                    opp_weapon = opp_lobby.get("weapon", "sword") if opp_lobby else "sword"

                    if is_joiner:
                        p1w, p2w = opp_weapon, my_weapon
                        # Host wins arena tie-breaker, so use opponent's arena
                        final_arena_id = opp_lobby.get("arena_id", arenas[arena_idx].arena_id)
                        final_arena_name = opp_lobby.get("arena_name", arenas[arena_idx].name)
                    else:
                        p1w, p2w = my_weapon, opp_weapon
                        # We are host, we win tie-breaker, use our arena
                        final_arena_id = arenas[arena_idx].arena_id
                        final_arena_name = arenas[arena_idx].name

                    result[0] = {
                        "p1_weapon": p1w,
                        "p2_weapon": p2w,
                        "arena_id": final_arena_id,
                        "arena_name": final_arena_name,
                    }
                    if not transition.active:
                        transition.start(lambda: None)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None, net
            elif event.type == pygame.KEYDOWN and not transition.active:
                if focus == "my_weapon":
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        my_weapon_idx = (my_weapon_idx - 1) % 3
                        my_display.select_weapon(my_weapon_idx)
                        play_ui_sfx("ui_move")
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        my_weapon_idx = (my_weapon_idx + 1) % 3
                        my_display.select_weapon(my_weapon_idx)
                        play_ui_sfx("ui_move")
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        my_display.confirmed = True
                        play_ui_sfx("ui_confirm")
                        send_selection()
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
                        arenas[arena_idx].votes += 1
                        vote_count += 1
                        play_ui_sfx("ui_confirm")
                        focus = "confirm"
                        confirm_ready = True

                elif focus == "confirm":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        weapon_names = list(WeaponCard.WEAPONS.keys())
                        weapon_types = [WeaponCard.WEAPONS[w]["type"] for w in weapon_names]
                        my_weapon = weapon_types[my_weapon_idx]

                        send_selection()

                        if net and net.connected:
                            # Signal ready and wait for opponent
                            net.send_ready()
                            waiting_for_opponent = True
                            play_ui_sfx("ui_confirm")
                        else:
                            # Offline mode — just start
                            if result[0] is None:
                                opp_weapon = weapon_types[opp_weapon_idx]
                                result[0] = {
                                    "p1_weapon": my_weapon,
                                    "p2_weapon": opp_weapon,
                                    "arena_id": arenas[arena_idx].arena_id,
                                    "arena_name": arenas[arena_idx].name,
                                }
                                play_ui_sfx("ui_confirm")
                                transition.start(lambda: None)

                # Back button (Escape)
                if event.key == pygame.K_ESCAPE:
                    play_ui_sfx("ui_back")
                    if focus == "arena":
                        my_display.confirmed = False
                        focus = "my_weapon"
                    elif focus == "confirm":
                        focus = "arena"

        # ── Draw ──
        frame_idx = int(pulse_timer * 15) % len(anim_background_frames)
        screen.blit(anim_background_frames[frame_idx], (0, 0))

        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 100))
        screen.blit(dim, (0, 0))

        # Top bar
        draw_panel(screen, (0, 0, WIDTH, 50), alpha=230, border_color=(60, 70, 90))
        draw_outlined_text(screen, "GAUNTLET GALAXY - BATTLE LOBBY", font_label, LIGHT_BLUE, 220, 25,
                           anchor="center")

        # Deploy timer
        deploy_min = int(max(0, deploy_timer)) // 60
        deploy_sec = int(max(0, deploy_timer)) % 60
        timer_color = WHITE if deploy_timer > 15 else RED
        draw_outlined_text(screen, f"DEPLOY IN: {deploy_min}:{deploy_sec:02d}", font_label, timer_color,
                           WIDTH - 120, 25)

        # Players ready count
        ready_count = sum([my_display.confirmed, opp_display.confirmed])
        draw_outlined_text(screen, f"PLAYERS READY: {ready_count}/2", font_small, LIGHT_BLUE,
                           WIDTH // 2, 70)

        # Left side: Team loadout
        draw_outlined_text(screen, "TEAM LOADOUT", font_subheader, WHITE, 300, 78, outline_width=3)
        p1_display.draw(screen, pulse_timer)
        p2_display.draw(screen, pulse_timer)

        # "YOU" indicator
        you_y = my_display.rect.y + my_display.rect.h // 2
        draw_outlined_text(screen, "◄ YOU", font_small, YELLOW,
                           my_display.rect.right + 30, you_y)

        # Right side: Stage select
        draw_outlined_text(screen, "STAGE SELECT", font_subheader, WHITE, 1040, 78, outline_width=3)
        for arena in arenas:
            arena.draw(screen, pulse_timer)

        # Vote info
        draw_outlined_text(screen, f"VOTES CAST: {vote_count} / {total_votes}", font_small, LIGHT_BLUE,
                           935, HEIGHT - 100)
        draw_outlined_text(screen, f"VOTE ENDS: 0:{int(max(0, deploy_timer)):02d}", font_small, ORANGE,
                           1140, HEIGHT - 100)

        # Bottom bar
        draw_panel(screen, (0, HEIGHT - 70, WIDTH, 70), alpha=230, border_color=(60, 70, 90))
        draw_outlined_text(screen, "ENTER: CONFIRM", font_tiny, GRAY, 80, HEIGHT - 40)
        draw_outlined_text(screen, "ESC: BACK", font_tiny, GRAY, 200, HEIGHT - 40)

        # Big confirm / waiting button
        if waiting_for_opponent and not (net and net.all_ready):
            btn_rect = pygame.Rect(WIDTH // 2 - 200, HEIGHT - 65, 400, 55)
            pygame.draw.rect(screen, (80, 80, 120), btn_rect, border_radius=6)
            pygame.draw.rect(screen, LIGHT_BLUE, btn_rect, 3, border_radius=6)
            dots = "." * (int(pulse_timer * 2) % 4)
            draw_outlined_text(screen, f"WAITING FOR OPPONENT{dots}", font_button, WHITE,
                               WIDTH // 2, HEIGHT - 38)
        elif confirm_ready:
            pulse = math.sin(pulse_timer * 5) * 0.5 + 0.5
            btn_color = (40 + int(pulse * 30), 180 + int(pulse * 40), 80 + int(pulse * 30))
            btn_rect = pygame.Rect(WIDTH // 2 - 200, HEIGHT - 65, 400, 55)
            pygame.draw.rect(screen, btn_color, btn_rect, border_radius=6)
            pygame.draw.rect(screen, WHITE, btn_rect, 3, border_radius=6)
            draw_outlined_text(screen, "CONFIRM SELECTIONS", font_button, WHITE,
                               WIDTH // 2, HEIGHT - 38)

        # Focus indicator
        focus_labels = {
            "my_weapon": "Select YOUR weapon (← → then ENTER)",
            "arena": "Vote for an arena (← → ↑ ↓ then ENTER)",
            "confirm": "Press ENTER to ready up!",
        }
        draw_outlined_text(screen, focus_labels.get(focus, ""), font_small,
                           YELLOW, WIDTH // 2, HEIGHT - 80)

        draw_outlined_text(screen, "ESC: BACK", font_tiny, GRAY, WIDTH - 80, HEIGHT - 40)

        transition.draw(screen)
        pygame.display.flip()

        if result[0] and not transition.active:
            return result[0], net

    return None, net


# ── Main Flow ──────────────────────────────────────────────────────────────

async def main_menu():
    """Complete game flow: Start Menu → Matchmaking → Lobby → Game."""
    while True:
        audio_manager.play_music("menu_theme_1")

        # STEP 1: Start Menu
        action = await screen_start_menu()
        if action == "QUIT":
            break

        if action == "CREDITS":
            await screen_credits()
            continue

        # STEP 2: Matchmaking (connects to server)
        action, is_joiner, net, solo_mode = await screen_matchmaking()
        if action == "QUIT":
            break

        # STEP 3: Battle Lobby (weapon select + arena vote)
        lobby_result = await screen_battle_lobby(is_joiner, net=net)
        if lobby_result is None or lobby_result[0] is None:
            break
        selections, net = lobby_result

        print(f"Game starting with selections: {selections}")

        # STEP 4: Launch the actual game with the selections
        try:
            from src.entities.sword_fighter import SwordFighter
            from src.entities.bow_fighter import BowFighter
            from src.entities.hammer_fighter import HammerFighter
            from src.game.game import Game
            import random

            fighter_classes = {
                "sword": SwordFighter,
                "bow": BowFighter,
                "hammer": HammerFighter,
            }

            # Determine local/remote based on player role
            if solo_mode:
                local_cls = fighter_classes[selections["p1_weapon"]]
                remote_cls = random.choice(list(fighter_classes.values()))
            elif is_joiner:
                # Joiner is P2 — local fighter uses P2 weapon, remote uses P1 weapon
                local_cls = fighter_classes[selections["p2_weapon"]]
                remote_cls = fighter_classes[selections["p1_weapon"]]
            else:
                # Host is P1 — local fighter uses P1 weapon, remote uses P2 weapon
                local_cls = fighter_classes[selections["p1_weapon"]]
                remote_cls = fighter_classes[selections["p2_weapon"]]

            game = Game(
                arena_id=selections["arena_id"],
                fighter_cls_local=local_cls,
                fighter_cls_remote=remote_cls,
                net=net,
                audio_manager=audio_manager,
                local_player_id=1 if is_joiner else 0,
                enable_enemy_ai=solo_mode,
            )

            # Configure the HUD arena name from lobby selection
            game.hud.arena_name = selections["arena_name"].upper()

            await game.run()

        except ImportError as e:
            print(f"Could not import game modules: {e}")
            print("Game would start with:", selections)
        finally:
            if 'net' in locals() and net:
                net.connected = False
                if net.sock:
                    try: net.sock.close()
                    except: pass
            server.stop_server_daemon()

    pygame.quit()
    sys.exit()


async def main_menu_async():
    await main_menu()


if __name__ == "__main__":
    asyncio.run(main_menu())
