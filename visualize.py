"""Pygame visualization for the drone response timing simulator."""

import math
import pygame

import config
from simulation import Simulation

pygame.init()
screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
pygame.display.set_caption("Randomized Multi-Drone Response Simulation")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)
small_font = pygame.font.SysFont(None, 20)
large_font = pygame.font.SysFont(None, 34)


def to_screen(x, y):
    return (
        int(config.ORIGIN_X + x * config.SCALE),
        int(config.ORIGIN_Y - y * config.SCALE),
    )


def draw_vector(entity, vx, vy, color):
    start = to_screen(entity["x"], entity["y"])
    end = to_screen(
        entity["x"] + vx * config.VECTOR_SECONDS,
        entity["y"] + vy * config.VECTOR_SECONDS,
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


simulation = Simulation()
started = False
paused = False
show_vectors = True
simulation_rate = 1.0
running = True

while running:
    elapsed_seconds = clock.tick(config.FPS) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            if not started:
                started = True
                paused = False
                simulation.event_log.append("Run started")
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            if started:
                paused = not paused
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_v:
            show_vectors = not show_vectors
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_1:
            simulation_rate = 1.0
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_2:
            simulation_rate = 2.0
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_3:
            simulation_rate = 5.0
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_4:
            simulation_rate = 10.0
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_UP:
            simulation.adjust_interceptor_speed(5.0)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_DOWN:
            simulation.adjust_interceptor_speed(-5.0)
        elif event.type == pygame.KEYDOWN and event.key in (
            pygame.K_RIGHT,
            pygame.K_RIGHTBRACKET,
            pygame.K_d,
        ):
            simulation.set_target_count(simulation.target_count + 1)
            started = False
            paused = False
        elif event.type == pygame.KEYDOWN and event.key in (
            pygame.K_LEFT,
            pygame.K_LEFTBRACKET,
            pygame.K_a,
        ):
            simulation.set_target_count(simulation.target_count - 1)
            started = False
            paused = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_n:
            simulation.new_seed()
            started = False
            paused = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_s:
            simulation.toggle_staggered_arrival()
            started = False
            paused = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            simulation.reset()
            started = False
            paused = False

    if started and not paused:
        simulation.step(elapsed_seconds * simulation_rate)

    screen.fill((245, 245, 245))

    for balloon in simulation.balloons:
        pygame.draw.circle(
            screen,
            (185, 185, 185),
            to_screen(balloon["x"], balloon["y"]),
            int(config.DETECTION_RANGE * config.SCALE),
            1,
        )

    pygame.draw.line(
        screen,
        (180, 180, 0),
        to_screen(-1300, config.PROTECTED_LINE_Y),
        to_screen(1300, config.PROTECTED_LINE_Y),
        3,
    )

    for target in simulation.targets:
        if not target["spawned"]:
            continue

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
        for target in simulation.targets
        if target["selected_balloon"] is not None
        and target["status"] not in ("INTERCEPT", "FAILED")
    }

    for balloon in simulation.balloons:
        position = to_screen(balloon["x"], balloon["y"])
        active = balloon["id"] in active_balloon_ids
        pygame.draw.circle(screen, (0, 160, 0), position, 13 if active else 10)

        queue_length = len(balloon["queue"])
        if queue_length:
            countdown = max(0.0, balloon["next_launch_time"] - simulation.time)
            queue_text = f" q={queue_length} next={countdown:.1f}s"
        else:
            queue_text = " q=0"

        label = (
            f"B{balloon['id']} inv={balloon['inventory']}{queue_text}"
            + (" ACTIVE" if active else "")
        )
        screen.blit(
            small_font.render(label, True, (0, 100, 0)),
            (position[0] + 10, position[1] - 8),
        )

    for target in simulation.targets:
        if not target["spawned"]:
            continue

        position = to_screen(target["x"], target["y"])
        resolved = target["status"] in ("INTERCEPT", "FAILED")
        if target["status"] == "INTERCEPT":
            target_color = (0, 150, 0)
        elif target["status"] == "FAILED":
            target_color = (150, 0, 0)
        elif target["status"] == "UNASSIGNED":
            target_color = (220, 120, 0)
        elif target["status"] == "QUEUED":
            target_color = (120, 0, 180)
        else:
            target_color = (220, 0, 0)

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
            if target["status"] == "UNASSIGNED":
                vector_color = (220, 120, 0)
            elif target["status"] == "QUEUED":
                vector_color = (120, 0, 180)
            else:
                vector_color = (180, 0, 0)
            draw_vector(target, target["vx"], target["vy"], vector_color)

        interceptor = target["interceptor"]
        if interceptor is not None and interceptor["launched"]:
            interceptor_position = to_screen(interceptor["x"], interceptor["y"])
            pygame.draw.circle(screen, (0, 0, 220), interceptor_position, 7)
            screen.blit(
                small_font.render(f"I{interceptor['id']}", True, (0, 0, 160)),
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

    metrics = simulation.metrics()
    mode = "staggered" if simulation.staggered_arrival else "simultaneous"
    screen.blit(
        font.render(
            f"t={simulation.time:.1f}s  rate={simulation_rate:g}x  seed={simulation.seed}  "
            f"mode={mode}  targets={metrics['targets']}  waiting={metrics['waiting']}  "
            f"interceptor speed={simulation.interceptor_speed:.0f} yd/s",
            True,
            (0, 0, 0),
        ),
        (20, 20),
    )
    screen.blit(
        font.render(
            f"queued={metrics['queued']}  launched={metrics['launched']}  "
            f"intercepted={metrics['intercepted']}  failed={metrics['failed']}  "
            f"unassigned={metrics['unassigned']}",
            True,
            (0, 0, 0),
        ),
        (20, 46),
    )
    screen.blit(
        small_font.render(
            "LEFT/RIGHT or A/D targets   N seed   S arrival   ENTER start   "
            "R reset   Space pause   V vectors   UP/DOWN speed   1/2/3/4 time scale",
            True,
            (0, 0, 0),
        ),
        (20, 74),
    )

    if not started:
        panel = pygame.Rect(250, 125, 600, 255)
        pygame.draw.rect(screen, (235, 242, 252), panel)
        pygame.draw.rect(screen, (0, 70, 150), panel, 2)
        screen.blit(
            large_font.render("SETUP MODE", True, (0, 70, 150)),
            (panel.x + 210, panel.y + 18),
        )
        screen.blit(
            large_font.render(
                f"Target count: {simulation.target_count}",
                True,
                (0, 0, 0),
            ),
            (panel.x + 55, panel.y + 70),
        )
        screen.blit(
            large_font.render(
                f"Interceptor speed: {simulation.interceptor_speed:.0f} yd/s",
                True,
                (0, 0, 0),
            ),
            (panel.x + 55, panel.y + 110),
        )
        screen.blit(
            font.render(
                f"Time scale: {simulation_rate:g}x (1 = real time)",
                True,
                (0, 0, 0),
            ),
            (panel.x + 55, panel.y + 150),
        )
        screen.blit(
            font.render(
                f"Launch interval: {config.LAUNCH_INTERVAL:.1f}s per balloon",
                True,
                (0, 0, 0),
            ),
            (panel.x + 55, panel.y + 180),
        )
        screen.blit(
            font.render(
                f"Seed: {simulation.seed}    Arrival: {mode}",
                True,
                (0, 0, 0),
            ),
            (panel.x + 55, panel.y + 208),
        )
        screen.blit(
            font.render("Press ENTER to start", True, (0, 100, 0)),
            (panel.x + 205, panel.y + 232),
        )
    elif paused:
        screen.blit(font.render("PAUSED", True, (0, 0, 0)), (20, 100))

    if simulation.complete:
        summary = (
            f"RUN COMPLETE: {metrics['intercepted']} intercepted, "
            f"{metrics['failed']} failed, {metrics['unassigned']} were unassigned"
        )
        screen.blit(font.render(summary, True, (0, 120, 0)), (20, 100))

    screen.blit(font.render("Event Log", True, (0, 0, 0)), (820, 20))
    for index, message in enumerate(simulation.event_log[-14:]):
        screen.blit(
            small_font.render(message, True, (0, 0, 0)),
            (820, 50 + index * 21),
        )

    pygame.display.flip()

pygame.quit()
