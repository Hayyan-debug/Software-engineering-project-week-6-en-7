import pygame


class SpritesheetHandler:
    def __init__(self, path: str, cols: int = 6, rows: int = 3):
        try:
            self.sheet = pygame.image.load(path).convert_alpha()
            self.sheet.set_colorkey((255, 255, 255))
        except Exception:
            # Fallback to a tiny blank surface if asset missing
            self.sheet = pygame.Surface((1, 1), pygame.SRCALPHA)

        self.w, self.h = self.sheet.get_size()
        self.cols, self.rows = cols, rows
        self.frame_w = self.w // cols
        self.frame_h = self.h // rows
        self.frames = []

        for r in range(rows):
            for c in range(cols):
                rect = pygame.Rect(c * self.frame_w, r * self.frame_h, self.frame_w, self.frame_h)
                # Ensure we don't go out of bounds if sheet isn't exact
                if rect.right <= self.w and rect.bottom <= self.h:
                    self.frames.append(self.sheet.subsurface(rect))
                else:
                    self.frames.append(pygame.Surface((self.frame_w, self.frame_h), pygame.SRCALPHA))

    def get_frame(self, index: int) -> pygame.Surface:
        if 0 <= index < len(self.frames):
            return self.frames[index]
        return self.frames[0]
