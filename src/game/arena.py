import pygame


TILE_SIZE = 48
TILE_COLOR = (80, 90, 110)


class Tile:
    """A single solid platform tile."""

    def __init__(self, x: int, y: int, w: int = TILE_SIZE, h: int = TILE_SIZE, color: tuple = TILE_COLOR):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color

    def draw(self, surface: pygame.Surface, cam_x: int = 0, cam_y: int = 0) -> None:
        rx = self.rect.x - cam_x
        ry = self.rect.y - cam_y
        pygame.draw.rect(surface, self.color, (rx, ry, self.rect.width, self.rect.height), border_radius=4)
        # Subtle top highlight
        pygame.draw.rect(
            surface,
            tuple(min(c + 40, 255) for c in self.color),
            (rx, ry, self.rect.width, 4),
            border_radius=2,
        )


def build_arena(arena_id: int = 0) -> list[Tile]:
    """Return a list of Tiles for the chosen arena."""
    tiles = []

    # Common helper to add a platform of tiles
    def add_platform(x_start: int, y_pos: int, num_tiles: int):
        for i in range(num_tiles):
            tiles.append(Tile(x_start + i * TILE_SIZE, y_pos))

    # Layout based on visual analysis of assets/maps/map_*.png
    # Most maps (0, 1, 2, 4, 5) use the "Tournament" layout (Main + 4 slots)
    # Gravity Well (3) uses a single large platform.
    if arena_id == 3:  # Gravity Well: Single large platform
        add_platform(240, 560, 17)
    else:
        # Main large platform (centered)
        add_platform(240, 560, 17)

        # Side platforms
        # Left side
        add_platform(120, 410, 4)
        add_platform(120, 260, 4)

        # Right side
        add_platform(968, 410, 4)
        add_platform(968, 260, 4)

    return tiles
