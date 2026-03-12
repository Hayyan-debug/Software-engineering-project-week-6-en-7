import pygame
import sys
import math
import os

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
BG_COLOR = (20, 20, 35)

# Setup screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Gauntlet Galaxy - Start Menu")
clock = pygame.time.Clock()

def load_image(filename):
    path = os.path.join("assets", filename)
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, (WIDTH, HEIGHT))
    except Exception as e:
        print(f"Could not load {path}: {e}")
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        if "platforms" not in filename:
            surf.fill(BG_COLOR)
        return surf

# Load background
background_img = load_image("background.png").convert()
looking_bg = load_image("lookingforteammate.png").convert()
looking_platforms = load_image("lookingforteammateplatforms.png")

# Fonts
try:
    font_title_large = pygame.font.SysFont("impact", 130)
    font_title_small = pygame.font.SysFont("impact", 110)
    font_prompt = pygame.font.SysFont("impact", 45)
    font_button = pygame.font.SysFont("impact", 35)
    font_small = pygame.font.SysFont("consolas", 20, bold=True)
except:
    font_title_large = pygame.font.Font(None, 140)
    font_title_small = pygame.font.Font(None, 120)
    font_prompt = pygame.font.Font(None, 50)
    font_button = pygame.font.Font(None, 40)
    font_small = pygame.font.Font(None, 24)

def draw_text_with_outlines(surface, text, font, font_color, inner_outline, outer_outline, x, y):
    text_surf = font.render(text, True, font_color)
    inner_surf = font.render(text, True, inner_outline)
    outer_surf = font.render(text, True, outer_outline)
    
    # Outer outline
    for ox in range(-5, 6):
        for oy in range(-5, 6):
            if abs(ox) + abs(oy) > 6: continue
            rect = outer_surf.get_rect(center=(x + ox, y + oy + 3))
            surface.blit(outer_surf, rect)
            
    # Inner outline
    for ox in range(-2, 3):
        for oy in range(-2, 3):
            if abs(ox) + abs(oy) > 2: continue
            rect = inner_surf.get_rect(center=(x + ox, y + oy))
            surface.blit(inner_surf, rect)
            
    rect = text_surf.get_rect(center=(x, y))
    surface.blit(text_surf, rect)


class Button:
    def __init__(self, text, x, y, width, height, selected=True):
        self.text = text
        self.rect = pygame.Rect(x - width//2, y - height//2, width, height)
        self.selected = selected

    def draw(self, surface, time):
        pulse = math.sin(time * 5) * 0.5 + 0.5
        
        if self.selected:
            bg_color = (15 + int(pulse*10), 35 + int(pulse*15), 65 + int(pulse*25))
            border_color = (130 + int(pulse*60), 220, 255)
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
        
        # Text and Drop Shadow
        text_shadow = font_button.render(self.text, True, BLACK)
        text_surf = font_button.render(self.text, True, text_color)
        
        text_x = self.rect.centerx
        if self.selected: text_x += 15
        
        shadow_rect_text = text_shadow.get_rect(center=(text_x + 2, self.rect.centery + 2))
        surface.blit(text_shadow, shadow_rect_text)
        
        text_rect = text_surf.get_rect(center=(text_x, self.rect.centery))
        
        if self.selected:
            # Render arrows pointing right
            arrow = font_button.render(">>", True, YELLOW)
            arrow_rect = arrow.get_rect(midright=(text_rect.left - 10, text_rect.centery))
            
            arrow_shadow = font_button.render(">>", True, BLACK)
            arr_sh_rect = arrow_shadow.get_rect(midright=(text_rect.left - 10 + 2, text_rect.centery + 2))
            
            surface.blit(arrow_shadow, arr_sh_rect)
            surface.blit(arrow, arrow_rect)
            
        surface.blit(text_surf, text_rect)


def main_menu():
    state = "START"
    continue_btn = Button("CONTINUE TO GAME", WIDTH//2, 600, 340, 60, selected=True)
    
    pulse_timer = 0
    state_timer = 0
    teammate_found = False
    
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        pulse_timer += dt
        state_timer += dt
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if state == "START":
                    state = "MATCHMAKING"
                    state_timer = 0
                    teammate_found = False
                elif state == "MATCHMAKING" and teammate_found:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        print("Proceeding to actual game/character select...")
                        running = False
            
        if state == "START":
            screen.blit(background_img, (0, 0))
            
            version_surf = font_small.render("VERSION 1.0", True, (150, 160, 180))
            screen.blit(version_surf, (20, 20))
            
            draw_text_with_outlines(screen, "GAUNTLET", font_title_large, LIGHT_BLUE, WHITE, BLACK, WIDTH//2, 170)
            draw_text_with_outlines(screen, "GALAXY", font_title_small, ORANGE, YELLOW, BLACK, WIDTH//2, 280)
            
            pulse_alpha = int((math.sin(pulse_timer * 4) * 0.2 + 0.8) * 255)
            prompt_text = "[START] PRESS ANY BUTTON"
            prompt_surf = font_prompt.render(prompt_text, True, ORANGE)
            prompt_outline = font_prompt.render(prompt_text, True, BLACK)
            
            prompt_surf.set_alpha(pulse_alpha)
            prompt_outline.set_alpha(pulse_alpha)
            
            prompt_rect = prompt_surf.get_rect(center=(WIDTH//2, 530))
            screen.blit(prompt_outline, (prompt_rect.x + 3, prompt_rect.y + 3))
            screen.blit(prompt_surf, prompt_rect)
            
        elif state == "MATCHMAKING":
            # 2 seconds look time before teammate is found
            if state_timer > 2.0:
                teammate_found = True
            
            screen.blit(looking_bg, (0, 0))
            
            if not teammate_found:
                pulse_alpha = int((math.sin(pulse_timer * 6) * 0.3 + 0.7) * 255)
                match_txt = "SEARCHING FOR PLAYERS..."
            else:
                pulse_alpha = 255
                match_txt = "TEAMMATE FOUND!"
            
            # Draw beautiful header panel a bit faded
            panel_height = 80
            s = pygame.Surface((WIDTH, panel_height), pygame.SRCALPHA)
            s.fill((0, 0, 0, 160))
            screen.blit(s, (0, 40))
            
            # Glowing borders for panel
            pygame.draw.line(screen, LIGHT_BLUE, (0, 40), (WIDTH, 40), 2)
            pygame.draw.line(screen, LIGHT_BLUE, (0, 40 + panel_height), (WIDTH, 40 + panel_height), 2)
            
            color = LIGHT_BLUE if not teammate_found else ORANGE
            match_surf = font_prompt.render(match_txt, True, color)
            match_outline = font_prompt.render(match_txt, True, BLACK)
            
            match_surf.set_alpha(pulse_alpha)
            match_outline.set_alpha(pulse_alpha)
            
            match_rect = match_surf.get_rect(center=(WIDTH//2, 40 + panel_height//2))
            screen.blit(match_outline, (match_rect.x + 3, match_rect.y + 3))
            screen.blit(match_surf, match_rect)
            
            if teammate_found:
                # Slide/Fade in platforms
                alpha = min(255, int((state_timer - 2.0) * 255 * 2))
                looking_platforms.set_alpha(alpha)
                screen.blit(looking_platforms, (0, 0))
                
                # Draw the fancy continue button
                continue_btn.draw(screen, pulse_timer)
                
        pygame.display.flip()
        
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main_menu()
