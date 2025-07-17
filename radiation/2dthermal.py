import io
import base64
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from plot_utils import DEFAULT_FIGSIZE

# =====================================================================
# Editable parameters
# =====================================================================
MATERIALS = {
    "solar_cells": {"thickness": 0.2, "rho": 2330.0, "cp": 700.0, "k": 150.0},
    "tim1": {"thickness": 0.2, "rho": 2200.0, "cp": 1000.0, "k": 3.0},
    # 4-layer PCB stackup (1 oz copper pour)
    "pcb_cu_top": {"thickness": 0.035, "rho": 8960.0, "cp": 385.0, "k": 400.0},
    "pcb_prepreg1": {"thickness": 0.15, "rho": 1850.0, "cp": 900.0, "k": 0.3},
    "pcb_cu_inner1": {"thickness": 0.035, "rho": 8960.0, "cp": 385.0, "k": 400.0},
    "pcb_core": {"thickness": 0.8, "rho": 1850.0, "cp": 900.0, "k": 0.3},
    "pcb_cu_inner2": {"thickness": 0.035, "rho": 8960.0, "cp": 385.0, "k": 400.0},
    "pcb_prepreg2": {"thickness": 0.15, "rho": 1850.0, "cp": 900.0, "k": 0.3},
    "pcb_cu_bottom": {"thickness": 0.035, "rho": 8960.0, "cp": 385.0, "k": 400.0},
    "asic": {"thickness": 1.0, "rho": 2330.0, "cp": 700.0, "k": 130.0},
    "tim2": {"thickness": 0.2, "rho": 2200.0, "cp": 1000.0, "k": 3.0},
    "radiator": {"thickness": 2.0, "rho": 2700.0, "cp": 900.0, "k": 205.0},
}
ASIC_WIDTH_MM = 8.0
ASIC_POWER_W = 9.0
DOMAIN_WIDTH_MM = 20.0
DX_MM = 1.0
DY_MM = 0.5
DT_S = 0.5  # requested timestep [s] -- may be reduced for stability
TOTAL_TIME_S = 90 * 60  # simulate one orbit (90 min)
ALPHA_TOP = 0.9
EPS_TOP = 0.9
EPS_BOTTOM = 0.85
VIEW_FACTOR_BOTTOM = 1.0
AREA_FACTOR_BOTTOM = 1.0
T_SPACE = 3.0
SOLAR_FLUX = 1361.0
SIGMA = 5.670374419e-8
INITIAL_T = 290.0

# Names of the layers from top (y=0) to bottom
LAYER_ORDER = [
    "solar_cells",
    "tim1",
    "pcb_cu_top",
    "pcb_prepreg1",
    "pcb_cu_inner1",
    "pcb_core",
    "pcb_cu_inner2",
    "pcb_prepreg2",
    "pcb_cu_bottom",
    "asic",
    "tim2",
    "radiator",
]

# =====================================================================
# Helper routines
# =====================================================================

def build_material_grid():
    layer_order = LAYER_ORDER
    thicknesses = [MATERIALS[l]["thickness"] for l in layer_order]
    total_thickness_mm = sum(thicknesses)
    ny = int(np.ceil(total_thickness_mm / DY_MM)) + 1
    nx = int(np.ceil(DOMAIN_WIDTH_MM / DX_MM)) + 1
    y = np.linspace(0, total_thickness_mm, ny)
    x = np.linspace(0, DOMAIN_WIDTH_MM, nx)
    k = np.zeros((ny, nx))
    rho = np.zeros((ny, nx))
    cp = np.zeros((ny, nx))
    Q = np.zeros((ny, nx))
    boundaries = np.cumsum([0] + thicknesses)
    for j, yy in enumerate(y):
        for idx in range(len(layer_order)):
            if boundaries[idx] <= yy < boundaries[idx + 1] or (
                idx == len(layer_order) - 1 and yy == boundaries[idx + 1]
            ):
                props = MATERIALS[layer_order[idx]]
                k[j, :] = props["k"]
                rho[j, :] = props["rho"]
                cp[j, :] = props["cp"]
                break
    asic_idx = layer_order.index("asic")
    asic_y_start = boundaries[asic_idx]
    asic_y_end = boundaries[asic_idx + 1]
    asic_x_start = 0.5 * (DOMAIN_WIDTH_MM - ASIC_WIDTH_MM)
    asic_x_end = asic_x_start + ASIC_WIDTH_MM
    i_start = int(asic_x_start / DX_MM)
    i_end = int(np.ceil(asic_x_end / DX_MM))
    j_start = int(asic_y_start / DY_MM)
    j_end = int(np.ceil(asic_y_end / DY_MM))
    volume_m3 = (
        ASIC_WIDTH_MM / 1000.0
        * MATERIALS["asic"]["thickness"] / 1000.0
        * 0.001
    )
    q_asic = ASIC_POWER_W / volume_m3
    for j in range(j_start, j_end):
        for i in range(i_start, i_end):
            k[j, i] = MATERIALS["asic"]["k"]
            rho[j, i] = MATERIALS["asic"]["rho"]
            cp[j, i] = MATERIALS["asic"]["cp"]
            Q[j, i] = q_asic
    asic_slice = (slice(j_start, j_end), slice(i_start, i_end))
    return x, y, k, rho, cp, Q, asic_slice, boundaries


def run_simulation(
    view_factor=VIEW_FACTOR_BOTTOM,
    area_factor=AREA_FACTOR_BOTTOM,
    total_time_s=TOTAL_TIME_S,
    dt_s=DT_S,
):
    """Run the transient 2-D thermal model."""

    x, y, k, rho, cp, Q, asic_slice, boundaries = build_material_grid()
    dx = DX_MM / 1000.0
    dy = DY_MM / 1000.0
    nx = len(x)
    ny = len(y)

    # Calculate diffusivity and stable timestep
    alpha = k / (rho * cp)
    dt_stable = (dx ** 2 * dy ** 2) / (2.0 * np.max(alpha) * (dx ** 2 + dy ** 2))
    dt = min(dt_s, 0.5 * dt_stable)

    steps = int(total_time_s / dt)
    record_steps = [0, steps // 4, steps // 2, steps - 1]
    snapshot_times = [s * dt for s in record_steps]

    T = np.full((ny, nx), INITIAL_T)
    snapshots = []
    src = Q / (rho * cp)

    for n in range(steps):
        # Pad for easy finite differences (Neumann on lateral sides)
        T_pad = np.pad(T, ((1, 1), (1, 1)), mode="edge")
        d2Tdx2 = (T_pad[1:-1, 2:] - 2 * T + T_pad[1:-1, :-2]) / dx ** 2
        d2Tdy2 = (T_pad[2:, 1:-1] - 2 * T + T_pad[:-2, 1:-1]) / dy ** 2

        bc = np.zeros_like(T)
        q_top = ALPHA_TOP * SOLAR_FLUX - EPS_TOP * SIGMA * (T[0, :] ** 4 - T_SPACE ** 4)
        bc[0, :] += q_top / (rho[0, :] * cp[0, :] * dy)
        q_bot = -EPS_BOTTOM * view_factor * area_factor * SIGMA * (T[-1, :] ** 4 - T_SPACE ** 4)
        bc[-1, :] += q_bot / (rho[-1, :] * cp[-1, :] * dy)

        T = T + dt * (alpha * (d2Tdx2 + d2Tdy2) + src + bc)

        if n in record_steps:
            snapshots.append(T.copy())
    asic_temps = T[asic_slice]
    stats = {
        "max_asic_K": float(np.max(asic_temps)),
        "avg_asic_K": float(np.mean(asic_temps)),
        "snapshot_times_s": snapshot_times,
        "actual_dt_s": dt,
    }
    return x, y, snapshots, T, stats, boundaries


def plot_temperature(x, y, temps, layer_boundaries_mm, times_s=None):
    """Plot one or more temperature snapshots with layer boundaries."""

    extent = [x[0], x[-1], y[0], y[-1]]
    fig, axes = plt.subplots(
        1,
        len(temps),
        figsize=(DEFAULT_FIGSIZE[0] * len(temps), DEFAULT_FIGSIZE[1]),
        sharey=True,
    )
    if len(temps) == 1:
        axes = [axes]

    layer_mid = 0.5 * (np.array(layer_boundaries_mm[:-1]) + np.array(layer_boundaries_mm[1:]))
    layer_labels = [l.replace("_", " ") for l in LAYER_ORDER]

    if times_s is None:
        times_s = [None] * len(temps)

    for ax, data, t in zip(axes, temps, times_s):
        im = ax.imshow(
            data,
            origin="lower",
            extent=extent,
            aspect="auto",
            cmap="inferno",
        )
        fig.colorbar(im, ax=ax, shrink=0.8, label="Temperature (K)")
        ax.set_xlabel("x (mm)")
        ax.set_ylabel("y (mm)")
        ax.set_yticks(layer_mid)
        ax.set_yticklabels(layer_labels)

        # Mark boundaries between layers
        for boundary in layer_boundaries_mm:
            ax.axhline(y=boundary, color="cyan", linestyle="--", linewidth=0.7)

        if t is not None:
            ax.text(
                0.02,
                0.95,
                f"t = {t:.1f} s",
                transform=ax.transAxes,
                color="white",
                fontsize=8,
                ha="left",
                va="top",
                bbox={"facecolor": "black", "alpha": 0.3, "boxstyle": "round"},
            )

    fig.tight_layout()
    return fig


def single_temp_plot_to_buffer(
    x,
    y,
    temp,
    vmin=None,
    vmax=None,
    layer_boundaries_mm=None,
    time_s=None,
):
    """Return a PNG buffer for one temperature snapshot."""
    extent = [x[0], x[-1], y[0], y[-1]]
    fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)
    im = ax.imshow(
        temp,
        origin="lower",
        extent=extent,
        aspect="auto",
        cmap="inferno",
        vmin=vmin,
        vmax=vmax,
    )
    fig.colorbar(im, ax=ax, shrink=0.8, label="Temperature (K)")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    if layer_boundaries_mm is not None:
        mid = 0.5 * (np.array(layer_boundaries_mm[:-1]) + np.array(layer_boundaries_mm[1:]))
        ax.set_yticks(mid)
        ax.set_yticklabels([l.replace("_", " ") for l in LAYER_ORDER])
        for boundary in layer_boundaries_mm:
            ax.axhline(y=boundary, color="cyan", linestyle="--", linewidth=0.7)
    if time_s is not None:
        ax.text(
            0.02,
            0.95,
            f"t = {time_s:.1f} s",
            transform=ax.transAxes,
            color="white",
            fontsize=8,
            ha="left",
            va="top",
            bbox={"facecolor": "black", "alpha": 0.3, "boxstyle": "round"},
        )
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200)
    plt.close(fig)
    buf.seek(0)
    return buf


def temperature_frames_base64(x, y, temps, layer_boundaries_mm=None, times_s=None):
    """Return a list of base64 PNGs for each snapshot."""
    vmin = float(np.min(temps[0]))
    vmax = float(np.max(temps[-1]))
    frames = []
    if times_s is None:
        times_s = [None] * len(temps)

    for t_img, t_sec in zip(temps, times_s):
        buf = single_temp_plot_to_buffer(
            x,
            y,
            t_img,
            vmin=vmin,
            vmax=vmax,
            layer_boundaries_mm=layer_boundaries_mm,
            time_s=t_sec,
        )
        frames.append(base64.b64encode(buf.getvalue()).decode("utf-8"))
    return frames


def temperature_plot_to_buffer(x, y, temps, layer_boundaries_mm=None, times_s=None):
    """Return a PNG buffer with the temperature plot."""

    fig = plot_temperature(x, y, temps, layer_boundaries_mm, times_s)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200)
    plt.close(fig)
    buf.seek(0)
    return buf


def temperature_plot_base64(x, y, temps, layer_boundaries_mm=None, times_s=None):
    """Return a base64-encoded PNG of the temperature plot."""

    buf = temperature_plot_to_buffer(x, y, temps, layer_boundaries_mm, times_s)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


if __name__ == "__main__":
    # Short demo run so the script finishes quickly when executed directly
    x, y, snaps, final_T, stats, boundaries = run_simulation(
        total_time_s=4.0,
        dt_s=DT_S,
    )
    times = stats.get("snapshot_times_s", [])
    fig = plot_temperature(
        x,
        y,
        snaps,
        layer_boundaries_mm=boundaries,
        times_s=times,
    )
    fig.savefig("2dthermal_result.png", dpi=200)
    plt.close(fig)
    frames = temperature_frames_base64(
        x,
        y,
        snaps,
        layer_boundaries_mm=boundaries,
        times_s=times,
    )
    for i, b64 in enumerate(frames):
        with open(f"2dthermal_frame_{i}.png", "wb") as f:
            f.write(base64.b64decode(b64))
    print(f"Max ASIC temp: {stats['max_asic_K']:.2f} K")
    print(f"Avg ASIC temp: {stats['avg_asic_K']:.2f} K")
