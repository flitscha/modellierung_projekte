TRAIL_MAX_LENGTH = 500

# simulation speed (the BASE_SIMULATION_SPEED gets multiplied with the step-values)
BASE_SIMULATION_SPEED = 300.0
SIMULATION_SPEED_STEPS = [0.1, 0.5, 1, 2, 5, 10, 50, 100]
DEFAULT_SIMULATION_SPEED_INDEX = 2

# camera settings
DEFAULT_ZOOM = 1e-5  # screen-pixels per metre
MIN_ZOOM = 1e-6
MAX_ZOOM = 1e-2
ZOOM_FACTOR = 1.15  # multiplier per scroll-tick

# Colour palette
COLOR_BG = (5, 5, 20)
COLOR_PLANET = (0, 100, 255)
COLOR_SHIP = (255, 255, 255)
COLOR_TARGET_ORBIT = (80, 220, 120)
COLOR_START_ORBIT = (80, 140, 255)
COLOR_TRAIL_HEAD = (255, 220, 100)
COLOR_TRAIL_TAIL = (60, 60, 60)

