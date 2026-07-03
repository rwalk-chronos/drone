"""Abstract interceptor guidance modes for the non-destructive timing simulator.

These modes only choose a simulated aim point for a moving dot. They do not model
payloads, damage, or real-world flight-control implementation.
"""

import math


MODE_DIRECT = "direct"
MODE_PREDICTED = "predicted"
MODE_WAYPOINT = "waypoint"
MODE_SENSOR_DELAY = "sensor_delay"
MODE_TARGET_LOSS = "target_loss"

GUIDANCE_MODES = [
    MODE_DIRECT,
    MODE_PREDICTED,
    MODE_WAYPOINT,
    MODE_SENSOR_DELAY,
    MODE_TARGET_LOSS,
]


def mode_label(mode):
    return mode.replace("_", " ").title()


def distance(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def target_point(target):
    return {"x": target["x"], "y": target["y"]}


def delayed_target_point(target, current_time, delay_seconds):
    history = target.get("history", [])
    if not history:
        return target_point(target)

    desired_time = current_time - delay_seconds
    best_sample = history[0]
    for sample in history:
        if sample["time"] <= desired_time:
            best_sample = sample
        else:
            break
    return {"x": best_sample["x"], "y": best_sample["y"]}


def predicted_intercept_point(interceptor, target, max_lead_seconds):
    rx = target["x"] - interceptor["x"]
    ry = target["y"] - interceptor["y"]
    vx = target["vx"]
    vy = target["vy"]
    speed = max(interceptor["speed"], 1e-6)

    a = vx * vx + vy * vy - speed * speed
    b = 2.0 * (rx * vx + ry * vy)
    c = rx * rx + ry * ry

    lead_time = None
    if abs(a) < 1e-9:
        if abs(b) > 1e-9:
            candidate = -c / b
            if candidate > 0:
                lead_time = candidate
    else:
        discriminant = b * b - 4.0 * a * c
        if discriminant >= 0:
            root = math.sqrt(discriminant)
            candidates = [
                (-b - root) / (2.0 * a),
                (-b + root) / (2.0 * a),
            ]
            positives = [candidate for candidate in candidates if candidate > 0]
            if positives:
                lead_time = min(positives)

    if lead_time is None:
        lead_time = min(max(distance(interceptor, target) / speed, 0.0), max_lead_seconds)
    else:
        lead_time = min(lead_time, max_lead_seconds)

    return {
        "x": target["x"] + target["vx"] * lead_time,
        "y": target["y"] + target["vy"] * lead_time,
    }


def waypoint_point(interceptor, target, protected_line_y, max_lead_seconds):
    if interceptor.get("waypoint") is None:
        vy = target["vy"]
        if vy < 0:
            time_to_line = max((protected_line_y - target["y"]) / vy, 0.0)
        else:
            time_to_line = max_lead_seconds
        lead_time = min(time_to_line * 0.55, max_lead_seconds)
        interceptor["waypoint"] = {
            "x": target["x"] + target["vx"] * lead_time,
            "y": target["y"] + target["vy"] * lead_time,
        }

    waypoint = interceptor["waypoint"]
    if distance(interceptor, waypoint) < 45.0:
        return target_point(target)
    return waypoint


def target_loss_point(interceptor, target, current_time, track_range, hold_seconds):
    current = target_point(target)
    if distance(interceptor, target) <= track_range:
        interceptor["last_track_time"] = current_time
        interceptor["last_target_point"] = current
        interceptor["tracking_status"] = "TRACKING"
        return current

    last_point = interceptor.get("last_target_point", current)
    last_time = interceptor.get("last_track_time", current_time)
    if current_time - last_time <= hold_seconds:
        interceptor["tracking_status"] = "HOLDING_LAST_TRACK"
        return last_point

    interceptor["tracking_status"] = "SEARCHING_LAST_TRACK"
    return last_point


def aim_point(mode, interceptor, target, current_time, config_module):
    if mode == MODE_DIRECT:
        interceptor["tracking_status"] = "DIRECT"
        return target_point(target)

    if mode == MODE_PREDICTED:
        interceptor["tracking_status"] = "PREDICTED"
        return predicted_intercept_point(
            interceptor,
            target,
            config_module.MAX_GUIDANCE_LEAD_TIME,
        )

    if mode == MODE_WAYPOINT:
        interceptor["tracking_status"] = "WAYPOINT"
        return waypoint_point(
            interceptor,
            target,
            config_module.PROTECTED_LINE_Y,
            config_module.MAX_GUIDANCE_LEAD_TIME,
        )

    if mode == MODE_SENSOR_DELAY:
        interceptor["tracking_status"] = "SENSOR_DELAY"
        return delayed_target_point(
            target,
            current_time,
            config_module.SENSOR_DELAY_SECONDS,
        )

    if mode == MODE_TARGET_LOSS:
        return target_loss_point(
            interceptor,
            target,
            current_time,
            config_module.TARGET_TRACK_RANGE,
            config_module.TARGET_LOSS_HOLD_SECONDS,
        )

    interceptor["tracking_status"] = "DIRECT"
    return target_point(target)
