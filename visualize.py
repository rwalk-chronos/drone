import math
import pygame

pygame.init()

WIDTH, HEIGHT = 1100, 760
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Multi-Drone Response Simulation")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)
small_font = pygame.font.SysFont(None, 20)

DT = 0.1
SCALE = 0.38
ORIGIN_X = WIDTH // 2
ORIGIN_Y = HEIGHT - 90
VECTOR_SECONDS = 5.0
INITIAL_INTERCEPTOR_SPEED = 60.0

TARGET_TEMPLATES = [
    {"x": -520.0, "y": 1500.0, "vx": 7.0, "vy": -24.0},
    {"x": -260.0, "y": 1420.0, "vx": 4.0, "vy": -23.0},
    {"x": 0.0, "y": 1560.0, "vx": 0.0, "vy": -26.0},
    {"x": 280.0, "y": 1460.0, "vx": -4.0, "vy": -23.0},
    {"x": 520.0, "y": 1520.0, "vx": -7.0, "vy": -24.0},
]

balloons = [
    {"id": 1, "x": -500.0, "y": 0.0},
    {"id": 2, "x": 0.0, "y": 0.0},
    {"id": 3, "x": 500.0, "y": 0.0},
]

launch_delay = 2.0
success_radius = 40.0
protected_line_y = 0.0
detection_range = 1100.0


def to_screen(x, y):
    return int(ORIGIN_X + x * SCALE), int(ORIGIN_Y - y * SCALE)


def distance(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def draw_vector(entity, vx, vy, color):
    start = to_screen(entity["x"], entity["y"])
    end = to_screen(
        entity["x"] + vx * VECTOR_SECONDS,
        entity["y"] + vy * VECTOR_SECONDS,
    )
    pygame.draw.line(screen, color, start, end, 2)

    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1:
        return

    ux = dx / length
    uy = dy / length
    left = (
        int(end[0] - 10 * ux + 5 * uy),
        int(end[1] - 10 * uy - 5 * ux),
    )
    right = (
        int(end[0] - 10 * ux - 5 * uy),
        int(end[1] - 10 * uy + 5 * ux),
    )
    pygame.draw.polygon(screen, color, [end, left, right])


def new_target(index, template):
    target = dict(template)
    target.update(
        {
            "id": index + 1,
            "status": "SEARCHING",
            "detected": False,
            "launch_time": None,
            "selected_balloon": None,
            "path": [],
            "interceptor": None,
            "resolved_time": None,
        }
    )
    return target


def reset_simulation(message):
    return {
        "targets": [
            new_target(index, template)
            for index, template in enumerate(TARGET_TEMPLATES)
        ],
        "time": 0.0,
        "event_log": [message],
        "complete": False,
    }


def create_interceptor(target, balloon):
    return {
        "id": target["id"],
        "x": balloon["x"],
        "y": balloon["y"],
        "vx": 0.0,
        "vy": 0.0,
        "speed": INITIAL_INTERCEPTOR_SPEED,
        "launched": False,
        "path": [],
    }


def nearest_balloon(target):
    return min(balloons, key=lambda node: distance(target, node))


def all_targets_resolved(targets):
    return all(target["status"] in ("INTERCEPT", "FAILED") for target in targets)


state = reset_simulation("Simulation started")
paused = False
show_vectors = True
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            paused = not paused
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_v:
            show_vectors = not show_vectors
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_UP:
            for target in state["targets"]:
                if target["interceptor"] is not None:
                    target["interceptor"]["speed"] += 5.0
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_DOWN:
            for target in state["targets"]:
                if target["interceptor"] is not None:
                    target["interceptor"]["speed"] = max(
                        5.0,
                        target["interceptor"]["speed"] - 5.0,
                    )
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            state = reset_simulation("Simulation restarted")
            paused = False

    if not paused and not state["complete"]:
        for target in state["targets"]:
            if target["status"] in ("INTERCEPT", "FAILED"):
                continue

            target["x"] += target["vx"] * DT
            target["y"] += target["vy"] * DT
            target["path"].append((target["x"], target["y"]))

            if not target["detected"]:
                in_range = [
                    balloon
                    for balloon in balloons
                    if distance(target, balloon) <= detection_range
                ]
                if in_range:
                    target["detected"] = True
                    target["status"] = "DETECTED"
                    target["selected_balloon"] = nearest_balloon(target)
                    target["interceptor"] = create_interceptor(
                        target,
                        target["selected_balloon"],
                    )
                    target["launch_time"] = state["time"] + launch_delay
                    state["event_log"].append(
                        f"T{target['id']} detected at {state['time']:.1f}s"
                    )

            interceptor = target["interceptor"]
            if (
                target["detected"]
                and interceptor is not None
                and not interceptor["launched"]
                and state["time"] >= target["launch_time"]
            ):
                interceptor["launched"] = True
                target["status"] = "LAUNCHED"
                state["event_log"].append(f"I{interceptor['id']} launched")

            if interceptor is not None and interceptor["launched"]:
                dx = target["x"] - interceptor["x"]
                dy = target["y"] - interceptor["y"]
                d = math.hypot(dx, dy)

                if d > 0:
                    interceptor["vx"] = interceptor["speed"] * dx / d
                    interceptor["vy"] = interceptor["speed"] * dy / d
                    interceptor["x"] += interceptor["vx"] * DT
                    interceptor["y"] += interceptor["vy"] * DT

                interceptor["path"].append((interceptor["x"], interceptor["y"]))

                if distance(target, interceptor) <= success_radius:
                    target["status"] = "INTERCEPT"
                    target["resolved_time"] = state["time"]
                    state["event_log"].append(
                        f"T{target['id']} intercept at {state['time']:.1f}s"
                    )

            if target["y"] <= protected_line_y and target["status"] != "INTERCEPT":
                target["status"] = "FAILED"
                target["resolved_time"] = state["time"]
                state["event_log"].append(f"T{target['id']} crossed line")

        state["time"] += DT

        if all_targets_resolved(state["targets"]):
            state["complete"] = True
            state["event_log"].append(
                f"Run complete at {state['time']:.1f}s"
            )

    screen.fill((245, 245, 245))

    for balloon in balloons:
        pygame.draw.circle(
            screen,
            (185, 185, 185),
            to_screen(balloon["x"], balloon["y"]),
            int(detection_range * SCALE),
            1,
        )

    pygame.draw.line(
        screen,
        (180, 180, 0),
        to_screen(-1300, protected_line_y),
        to_screen(1300, protected_line_y),
        3,
    )

    for target in state["targets"]:
        if len(target["path"]) > 1:
            pygame.draw.lines(
                screen,
                (200, 0, 0),
                False,
                [to_screen(x, y) for x, y in target["path"]],
                2,
            )

        interceptor = target["interceptor"]
        if interceptor is not None and len(interceptor["path"]) > 1:
            pygame.draw.lines(
                screen,
                (0, 0, 200),
                False,
                [to_screen(x, y) for x, y in interceptor["path"]],
                2,
            )

    active_balloon_ids = {
        target["selected_balloon"]["id"]
        for target in state["targets"]
        if target["selected_balloon"] is not None
        and target["status"] not in ("INTERCEPT", "FAILED")
    }

    for balloon in balloons:
        position = to_screen(balloon["x"], balloon["y"])
        active = balloon["id"] in active_balloon_ids
        pygame.draw.circle(screen, (0, 160, 0), position, 13 if active else 10)
        label = f"B{balloon['id']}" + (" ACTIVE" if active else "")
        screen.blit(
            small_font.render(label, True, (0, 100, 0)),
            (position[0] + 10, position[1] - 8),
        )

    for target in state["targets"]:
        position = to_screen(target["x"], target["y"])
        resolved = target["status"] in ("INTERCEPT", "FAILED")
        target_color = (
            (0, 150, 0)
            if target["status"] == "INTERCEPT"
            else (150, 0, 0) if target["status"] == "FAILED" else (220, 0, 0)
        )
        pygame.draw.circle(screen, target_color, position, 7)

        label_y_offset = -26 if target["id"] % 2 else 10
        screen.blit(
            small_font.render(
                f"T{target['id']} {target['status']}",
                True,
                target_color,
            ),
            (position[0] + 10, position[1] + label_y_offset),
        )

        if show_vectors and not resolved:
            draw_vector(target, target["vx"], target["vy"], (180, 0, 0))

        interceptor = target["interceptor"]
        if interceptor is not None and interceptor["launched"]:
            interceptor_position = to_screen(interceptor["x"], interceptor["y"])
            pygame.draw.circle(screen, (0, 0, 220), interceptor_position, 7)
            screen.blit(
                small_font.render(
                    f"I{interceptor['id']}",
                    True,
                    (0, 0, 160),
                ),
                (
                    interceptor_position[0] + 10,
                    interceptor_position[1] + (10 if target["id"] % 2 else -26),
                ),
            )
            if show_vectors and not resolved:
                draw_vector(
                    interceptor,
                    interceptor["vx"],
                    interceptor["vy"],
                    (0, 0, 180),
                )

    intercepted = sum(
        1 for target in state["targets"] if target["status"] == "INTERCEPT"
    )
    failed = sum(
        1 for target in state["targets"] if target["status"] == "FAILED"
    )
    launched = sum(
        1
        for target in state["targets"]
        if target["interceptor"] is not None
        and target["interceptor"]["launched"]
    )

    screen.blit(
        font.render(
            f"t={state['time']:.1f}s  targets={len(state['targets'])}  "
            f"launched={launched}  intercepted={intercepted}  failed={failed}",
            True,
            (0, 0, 0),
        ),
        (20, 20),
    )
    screen.blit(
        font.render(
            "Space=pause  R=restart  V=vectors  UP/DOWN=interceptor speed",
            True,
            (0, 0, 0),
        ),
        (20, 50),
    )

    if paused:
        screen.blit(font.render("PAUSED", True, (0, 0, 0)), (20, 80))

    if state["complete"]:
        summary = f"RUN COMPLETE: {intercepted} intercepted, {failed} failed"
        screen.blit(font.render(summary, True, (0, 120, 0)), (20, 80))

    screen.blit(font.render("Event Log", True, (0, 0, 0)), (820, 20))
    for index, message in enumerate(state["event_log"][-12:]):
        screen.blit(
            small_font.render(message, True, (0, 0, 0)),
            (820, 50 + index * 22),
        )

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
