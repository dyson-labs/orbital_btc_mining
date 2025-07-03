import io
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from astropy import units as u

from orbits.eclipse import OrbitEnvironment


def plot_orbit_to_buffer(env: OrbitEnvironment, n_points: int = 200):
    """Return PNG buffer with a 3D orbit plot."""
    period = env.orbit.period.to(u.s).value
    times = np.linspace(0, period, n_points)
    positions = []
    for t in times:
        orb = env.orbit.propagate(t * u.s)
        positions.append(orb.r.to(u.km).value)
    positions = np.array(positions)

    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(positions[:, 0], positions[:, 1], positions[:, 2], label="Orbit")

    # draw Earth sphere
    R = 6371
    uphi = np.linspace(0, np.pi, 20)
    utheta = np.linspace(0, 2 * np.pi, 40)
    x = R * np.outer(np.sin(uphi), np.cos(utheta))
    y = R * np.outer(np.sin(uphi), np.sin(utheta))
    z = R * np.outer(np.cos(uphi), np.ones_like(utheta))
    ax.plot_surface(x, y, z, color="lightblue", alpha=0.5, linewidth=0)

    # draw equatorial plane for reference
    eq_theta = np.linspace(0, 2 * np.pi, 100)
    eq_x = R * np.cos(eq_theta)
    eq_y = R * np.sin(eq_theta)
    ax.plot(eq_x, eq_y, 0, color="gray", linestyle="--", linewidth=0.8)

    # draw north pole axis
    ax.quiver(0, 0, -R, 0, 0, 2 * R, color="k", arrow_length_ratio=0.05)

    ax.set_xlabel("X (km)")
    ax.set_ylabel("Y (km)")
    ax.set_zlabel("Z (km)")
    ax.set_title("Satellite Orbit")
    ax.view_init(elev=25, azim=60)
    ax.legend()
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf
