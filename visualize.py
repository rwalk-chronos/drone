import math
import pygame

pygame.init()

WIDTH, HEIGHT = 900, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Drone Response Timing Simulation")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)

DT = 0.1
scale = 0.4
origin_x = WIDTH // 2
origin_y = HEIGHT - 80

INITIAL_TARGET = {"x": 0.0, "y": 1200.0, "vx": 0.0, "vy": -22.0}
INITIAL_INTERCEPTOR_SPEED = 60.0

balloons = [
    {"x": -400.0, "y": 0.0},
    {"x": 400.0, "y": 0.0},
]

launch_delay = 2.0
success_radius = 40.0
protected_line_y = 0.0
detection_range = 1000.0


def to_screen(x, y):
    return int(origin_x + x * scale), int(origin_y - y * scale)


def dist(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def nearest_balloon(target):
    return min(balloons, key=lambda node: dist(target, node))


def reset_simulation(message):
    target = dict(INITIAL_TARGET)
    selected_balloon = nearest_balloon(target)
    interceptor = {
        "x": selected_balloon["x"],
        "y": selected_balloon["y"],
        "speed": INITIAL_INTERCEPTOR_SPEED,
    }
    return {
        "target": target,
        "selected_balloon": selected_balloon,
        "interceptor": interceptor,
        "target_path": [],
        "interceptor_path": [],
        "launched": False,
        "success": False,
        "failed": False,
        "detected": False,
        "launch_time": None,
        "time": 0.0,
        "event_log": [message],
    }


state = reset_simulation("Simulation started")
paused = False
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            paused = not paused
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_UP:
            state["interceptor"]["speed"] += 5.0
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_DOWN:
            state["interceptor"]["speed"] = max(
                5.0, state["interceptor"]["speed"] - 5.0
            )
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            state = reset_simulation("Simulation restarted")
            paused = False

    target = state["target"]
    interceptor = state["interceptor"]
    selected_balloon = state["selected_balloon"]

    if not paused and not state["success"] and not state["failed"]:
        target["x"] += target["vx"] * DT
        target["y"] += target["vy"] * DT
        state["target_path"].append((target["x"], target["y"]))

        if not state["detected"]:
            in_range = [b for b in balloons if dist(target, b) <= detection_range]
            if in_range:
                state["detected"] = True
                state["selected_balloon"] = min(in_range, key=lambda b: dist(target, b))
                selected_balloon = state["selected_balloon"]
                interceptor["x"] = selected_balloon["x"]
                interceptor["y"] = selected_balloon["y"]
                state["launch_time"] = state["time"] + launch_delay
                state["event_log"].append(
                    f"Detected at {state['time']:.1f}s"
                )

        if (
            state["detected"]
            and not state["launched"]
            and state["launch_time"] is not None
            and state["time"] >= state["launch_time"]
        ):
            state["launched"] = True
            state["event_log"].append("Interceptor launched")

        if state["launched"]:
            dx = target["x"] - interceptor["x"]
            dy = target["y"] - interceptor["y"]
            distance_to_target = math.hypot(dx, dy)

            if distance_to_target > 0:
                interceptor["x"] += interceptor["speed"] * dx / distance_to_target * DT
                interceptor["y"] += interceptor["speed"] * dy / distance_to_target * DT

            state["interceptor_path"].append(
                (interceptor["x"], interceptor["y"])
            )

            if dist(target, interceptor) <= success_radius:
                state["success"] = True
                state["event_log"].append(
                    f"Intercept at {state['time']:.1f}s"
                )

        if target["y"] <= protected_line_y and not state["success"]:
            state["failed"] = True
            state["event_log"].append(
                f"Target crossed line at {state['time']:.1f}s"
            )

        state["time"] += DT

    screen.fill((245, 245, 245))

    for b in balloons:
        pygame.draw.circle(
            screen,
            (180, 180, 180),
            to_screen(b["x"], b["y"]),
            int(detection_range * scale),
            1,
        )

    pygame.draw.line(
        screen,
        (180, 180, 0),
        to_screen(-1000, protected_line_y),
        to_screen(1000, protected_line_y),
        3,
    )

    if len(state["target_path"]) > 1:
        pygame.draw.lines(
            screen,
            (200, 0, 0),
            False,
            [to_screen(x, y) for x, y in state["target_path"]],
            2,
        )

    if len(state["interceptor_path"]) > 1:
        pygame.draw.lines(
            screen,
            (0, 0, 200),
            False,
            [to_screen(x, y) for x, y in state["interceptor_path"]],
            2,
        )

    for index, b in enumerate(balloons, start=1):
        position = to_screen(b["x"], b["y"])
        active = b is state["selected_balloon"]
        radius = 13 if active else 10
        pygame.draw.circle(screen, (0, 160, 0), position, radius)
        label = f"Balloon {index}" + (" ACTIVE" if active else "")
        screen.blit(
            font.render(label, True, (0, 100, 0)),
            (position[0] + 12, position[1] - 10),
        )

    target_position = to_screen(target["x"], target["y"])
    pygame.draw.circle(screen, (220, 0, 0), target_position, 8)
    screen.blit(
        font.render("Target", True, (160, 0, 0)),
        (target_position[0] + 12, target_position[1] - 10),
    )

    if state["launched"]:
        interceptor_position = to_screen(interceptor["x"], interceptor["y"])
        pygame.draw.circle(screen, (0, 0, 220), interceptor_position, 8)
        screen.blit(
            font.render("Interceptor", True, (0, 0, 160)),
            (interceptor_position[0] + 12, interceptor_position[1] - 10),
        )

    status = "SEARCHING"
    status_color = (80, 80, 80)
    if state["detected"]:
        status = "DETECTED"
        status_color = (180, 120, 0)
    if state["launched"]:
        status = "LAUNCHED"
        status_color = (0, 80, 200)
    if state["success"]:
        status = "INTERCEPT"
        status_color = (0, 180, 0)
    if state["failed"]:
        status = "FAILED"
        status_color = (200, 0, 0)

    text = (
        f"t={state['time']:.1f}s  launched={state['launched']}  "
        f"distance={dist(target, interceptor):.1f} yd  "
        f"speed={interceptor['speed']:.1f} yd/s"
    )
    screen.blit(font.render(text, True, (0, 0, 0)), (20, 20))
    screen.blit(font.render(f"Status: {status}", True, status_color), (20, 150))

    if paused:
        screen.blit(
            font.render("PAUSED - press Space", True, (0, 0, 0)),
            (20, 90),
        )

    screen.blit(
        font.render(
            "Space=pause  R=restart  UP/DOWN=interceptor speed",
            True,
            (0, 0, 0),
        ),
        (20, 120),
    )

    screen.blit(font.render("Event Log", True, (0, 0, 0)), (650, 20))
    for i, message in enumerate(state["event_log"][-8:]):
        screen.blit(
            font.render(message, True, (0, 0, 0)),
            (650, 50 + i * 25),
        )

    if state["success"]:
        screen.blit(
            font.render(
                "SUCCESS: simulated intercept radius reached",
                True,
                (0, 120, 0),
            ),
            (20, 55),
        )
    elif state["failed"]:
        screen.blit(
            font.render(
                "FAILED: target crossed protected line",
                True,
                (180, 0, 0),
            ),
            (20, 55),
        )

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
