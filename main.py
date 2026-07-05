import numpy as np
from simulation import run_simulation
from visualize import plot_3d_engagement

if __name__ == "__main__":
    print("Running simulation...")
    stats = run_simulation(30)  # Change number as needed
    print("Simulation complete:", stats)
    
    # Example visualization (replace with real paths from your sim)
    interceptor_path = np.array([
        [0, 0, 200],      # drop point
        [100, 10, 190],
        [300, 30, 150],
        [500, 50, 100]    # intercept point
    ])
    
    threat_path = np.array([
        [400, 40, 30],    # threat start
        [450, 45, 30],
        [500, 50, 30]     # intercept point
    ])
    
    intercept_point = np.array([500, 50, 100])
    
    plot_3d_engagement(interceptor_path, threat_path, intercept_point, title="Sample Engagement")
