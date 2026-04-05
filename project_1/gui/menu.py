import pygame
from enum import Enum, auto


# Colours
COLOR_OVERLAY = (0, 0, 0, 160)  # semi-transparent black
COLOR_TITLE = (255, 255, 255)
COLOR_ITEM_DEFAULT = (180, 180, 180)
COLOR_ITEM_HOVER = (255, 220, 100)
COLOR_ITEM_BORDER = (60, 60, 100)

# Layout
TITLE_FONT_SIZE = 32
ITEM_FONT_SIZE = 22
ITEM_PADDING = 14  # vertical padding inside each button
ITEM_WIDTH = 260
ITEM_SPACING = 8  # gap between buttons


class MenuAction(Enum):
    NONE = auto()
    RESUME = auto()
    EDIT_ORBITS = auto()
    RESET = auto()
    QUIT = auto()


# Each entry: (label, action)
MENU_ITEMS = [
    ("Resume", MenuAction.RESUME),
    ("Edit Orbits", MenuAction.EDIT_ORBITS),
    ("Reset", MenuAction.RESET),
    ("Quit", MenuAction.QUIT),
]


class Menu:
    """
    Menu shown when the user presses Escape.

    Usage
    -----
        action = menu.handle_events(events)
        if action == MenuAction.RESUME:
            ...
        menu.draw()

    The menu draws a dark overlay over the simulation, so the simulation
    should still be rendered underneath each frame.
    """

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.title_font = pygame.font.SysFont("monospace", TITLE_FONT_SIZE, bold=True)
        self.item_font = pygame.font.SysFont("monospace", ITEM_FONT_SIZE)
        self._hovered = None  # index of currently hovered item


    def handle_events(self, events: list[pygame.event.Event]) -> MenuAction:
        """
        Process events and return the action the user triggered.
        Returns MenuAction.NONE if nothing was selected.
        """
        mouse_pos = pygame.mouse.get_pos()
        self._hovered = self._item_at(mouse_pos)

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return MenuAction.RESUME

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._hovered is not None:
                    return MENU_ITEMS[self._hovered][1]

        return MenuAction.NONE

    def draw(self):
        w, h = self.screen.get_size()

        # Dark overlay
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill(COLOR_OVERLAY)
        self.screen.blit(overlay, (0, 0))

        # Layout: center everything vertically
        item_h = self.item_font.get_height() + ITEM_PADDING * 2
        total_h = (item_h + ITEM_SPACING) * len(MENU_ITEMS) - ITEM_SPACING
        title_surf = self.title_font.render("MENU", True, COLOR_TITLE)
        title_gap = 40   # space between title and first button

        start_y = h // 2 - (total_h + title_surf.get_height() + title_gap) // 2

        # Title
        self.screen.blit(title_surf, (w // 2 - title_surf.get_width() // 2, start_y))
        y = start_y + title_surf.get_height() + title_gap

        # Buttons
        for i, (label, _) in enumerate(MENU_ITEMS):
            hovered = (self._hovered == i)
            self._draw_item(label, i, y, w, item_h, hovered)
            y += item_h + ITEM_SPACING


    def _item_rect(self, index: int, y: int, w: int, item_h: int) -> pygame.Rect:
        x = w // 2 - ITEM_WIDTH // 2
        return pygame.Rect(x, y, ITEM_WIDTH, item_h)

    def _draw_item(self, label: str, index: int, y: int, w: int, item_h: int, hovered: bool):
        rect = self._item_rect(index, y, w, item_h)
        color = COLOR_ITEM_HOVER if hovered else COLOR_ITEM_DEFAULT

        # Background + border
        bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        bg.fill((30, 30, 60, 200))
        self.screen.blit(bg, rect.topleft)
        pygame.draw.rect(self.screen, COLOR_ITEM_BORDER, rect, 1)

        # Label
        surf = self.item_font.render(label, True, color)
        self.screen.blit(surf, (
            rect.centerx - surf.get_width()  // 2,
            rect.centery - surf.get_height() // 2,
        ))

    def _item_at(self, mouse_pos) -> int | None:
        """Return the index of the menu item under the mouse, or None."""
        w, h = self.screen.get_size()
        item_h = self.item_font.get_height() + ITEM_PADDING * 2

        title_surf = self.title_font.render("MENU", True, COLOR_TITLE)
        title_gap = 40
        total_h = (item_h + ITEM_SPACING) * len(MENU_ITEMS) - ITEM_SPACING
        start_y = h // 2 - (total_h + title_surf.get_height() + title_gap) // 2
        y = start_y + title_surf.get_height() + title_gap

        for i in range(len(MENU_ITEMS)):
            if self._item_rect(i, y, w, item_h).collidepoint(mouse_pos):
                return i
            y += item_h + ITEM_SPACING

        return None

