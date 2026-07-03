import math

DT = 0.1
MAX_TIME = 120.0

# yards and seconds
target = {"x": 0.0, "y": 1200.0, "vx": 0.0, "vy": -22.0}
balloon = {"x": 0.0, "y": 0.0}
interceptor = {"x": balloon["x"], "y": balloon["y"], "speed": 44.0}

launch_delay = 5.0
success_radius = 25.0
protected_line_y = 0.0

launched = False
success = False
t = 0.0

def distance(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])

while t <= MAX_TIME:
    target["x"] += target["vx"] * DT
    target["y"] += target["vy"] * DT

    if t >= launch_delay:
        launched = True

    if launched:
        dx = target["x"] - interceptor["x"]
        dy = target["y"] - interceptor["y"]
        d = math.hypot(dx, dy)

        if d > 0:
            interceptor["x"] += interceptor["speed"] * dx / d * DT
            interceptor["y"] += interceptor["speed"] * dy / d * DT

        if d <= success_radius:
            success = True
            break

    if target["y"] <= protected_line_y:
        break

    t += DT

print("Simulation complete")
print(f"Success: {success}")
print(f"Time: {t:.1f} sec")
print(f"Target position: ({target['x']:.1f}, {target['y']:.1f})")
print(f"Interceptor position: ({interceptor['x']:.1f}, {interceptor['y']:.1f})")
print(f"Final distance: {distance(target, interceptor):.1f} yards")
