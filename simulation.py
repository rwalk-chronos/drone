import numpy as np
from config import *

class DroneResponseSimulation:
    def __init__(self):
        self.reset()

    def reset(self):
        self.time = 0.0
        self.interceptors = []
        self.threats = []
        self.stats = {'hits': 0, 'reached': 0, 'drops': 0}

    def calculate_intercept_vector(self, pi, vi, pd, vd):
        R = pd - pi
        a = np.dot(vd, vd) - vi**2
        b = 2 * np.dot(R, vd)
        c = np.dot(R, R)
        disc = b**2 - 4*a*c
        if disc < 0:
            return None
        sqrt_disc = np.sqrt(max(disc, 0))
        ts = []
        if abs(a) < 1e-9:
            if abs(b) > 1e-9:
                t = -c / b
                if t > 0: ts.append(t)
        else:
            t1 = (-b + sqrt_disc) / (2 * a)
            t2 = (-b - sqrt_disc) / (2 * a)
            ts = [t for t in [t1, t2] if t > 0]
        if not ts:
            return None
        t = min(ts)
        if t > 120:
            return None
        intercept_pos = pd + vd * t
        vi_vec = (intercept_pos - pi) / t
        return vi_vec

    def run_simulation(self, num_threats, random_seed=42):
        np.random.seed(random_seed)
        self.reset()

        # Initialize threats
        for i in range(num_threats):
            y = np.random.uniform(-300, 300)
            x_start = np.random.uniform(1200, 2200)
            vx = -THREAT_SPEED
            vy = np.random.uniform(-5, 5)
            vz = np.random.uniform(-2, 2)
            self.threats.append({'pos': np.array([x_start, y, THREAT_ALT]), 'vel': np.array([vx, vy, vz]), 
                                 'active': True, 'destroyed_by': None, 'assigned': False, 'last_jink': 0.0})

        # Initialize interceptors on balloons
        balloon_positions = [
            np.array([PICKET_X - 100, -150, BALLOON_ALT]),
            np.array([PICKET_X + 150, 0, BALLOON_ALT]),
            np.array([PICKET_X - 100, 150, BALLOON_ALT])
        ]
        for b in range(len(balloon_positions)):
            for i in range(10):  # 10 per balloon
                pos = balloon_positions[b] + np.random.uniform(-20,20,3)
                self.interceptors.append({'pos': pos.copy(), 'vel': np.zeros(3), 'active': False,
                                         'time_left': 180.0, 'hits': 0, 'last_revector': 0.0, 'drop_time': None})

        # Main simulation loop
        while self.time < MAX_TIME and any(t['active'] for t in self.threats):
            # Update threats + jinks
            for t in self.threats:
                if t['active']:
                    t['pos'] += t['vel'] * DT
                    if t['pos'][0] < 50:
                        t['active'] = False
                        t['destroyed_by'] = 'reached FOB'
                        self.stats['reached'] += 1
                    if self.time - t['last_jink'] >= JINK_INTERVAL:
                        t['vel'] += np.random.uniform(-JINK_STRENGTH, JINK_STRENGTH, 3)
                        t['vel'][0] = max(t['vel'][0], -THREAT_SPEED * 1.2)
                        t['last_jink'] = self.time

            # Update active interceptors
            for inter in self.interceptors:
                if inter['active'] and inter['time_left'] > 0:
                    inter['pos'] += inter['vel'] * DT
                    inter['time_left'] -= DT
                    if inter['time_left'] <= 0:
                        inter['active'] = False

            # Selective drops
            active_threats = [t for t in self.threats if t['active'] and not t['assigned']]
            for threat in active_threats:
                dormant = [inter for inter in self.interceptors if not inter['active']]
                if dormant:
                    closest_inter = min(dormant, key=lambda ii: np.linalg.norm(ii['pos'] - threat['pos']))
                    if np.linalg.norm(closest_inter['pos'] - threat['pos']) < DETECTION_RANGE:
                        closest_inter['active'] = True
                        self.stats['drops'] += 1
                        threat['assigned'] = True
                        closest_inter['drop_time'] = self.time
                        direction = threat['pos'] - closest_inter['pos']
                        direction[2] = -np.abs(direction[2]) * 0.2  # 10° bias
                        if np.linalg.norm(direction) > 0.1:
                            closest_inter['vel'] = (direction / np.linalg.norm(direction)) * VI_SPEED
                        else:
                            closest_inter['vel'] = np.array([0, 0, -VI_SPEED * 0.2])
                        closest_inter['last_revector'] = self.time + SPIN_UP_DELAY

            # Re-vectoring
            for inter in self.interceptors:
                if inter['active'] and inter['time_left'] > 0:
                    if inter['drop_time'] is not None and self.time < inter['drop_time'] + SPIN_UP_DELAY:
                        continue
                    if self.time - inter['last_revector'] >= REVECTOR_INTERVAL:
                        active_th = [t for t in self.threats if t['active']]
                        if active_th:
                            closest = min(active_th, key=lambda tt: np.linalg.norm(inter['pos'] - tt['pos']))
                            vi_vec = self.calculate_intercept_vector(inter['pos'], VI_SPEED, closest['pos'], closest['vel'])
                            if vi_vec is not None:
                                inter['vel'] = vi_vec
                            else:
                                d = closest['pos'] - inter['pos']
                                inter['vel'] = (d / np.linalg.norm(d)) * VI_SPEED if np.linalg.norm(d) > 0.1 else np.zeros(3)
                        inter['last_revector'] = self.time

                    # Hit check with proximity charge
                    for t in self.threats:
                        if t['active'] and np.linalg.norm(inter['pos'] - t['pos']) < R_HIT:
                            t['active'] = False
                            t['destroyed_by'] = 'interceptor'
                            inter['hits'] += 1
                            self.stats['hits'] += 1
                            if inter['hits'] >= 1:
                                inter['active'] = False
                            break

            self.time += DT

        return self.stats

# Example usage
if __name__ == "__main__":
    sim = DroneResponseSimulation()
    stats = sim.run_simulation(30)
    print("Simulation complete:", stats)
