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

target = {"x": 0.0, "y": 1200.0, "vx": 0.0, "vy": -22.0}
balloon = {"x": 0.0, "y": 0.0}
interceptor = {"x": balloon["x"], "y": balloon["y"], "speed": 60.0}

launch_delay = 2.0
success_radius = 40.0
protected_line_y = 0.0
detection_range = 1000.0

target_path = []
interceptor_path = []

launched = False
success = False
failed = False
t = 0.0
paused = False
detected = False
event_log = ["Simulation started"]

def to_screen(x, y):
    return int(origin_x + x * scale), int(origin_y - y * scale)

def dist(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            paused = not paused
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_UP:
            interceptor["speed"] += 5.0
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_DOWN:
            interceptor["speed"] = max(5.0, interceptor["speed"] - 5.0)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            target = {"x": 0.0, "y": 1200.0, "vx": 0.0, "vy": -22.0}
            interceptor = {"x": balloon["x"], "y": balloon["y"], "speed": 44.0}
            target_path = []
            interceptor_path = []
            launched = False
            success = False
            failed = False
            detected = False
            event_log = ["Simulation restarted"]
            t = 0.0

    if not paused and not success and not failed:
        target["x"] += target["vx"] * DT
        target["y"] += target["vy"] * DT
        target_path.append((target["x"], target["y"]))

        if not detected and dist(target, balloon) <= detection_range:
            detected = True
            event_log.append(f"Detected at {t:.1f}s")
        if t >= launch_delay:
            launched = True
            if "Interceptor launched" not in event_log:
                event_log.append("Interceptor launched")

        if launched:
            dx = target["x"] - interceptor["x"]
            dy = target["y"] - interceptor["y"]
            d = math.hypot(dx, dy)

            if d > 0:
                interceptor["x"] += interceptor["speed"] * dx / d * DT
                interceptor["y"] += interceptor["speed"] * dy / d * DT

            interceptor_path.append((interceptor["x"], interceptor["y"]))

            if d <= success_radius:
                success = True
                event_log.append(f"Intercept at {t:.1f}s")

        if target["y"] <= protected_line_y:
            failed = True
            event_log.append(f"Target crossed line at {t:.1f}s")

        t += DT

    screen.fill((245, 245, 245))

    # protected line
    # detection range
    pygame.draw.circle(screen, (180, 180, 180), to_screen(balloon["x"], balloon["y"]), int(detection_range * scale), 1)
    pygame.draw.line(screen, (180, 180, 0), to_screen(-1000, protected_line_y), to_screen(1000, protected_line_y), 3)

    # paths
    if len(target_path) > 1:
        pygame.draw.lines(screen, (200, 0, 0), False, [to_screen(x, y) for x, y in target_path], 2)

    if len(interceptor_path) > 1:
        pygame.draw.lines(screen, (0, 0, 200), False, [to_screen(x, y) for x, y in interceptor_path], 2)

    # balloon
    pygame.draw.circle(screen, (0, 160, 0), to_screen(balloon["x"], balloon["y"]), 10)
    screen.blit(font.render("Balloon", True, (0, 100, 0)), (to_screen(balloon["x"], balloon["y"])[0] + 12, to_screen(balloon["x"], balloon["y"])[1] - 10))

    # target
    pygame.draw.circle(screen, (220, 0, 0), to_screen(target["x"], target["y"]), 8)
    screen.blit(font.render("Target", True, (160, 0, 0)), (to_screen(target["x"], target["y"])[0] + 12, to_screen(target["x"], target["y"])[1] - 10))

    # interceptor
    if launched:
        pygame.draw.circle(screen, (0, 0, 220), to_screen(interceptor["x"], interceptor["y"]), 8)
        screen.blit(font.render("Interceptor", True, (0, 0, 160)), (to_screen(interceptor["x"], interceptor["y"])[0] + 12, to_screen(interceptor["x"], interceptor["y"])[1] - 10))

    text = f"t={t:.1f}s  launched={launched}  distance={dist(target, interceptor):.1f} yd  speed={interceptor["speed"]:.1f} yd/s"

    status = "SEARCHING"
    color = (80,80,80)
    if detected:
        status = "DETECTED"
        color = (180,120,0)
    if launched:
        status = "LAUNCHED"
        color = (0,80,200)
    if success:
        status = "INTERCEPT"
        color = (0,180,0)
    if failed:
        status = "FAILED"
        color = (200,0,0)

    screen.blit(font.render(f"Status: {status}", True, color), (20,150))

    screen.blit(font.render("Event Log", True, (0,0,0)), (650, 20))
    for i, msg in enumerate(event_log[-8:]):
        screen.blit(font.render(msg, True, (0,0,0)), (650, 50 + i * 25))

    status = "SEARCHING"
    color = (80,80,80)
    if detected:
        status = "DETECTED"
        color = (180,120,0)
    if launched:
        status = "LAUNCHED"
        color = (0,80,200)
    if success:
        status = "INTERCEPT"
        color = (0,180,0)
    if failed:
        status = "FAILED"
        color = (200,0,0)

    screen.blit(font.render(f"Status: {status}", True, color), (20,150))

    screen.blit(font.render("Event Log", True, (0,0,0)), (650, 20))
    for i, msg in enumerate(event_log[-8:]):
        screen.blit(font.render(msg, True, (0,0,0)), (650, 50 + i * 25))
    if paused:
        screen.blit(font.render("PAUSED - press Space", True, (0, 0, 0)), (20, 90))
    screen.blit(font.render("Space=pause  R=restart  UP/DOWN=speed", True, (0, 0, 0)), (20, 120))
    screen.blit(font.render(text, True, (0, 0, 0)), (20, 20))

    if success:
        screen.blit(font.render("SUCCESS: simulated intercept radius reached", True, (0, 120, 0)), (20, 55))
    elif failed:
        screen.blit(font.render("FAILED: target crossed protected line", True, (180, 0, 0)), (20, 55))

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
