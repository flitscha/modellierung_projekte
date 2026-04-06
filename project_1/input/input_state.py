from dataclasses import dataclass, field


@dataclass
class InputState:
    """snapshot of what the user did this frame"""

    # raw pygame events
    events: list

    # App
    quit: bool = False

    # One-shot key presses
    escape_pressed: bool = False
    a_pressed: bool = False
    r_pressed: bool = False
    h_pressed: bool = False
    c_pressed: bool = False
    plus_pressed: bool = False
    minus_pressed: bool = False

    # held keys
    thrust_up: bool = False
    thrust_down: bool = False

    # mouse / camera
    scroll_delta: int  = 0
    scroll_pos: tuple[int, int] = field(default_factory=lambda: (0, 0))
    pan_started: bool = False
    pan_ended: bool = False
    pan_delta: tuple[int, int] = field(default_factory=lambda: (0, 0))
    mouse_pos: tuple[int, int] = field(default_factory=lambda: (0, 0))

    # raw mouse-events used in the Orbit-editor
    mouse_button_down: bool = False
    mouse_button_up: bool = False
    mouse_moved: bool = False

