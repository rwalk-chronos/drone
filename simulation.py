"""Core kinematic simulation engine, independent of Pygame rendering."""

import math
import random
from copy import deepcopy

import config
import guidance


TERMINAL_STATUSES = {"INTERCEPT", "FAILED"}
MANEUVER_MODES = ["straight", "random"]


def distance(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


class Simulation:
    def __init__(self):
        self.target_count = config.DEFAULT_TARGET_COUNT
        self.seed = config.DEFAULT_RANDOM_SEED
        self.staggered_arrival = config.DEFAULT_STAGGERED_ARRIVAL
        self.interceptor_speed = config.INITIAL_INTERCEPTOR_SPEED
        self.guidance_mode = config.DEFAULT_GUIDANCE_MODE
        self.maneuver_mode = config.DEFAULT_MANEUVER_MODE
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
                    "speed": speed,
                    "spawn_time": spawn_time,
                }
            )

        return templates

    def reset(self, message="Simulation restarted"):
        self.time = 0.0
        self.complete = False
        self.event_log = [
            f"{message} | seed={self.seed} targets={self.target_count} "
            f"speed={self.interceptor_speed:.0f} guidance={self.guidance_mode} "
            f"maneuver={self.maneuver_mode} staggered={self.staggered_arrival}"
        ]

        self.balloons = []
        for template in config.BALLOON_TEMPLATES:
            balloon = deepcopy(template)
            balloon.update(
                {
                    "inventory": config.INTERCEPTORS_PER_BALLOON,
                    "queue": [],
                    "next_launch_time": 0.0,
                }
            )
            self.balloons.append(balloon)

        self.targets = []
        for index, template in enumerate(self.generate_target_templates(), start=1):
            target = deepcopy(template)
            maneuver_rng = random.Random(self.seed * 1000 + index)
            target.update(
                {
                    "id": index,
                    "status": "WAITING" if target["spawn_time"] > 0 else "SEARCHING",
                    "spawned": target["spawn_time"] <= 0,
                    "detected": False,
                    "unassigned": False,
                    "selected_balloon": None,
                    "path": [],
                    "history": [],
                    "interceptor": None,
                    "ready_time": None,
                    "resolved_time": None,
                    "reservation_released": False,
                    "maneuver_rng": maneuver_rng,
                    "next_maneuver_time": target["spawn_time"]
                    + maneuver_rng.uniform(*config.MANEUVER_INTERVAL_RANGE),
                    "maneuver_count": 0,
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

    def cycle_guidance_mode(self):
        modes = guidance.GUIDANCE_MODES
        current_index = modes.index(self.guidance_mode)
        self.guidance_mode = modes[(current_index + 1) % len(modes)]
        self.reset("Guidance mode changed")

    def cycle_maneuver_mode(self):
        current_index = MANEUVER_MODES.index(self.maneuver_mode)
        self.maneuver_mode = MANEUVER_MODES[(current_index + 1) % len(MANEUVER_MODES)]
        self.reset("Target maneuver mode changed")

    def adjust_interceptor_speed(self, delta):
        self.interceptor_speed = max(5.0, self.interceptor_speed + delta)
        for target in self.targets:
            interceptor = target["interceptor"]
            if interceptor is not None:
                interceptor["speed"] = self.interceptor_speed

    def target_by_id(self, target_id):
        return next(target for target in self.targets if target["id"] == target_id)

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
        balloon["queue"].append(target["id"])

        target["detected"] = True
        target["unassigned"] = False
        target["status"] = "QUEUED"
        target["selected_balloon"] = balloon
        target["ready_time"] = self.time + config.LAUNCH_DELAY
        target["interceptor"] = {
            "id": target["id"],
            "x": balloon["x"],
            "y": balloon["y"],
            "vx": 0.0,
            "vy": 0.0,
            "speed": self.interceptor_speed,
            "launched": False,
            "path": [],
            "waypoint": None,
            "last_target_point": None,
            "last_track_time": self.time,
            "tracking_status": "QUEUED",
            "aim_point": None,
        }
        self.event_log.append(
            f"T{target['id']} queued B{balloon['id']} at {self.time:.1f}s; "
            f"ready {target['ready_time']:.1f}s"
        )
        return True

    def release_reservation(self, target):
        balloon = target["selected_balloon"]
        interceptor = target["interceptor"]
        if (
            balloon is None
            or interceptor is None
            or interceptor["launched"]
            or target["reservation_released"]
        ):
            return

        balloon["queue"] = [
            target_id for target_id in balloon["queue"] if target_id != target["id"]
        ]
        balloon["inventory"] += 1
        target["reservation_released"] = True
        self.event_log.append(
            f"T{target['id']} removed from B{balloon['id']} queue at {self.time:.1f}s"
        )

    def process_launch_queues(self):
        for balloon in self.balloons:
            while balloon["queue"]:
                target = self.target_by_id(balloon["queue"][0])
                if target["status"] == "FAILED":
                    balloon["queue"].pop(0)
                    continue
                break

            if not balloon["queue"]:
                continue

            target = self.target_by_id(balloon["queue"][0])
            earliest_launch = max(
                balloon["next_launch_time"],
                target["ready_time"] or 0.0,
            )
            if self.time < earliest_launch:
                continue

            balloon["queue"].pop(0)
            interceptor = target["interceptor"]
            if interceptor is None or target["status"] == "FAILED":
                continue

            interceptor["launched"] = True
            target["status"] = "LAUNCHED"
            balloon["next_launch_time"] = self.time + config.LAUNCH_INTERVAL
            self.event_log.append(
                f"I{interceptor['id']} launched B{balloon['id']} at {self.time:.1f}s; "
                f"next slot {balloon['next_launch_time']:.1f}s"
            )

    def apply_target_maneuver(self, target):
        if self.maneuver_mode != "random" or self.time < target["next_maneuver_time"]:
            return

        rng = target["maneuver_rng"]
        speed = target["speed"]
        horizontal_limit = speed * config.MANEUVER_HORIZONTAL_FRACTION
        target["vx"] = rng.uniform(-horizontal_limit, horizontal_limit)
        target["vy"] = -math.sqrt(max(speed * speed - target["vx"] * target["vx"], 0.0))
        target["maneuver_count"] += 1
        target["next_maneuver_time"] = self.time + rng.uniform(
            *config.MANEUVER_INTERVAL_RANGE
        )

    def move_interceptor(self, target, interceptor, dt):
        aim = guidance.aim_point(
            self.guidance_mode,
            interceptor,
            target,
            self.time,
            config,
        )
        interceptor["aim_point"] = aim
        dx = aim["x"] - interceptor["x"]
        dy = aim["y"] - interceptor["y"]
        d = math.hypot(dx, dy)
        if d > 0:
            interceptor["vx"] = interceptor["speed"] * dx / d
            interceptor["vy"] = interceptor["speed"] * dy / d
            interceptor["x"] += interceptor["vx"] * dt
            interceptor["y"] += interceptor["vy"] * dt
        interceptor["path"].append((interceptor["x"], interceptor["y"]))

    def update_target(self, target, dt):
        if target["status"] in TERMINAL_STATUSES:
            return

        if not target["spawned"]:
            if self.time < target["spawn_time"]:
                return
            target["spawned"] = True
            target["status"] = "SEARCHING"
            self.event_log.append(f"T{target['id']} entered at {self.time:.1f}s")

        self.apply_target_maneuver(target)

        target["x"] += target["vx"] * dt
        target["y"] += target["vy"] * dt
        target["path"].append((target["x"], target["y"]))
        target["history"].append({"time": self.time, "x": target["x"], "y": target["y"]})
        while target["history"] and self.time - target["history"][0]["time"] > 20.0:
            target["history"].pop(0)

        if not target["detected"]:
            in_any_detection_zone = any(
                distance(target, balloon) <= config.DETECTION_RANGE
                for balloon in self.balloons
            )
            if in_any_detection_zone:
                if not self.assign_interceptor(target) and not target["unassigned"]:
                    target["unassigned"] = True
                    target["status"] = "UNASSIGNED"
                    self.event_log.append(
                        f"T{target['id']} unassigned: no local inventory"
                    )

        interceptor = target["interceptor"]
        if interceptor is not None and interceptor["launched"]:
            self.move_interceptor(target, interceptor, dt)

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
            self.release_reservation(target)
            self.event_log.append(f"T{target['id']} crossed line at {self.time:.1f}s")

    def step(self, dt=config.DT):
        if self.complete:
            return

        self.process_launch_queues()

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
            "queued": sum(1 for target in self.targets if target["status"] == "QUEUED"),
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
            "maneuvers": sum(target["maneuver_count"] for target in self.targets),
        }
