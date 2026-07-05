import plotly.graph_objects as go
import numpy as np

def plot_3d_engagement(interceptor_path, threat_path, intercept_point, title="Intercept Engagement"):
    fig = go.Figure()

    # Interceptor path
    fig.add_trace(go.Scatter3d(
        x=interceptor_path[:,0], y=interceptor_path[:,1], z=interceptor_path[:,2],
        mode='lines', line=dict(color='blue', width=4), name='Interceptor Path'
    ))

    # Threat path
    fig.add_trace(go.Scatter3d(
        x=threat_path[:,0], y=threat_path[:,1], z=threat_path[:,2],
        mode='lines', line=dict(color='red', width=4, dash='dash'), name='Threat Path'
    ))

    # Intercept point
    fig.add_trace(go.Scatter3d(
        x=[intercept_point[0]], y=[intercept_point[1]], z=[intercept_point[2]],
        mode='markers', marker=dict(size=8, color='green'), name='Intercept Point'
    ))

    # Balloon drop point (example)
    fig.add_trace(go.Scatter3d(
        x=[interceptor_path[0,0]], y=[interceptor_path[0,1]], z=[interceptor_path[0,2]],
        mode='markers', marker=dict(size=6, color='blue', symbol='diamond'), name='Balloon Drop'
    ))

    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title='X (Forward)',
            yaxis_title='Y (Lateral)',
            zaxis_title='Z (Altitude)',
            aspectmode='cube'
        ),
        margin=dict(l=0, r=0, b=0, t=40)
    )

    fig.show()
