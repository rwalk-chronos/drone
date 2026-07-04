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


def normalize_angle(angle):
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


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
                    "ground_detected": False,
                    "track_available": False,
                    "track_available_time": None,
                    "unassigned": False,
                    "missed": False,
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
        self.target_count = max(config.MIN_TARGET_COUNT, min(config.MAX_TARGET_COUNT, count))
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

    def update_ground_track(self, target):
        if not config.GROUND_CUEING_ENABLED or not target["spawned"]:
            return

        if not target["ground_detected"] and target["y"] <= config.GROUND_SENSOR_DETECTION_Y:
            target["ground_detected"] = True
            target["track_available_time"] = self.time + config.GROUND_TRACK_DELAY
            self.event_log.append(
                f"T{target['id']} ground detected at {self.time:.1f}s; "
                f"track ready {target['track_available_time']:.1f}s"
            )

        if (
            target["ground_detected"]
            and not target["track_available"]
            and self.time >= target["track_available_time"]
        ):
            target["track_available"] = True
            target["status"] = "TRACKED"
            self.event_log.append(
                f"T{target['id']} track available at {self.time:.1f}s"
            )

    def has_track_for_assignment(self, target):
        if config.GROUND_CUEING_ENABLED:
            return target["track_available"]
        return any(
            distance(target, balloon) <= config.DETECTION_RANGE
            for balloon in self.balloons
        )

    def estimated_time_to_fob(self, target):
        if target["vy"] >= 0.0:
            return float("inf")
        return max((config.FOB_LINE_Y - target["y"]) / target["vy"], 0.0)

    def balloon_score(self, balloon, target):
        queue_delay = max(
            0.0,
            balloon["next_launch_time"] - self.time,
        ) + len(balloon["queue"]) * config.LAUNCH_INTERVAL
        travel_time = distance(target, balloon) / max(self.interceptor_speed, 1e-6)
        inventory_used = config.INTERCEPTORS_PER_BALLOON - balloon["inventory"]
        return (
            queue_delay * config.QUEUE_SCORE_WEIGHT
            + travel_time
            + inventory_used * config.INVENTORY_SCORE_WEIGHT
        )

    def available_balloons_for_assignment(self, target):
        candidates = [
            balloon for balloon in self.balloons if balloon["inventory"] > 0
        ]
        if not config.GLOBAL_ASSIGNMENT_ENABLED:
            candidates = [
                balloon
                for balloon in candidates
                if distance(target, balloon) <= config.DETECTION_RANGE
            ]
        return candidates

    def assign_interceptor(self, target):
        candidates = self.available_balloons_for_assignment(target)
        if not candidates:
            return False

        balloon = min(candidates, key=lambda node: self.balloon_score(node, target))
        balloon["inventory"] -= 1
        balloon["queue"].append(target["id"])

        initial_heading = math.atan2(target["y"] - balloon["y"], target["x"] - balloon["x"])
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
            "heading": initial_heading,
            "drop_angle_deg": config.INTERCEPTOR_DROP_ANGLE_DEG,
            "launched": False,
            "launch_time": None,
            "engage_time": None,
            "stabilized": False,
            "expired": False,
            "path": [],
            "waypoint": None,
            "last_target_point": None,
            "last_track_time": self.time,
            "tracking_status": "QUEUED",
            "aim_point": None,
            "hard_turn_remaining": config.INTERCEPTOR_HARD_TURN_MAX_SECONDS,
            "hard_turn_cooldown_until": 0.0,
            "turn_mode": "NORMAL",
        }
        self.event_log.append(
            f"T{target['id']} globally assigned B{balloon['id']} at {self.time:.1f}s; "
            f"ready {target['ready_time']:.1f}s; "
            f"TTF {self.estimated_time_to_fob(target):.1f}s"
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
        balloon["queue"] = [target_id for target_id in balloon["queue"] if target_id != target["id"]]
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
            earliest_launch = max(balloon["next_launch_time"], target["ready_time"] or 0.0)
            if self.time < earliest_launch:
                continue

            balloon["queue"].pop(0)
            interceptor = target["interceptor"]
            if interceptor is None or target["status"] == "FAILED":
                continue

            interceptor["launched"] = True
            interceptor["launch_time"] = self.time
            interceptor["engage_time"] = self.time + config.INTERCEPTOR_STABILIZATION_TIME
            target["status"] = "STABILIZING"
            balloon["next_launch_time"] = self.time + config.LAUNCH_INTERVAL
            self.event_log.append(
                f"I{interceptor['id']} dropped B{balloon['id']} at {self.time:.1f}s; "
                f"engage {interceptor['engage_time']:.1f}s"
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
        target["next_maneuver_time"] = self.time + rng.uniform(*config.MANEUVER_INTERVAL_RANGE)

    def turn_rate_for(self, interceptor, heading_error, dt):
        hard_turn_requested = (
            abs(math.degrees(heading_error)) >= config.INTERCEPTOR_HARD_TURN_TRIGGER_DEG
        )
        hard_turn_available = (
            self.time >= interceptor["hard_turn_cooldown_until"]
            and interceptor["hard_turn_remaining"] > 0.0
        )

        if hard_turn_requested and hard_turn_available:
            interceptor["turn_mode"] = "HARD"
            interceptor["hard_turn_remaining"] = max(
                0.0, interceptor["hard_turn_remaining"] - dt
            )
            if interceptor["hard_turn_remaining"] <= 0.0:
                interceptor["hard_turn_cooldown_until"] = (
                    self.time + config.INTERCEPTOR_HARD_TURN_COOLDOWN_SECONDS
                )
            return config.INTERCEPTOR_HARD_TURN_RATE_DEG_PER_SEC

        if self.time >= interceptor["hard_turn_cooldown_until"]:
            interceptor["hard_turn_remaining"] = config.INTERCEPTOR_HARD_TURN_MAX_SECONDS
        interceptor["turn_mode"] = "NORMAL"
        return config.INTERCEPTOR_NORMAL_TURN_RATE_DEG_PER_SEC

    def move_interceptor(self, target, interceptor, dt):
        aim = guidance.aim_point(
            self.guidance_mode,
            interceptor,
            target,
            self.time,
            config,
        )
        interceptor["aim_point"] = aim
        desired_heading = math.atan2(aim["y"] - interceptor["y"], aim["x"] - interceptor["x"])
        heading_error = normalize_angle(desired_heading - interceptor["heading"])
        turn_rate = self.turn_rate_for(interceptor, heading_error, dt)
        max_turn = math.radians(turn_rate) * dt
        heading_change = max(-max_turn, min(max_turn, heading_error))
        interceptor["heading"] = normalize_angle(interceptor["heading"] + heading_change)
        interceptor["vx"] = interceptor["speed"] * math.cos(interceptor["heading"])
        interceptor["vy"] = interceptor["speed"] * math.sin(interceptor["heading"])
        interceptor["x"] += interceptor["vx"] * dt
        interceptor["y"] += interceptor["vy"] * dt
        interceptor["path"].append((interceptor["x"], interceptor["y"]))

    def expire_interceptor(self, target, interceptor):
        interceptor["expired"] = True
        target["missed"] = True
        target["status"] = "UNASSIGNED"
        target["unassigned"] = True
        target["interceptor"] = None
        target["selected_balloon"] = None
        target["detected"] = True
        self.event_log.append(
            f"I{interceptor['id']} missed T{target['id']} at {self.time:.1f}s"
        )

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

        self.update_ground_track(target)
        if not target["detected"] and self.has_track_for_assignment(target):
            if not self.assign_interceptor(target) and not target["unassigned"]:
                target["unassigned"] = True
                target["status"] = "UNASSIGNED"
                self.event_log.append(
                    f"T{target['id']} unassigned: network inventory exhausted"
                )

        interceptor = target["interceptor"]
        if interceptor is not None and interceptor["launched"]:
            if self.time - interceptor["launch_time"] >= config.INTERCEPTOR_MAX_FLIGHT_TIME:
                self.expire_interceptor(target, interceptor)
            elif self.time < interceptor["engage_time"]:
                target["status"] = "STABILIZING"
                interceptor["tracking_status"] = "STABILIZING"
            else:
                if not interceptor["stabilized"]:
                    interceptor["stabilized"] = True
                    target["status"] = "LAUNCHED"
                    self.event_log.append(
                        f"I{interceptor['id']} stabilized and engaged at {self.time:.1f}s"
                    )
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
            "tracks": sum(1 for target in self.targets if target["track_available"]),
            "queued": sum(1 for target in self.targets if target["status"] == "QUEUED"),
            "stabilizing": sum(1 for target in self.targets if target["status"] == "STABILIZING"),
            "launched": sum(
                1
                for target in self.targets
                if target["interceptor"] is not None and target["interceptor"].get("stabilized")
            ),
            "intercepted": sum(1 for target in self.targets if target["status"] == "INTERCEPT"),
            "failed": sum(1 for target in self.targets if target["status"] == "FAILED"),
            "unassigned": sum(1 for target in self.targets if target["unassigned"]),
            "missed": sum(1 for target in self.targets if target["missed"]),
            "maneuvers": sum(target["maneuver_count"] for target in self.targets),
        }
