"""Pygame visualization for the drone response timing simulator."""

import math
import pygame

import config
from simulation import Simulation

pygame.init()
screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
pygame.display.set_caption("Multi-Drone Response Simulation")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)
small_font = pygame.font.SysFont(None, 20)


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
            simulation.adjust_interceptor_speed(5.0)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_DOWN:
            simulation.adjust_interceptor_speed(-5.0)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            simulation.reset()
            paused = False

    if not paused:
        simulation.step()

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
        and target["status"] not in ("INTERCEPT", "FAILED", "UNASSIGNED")
    }

    for balloon in simulation.balloons:
        position = to_screen(balloon["x"], balloon["y"])
        active = balloon["id"] in active_balloon_ids
        pygame.draw.circle(screen, (0, 160, 0), position, 13 if active else 10)
        label = (
            f"B{balloon['id']} inv={balloon['inventory']}"
            + (" ACTIVE" if active else "")
        )
        screen.blit(
            small_font.render(label, True, (0, 100, 0)),
            (position[0] + 10, position[1] - 8),
        )

    for target in simulation.targets:
        position = to_screen(target["x"], target["y"])
        resolved = target["status"] in ("INTERCEPT", "FAILED", "UNASSIGNED")
        if target["status"] == "INTERCEPT":
            target_color = (0, 150, 0)
        elif target["status"] in ("FAILED", "UNASSIGNED"):
            target_color = (150, 0, 0)
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
            draw_vector(target, target["vx"], target["vy"], (180, 0, 0))

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
    screen.blit(
        font.render(
            f"t={simulation.time:.1f}s  targets={metrics['targets']}  "
            f"launched={metrics['launched']}  intercepted={metrics['intercepted']}  "
            f"failed={metrics['failed']}  unassigned={metrics['unassigned']}",
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

    if simulation.complete:
        summary = (
            f"RUN COMPLETE: {metrics['intercepted']} intercepted, "
            f"{metrics['failed']} failed, {metrics['unassigned']} unassigned"
        )
        screen.blit(font.render(summary, True, (0, 120, 0)), (20, 80))

    screen.blit(font.render("Event Log", True, (0, 0, 0)), (820, 20))
    for index, message in enumerate(simulation.event_log[-12:]):
        screen.blit(
            small_font.render(message, True, (0, 0, 0)),
            (820, 50 + index * 22),
        )

    pygame.display.flip()
    clock.tick(config.FPS)

pygame.quit()
