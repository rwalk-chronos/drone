"""Configuration for the non-destructive drone response timing simulator."""

WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 760
FPS = 30
DT = 0.1

SCALE = 0.38
ORIGIN_X = WINDOW_WIDTH // 2
ORIGIN_Y = WINDOW_HEIGHT - 90
VECTOR_SECONDS = 5.0

LAUNCH_DELAY = 2.0
SUCCESS_RADIUS = 40.0
PROTECTED_LINE_Y = 0.0
DETECTION_RANGE = 1100.0
INITIAL_INTERCEPTOR_SPEED = 60.0
INTERCEPTORS_PER_BALLOON = 2

TARGET_TEMPLATES = [
    {"x": -520.0, "y": 1500.0, "vx": 7.0, "vy": -24.0},
    {"x": -260.0, "y": 1420.0, "vx": 4.0, "vy": -23.0},
    {"x": 0.0, "y": 1560.0, "vx": 0.0, "vy": -26.0},
    {"x": 280.0, "y": 1460.0, "vx": -4.0, "vy": -23.0},
    {"x": 520.0, "y": 1520.0, "vx": -7.0, "vy": -24.0},
]

BALLOON_TEMPLATES = [
    {"id": 1, "x": -500.0, "y": 0.0},
    {"id": 2, "x": 0.0, "y": 0.0},
    {"id": 3, "x": 500.0, "y": 0.0},
]
