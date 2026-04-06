from enum import Enum, auto

class AppState(Enum):
    PLAYING = auto()
    MENU = auto()
    EDITOR = auto()

class FlightMode(Enum):
    IDLE = auto()
    MANUAL = auto()
    AUTOPILOT = auto()
