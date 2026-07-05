import numpy as np
from config import *

def calculate_intercept_vector(pi, vi, pd, vd):
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

# Full simulation function (expand with the loop from our 3D runs)
def run_simulation(num_threats, random_seed=42):
    np.random.seed(random_seed)
    # ... (paste the full 3D loop code from our earlier successful runs)
    # Return stats dict
    return {'hits': num_threats, 'reached': 0, 'drops': num_threats}

# Add Monte Carlo wrapper here
