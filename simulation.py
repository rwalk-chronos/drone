"""Core kinematic simulation engine, independent of Pygame rendering."""

import math
import random
from copy import deepcopy

import config


TERMINAL_STATUSES = {"INTERCEPT", "FAILED"}


def distance(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


class Simulation:
    def __init__(self):
        self.target_count = config.DEFAULT_TARGET_COUNT
        self.seed = config.DEFAULT_RANDOM_SEED
        self.staggered_arrival = config.DEFAULT_STAGGERED_ARRIVAL
        self.interceptor_speed = config.INITIAL_INTERCEPTOR_SPEED
        self.reset("Simulation started")

    def generate_target_templates(self):
        rng = random.Random(self.seed)
        templates = []

        for _ in range(self.target_count):
            speed = rng.uniform(*config.TARGET_SPEED_RANGE)
            horizontal_limit = speed * config.TARGET_HORIZONTAL_FRACTION
            vx = rng.uniform(-horizontal_limit, horizontal_limit)
            vy = -math.sqrt(max(speed * speed - vx * vx, 0.0))
            spawn_time = (
                rng.uniform(0.0, config.MAX_SPAWN_DELAY)
                if self.staggered_arrival
                else 0.0
            )
            templates.append(
                {
                    "x": rng.uniform(*config.TARGET_START_X_RANGE),
                    "y": rng.uniform(*config.TARGET_START_Y_RANGE),
                    "vx": vx,
                    "vy": vy,
                    "spawn_time": spawn_time,
                }
            )

        return templates

    def reset(self, message="Simulation restarted"):
        self.time = 0.0
        self.complete = False
        self.event_log = [
            f"{message} | seed={self.seed} targets={self.target_count} "
            f"speed={self.interceptor_speed:.0f} staggered={self.staggered_arrival}"
        ]
        self.balloons = []
        for template in config.BALLOON_TEMPLATES:
            balloon = deepcopy(template)
            balloon["inventory"] = config.INTERCEPTORS_PER_BALLOON
            self.balloons.append(balloon)

        self.targets = []
        for index, template in enumerate(self.generate_target_templates(), start=1):
            target = deepcopy(template)
            target.update(
                {
                    "id": index,
                    "status": "WAITING" if target["spawn_time"] > 0 else "SEARCHING",
                    "spawned": target["spawn_time"] <= 0,
                    "detected": False,
                    "unassigned": False,
                    "launch_time": None,
                    "selected_balloon": None,
                    "path": [],
                    "interceptor": None,
                    "resolved_time": None,
                }
            )
            self.targets.append(target)

    def set_target_count(self, count):
        self.target_count = max(
            config.MIN_TARGET_COUNT,
            min(config.MAX_TARGET_COUNT, count),
        )
        self.reset("Target count changed")

    def new_seed(self):
        self.seed += 1
        self.reset("New randomized scenario")

    def toggle_staggered_arrival(self):
        self.staggered_arrival = not self.staggered_arrival
        self.reset("Arrival mode changed")

    def adjust_interceptor_speed(self, delta):
        self.interceptor_speed = max(5.0, self.interceptor_speed + delta)
        for target in self.targets:
            interceptor = target["interceptor"]
            if interceptor is not None:
                interceptor["speed"] = self.interceptor_speed

    def available_balloons_in_range(self, target):
        return [
            balloon
            for balloon in self.balloons
            if balloon["inventory"] > 0
            and distance(target, balloon) <= config.DETECTION_RANGE
        ]

    def assign_interceptor(self, target):
        candidates = self.available_balloons_in_range(target)
        if not candidates:
            return False

        balloon = min(candidates, key=lambda node: distance(target, node))
        balloon["inventory"] -= 1
        target["detected"] = True
        target["status"] = "DETECTED"
        target["selected_balloon"] = balloon
        target["launch_time"] = self.time + config.LAUNCH_DELAY
        target["interceptor"] = {
            "id": target["id"],
            "x": balloon["x"],
            "y": balloon["y"],
            "vx": 0.0,
            "vy": 0.0,
            "speed": self.interceptor_speed,
            "launched": False,
            "path": [],
        }
        self.event_log.append(
            f"T{target['id']} assigned B{balloon['id']} at {self.time:.1f}s"
        )
        return True

    def update_target(self, target, dt):
        if target["status"] in TERMINAL_STATUSES:
            return

        if not target["spawned"]:
            if self.time < target["spawn_time"]:
                return
            target["spawned"] = True
            target["status"] = "SEARCHING"
            self.event_log.append(f"T{target['id']} entered at {self.time:.1f}s")

        target["x"] += target["vx"] * dt
        target["y"] += target["vy"] * dt
        target["path"].append((target["x"], target["y"]))

        if not target["detected"]:
            in_any_detection_zone = any(
                distance(target, balloon) <= config.DETECTION_RANGE
                for balloon in self.balloons
            )
            if in_any_detection_zone:
                if self.assign_interceptor(target):
                    target["unassigned"] = False
                elif not target["unassigned"]:
                    target["unassigned"] = True
                    target["detected"] = True
                    target["status"] = "UNASSIGNED"
                    self.event_log.append(
                        f"T{target['id']} unassigned: no inventory"
                    )

        interceptor = target["interceptor"]
        if (
            interceptor is not None
            and not interceptor["launched"]
            and self.time >= target["launch_time"]
        ):
            interceptor["launched"] = True
            target["status"] = "LAUNCHED"
            self.event_log.append(f"I{interceptor['id']} launched")

        if interceptor is not None and interceptor["launched"]:
            dx = target["x"] - interceptor["x"]
            dy = target["y"] - interceptor["y"]
            d = math.hypot(dx, dy)
            if d > 0:
                interceptor["vx"] = interceptor["speed"] * dx / d
                interceptor["vy"] = interceptor["speed"] * dy / d
                interceptor["x"] += interceptor["vx"] * dt
                interceptor["y"] += interceptor["vy"] * dt
            interceptor["path"].append((interceptor["x"], interceptor["y"]))

            if distance(target, interceptor) <= config.SUCCESS_RADIUS:
                target["status"] = "INTERCEPT"
                target["resolved_time"] = self.time
                self.event_log.append(
                    f"T{target['id']} intercept at {self.time:.1f}s"
                )
                return

        if target["y"] <= config.PROTECTED_LINE_Y:
            target["status"] = "FAILED"
            target["resolved_time"] = self.time
            self.event_log.append(f"T{target['id']} crossed line")

    def step(self, dt=config.DT):
        if self.complete:
            return

        for target in self.targets:
            self.update_target(target, dt)

        self.time += dt
        if all(target["status"] in TERMINAL_STATUSES for target in self.targets):
            self.complete = True
            self.event_log.append(f"Run complete at {self.time:.1f}s")

    def metrics(self):
        return {
            "targets": len(self.targets),
            "waiting": sum(1 for target in self.targets if not target["spawned"]),
            "launched": sum(
                1
                for target in self.targets
                if target["interceptor"] is not None
                and target["interceptor"]["launched"]
            ),
            "intercepted": sum(
                1 for target in self.targets if target["status"] == "INTERCEPT"
            ),
            "failed": sum(
                1 for target in self.targets if target["status"] == "FAILED"
            ),
            "unassigned": sum(
                1 for target in self.targets if target["unassigned"]
            ),
        }
