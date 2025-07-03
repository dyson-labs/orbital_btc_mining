# app.py

from flask import Flask, render_template, request, jsonify, send_file

# === ANALYSIS FOLDER ===
import base64
import json
import os
import pandas as pd
from astropy import units as u
from analysis.orbit_plot import plot_orbit_to_buffer

# === MAIN/UTILS (core orchestrator) ===
from main import run_simulation

# === ORBITS FOLDER ===
from orbits.eclipse import OrbitEnvironment

# === POWER FOLDER ===
from power.power_model import PowerModel

# === LAUNCH FOLDER ===
from launch.launch_model import LaunchModel

# === RADIATION FOLDER ===
from radiation.tid_model import RadiationModel
from radiation.Thermal import run_thermal_eclipse_model
from radiation.rf_model import full_rf_visibility_simulation

# === COSTMODEL FOLDER ===
from costmodel.cost import run_cost_model

app = Flask(__name__)

ROOT = os.path.dirname(os.path.abspath(__file__))
orbits_path = os.path.join(ROOT, "config", "orbits_to_test.json")
with open(orbits_path, "r", encoding="utf-8-sig") as f:
    try:
        ORBIT_CONFIGS = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse {orbits_path}: {e}")
ORBIT_OPTIONS = [
    (str(i), o.get("name", f"Orbit {i}")) for i, o in enumerate(ORBIT_CONFIGS)
]

launch_db = pd.read_csv(os.path.join(ROOT, "launch", "launcher_db.csv"))
vehicles = sorted(launch_db["vehicle"].unique())
LAUNCH_OPTIONS = [(v, v) for v in vehicles]
LAUNCH_REGIME_OPTIONS = [("current", "Current"), ("early", "Early"), ("late", "Late")]
SAT_CLASS_OPTIONS = [
    ("cubesat", "CubeSat"),
    ("espa", "ESPA-Class"),
    ("mw", "MW-Class"),
    ("40mw", "MMW-Class"),
]
BITCOIN_PRICE_APPRECIATION_OPTIONS = [(str(i), f"{i}%") for i in range(-50, 51, 5)]
BITCOIN_HASH_GROWTH_OPTIONS = [(str(i), f"{i}%") for i in range(-50, 51, 5)]


@app.route("/")
def index():
    return render_template(
        "index.html",
        orbits=ORBIT_OPTIONS,
        launches=LAUNCH_OPTIONS,
        regimes=LAUNCH_REGIME_OPTIONS,
        sat_classes=SAT_CLASS_OPTIONS,
        btc_appreciations=BITCOIN_PRICE_APPRECIATION_OPTIONS,
        btc_hash_grows=BITCOIN_HASH_GROWTH_OPTIONS,
    )


@app.route("/orbit_visuals/<int:idx>")
def orbit_visuals(idx: int):
    """Return orbit and thermal plots for the selected orbit."""
    if idx < 0 or idx >= len(ORBIT_CONFIGS):
        idx = 0
    orbit_cfg = ORBIT_CONFIGS[idx]
    if orbit_cfg.get("tle_lines"):
        env = OrbitEnvironment(tle_lines=orbit_cfg.get("tle_lines"))
    else:
        env = OrbitEnvironment(
            altitude_km=orbit_cfg.get("altitude_km"),
            inclination_deg=orbit_cfg.get("inclination_deg"),
        )

    period_s = env.orbit.period.to(u.s).value
    eclipse_duration_s = env.eclipse_fraction * period_s
    _, _, thermal_buf, _ = run_thermal_eclipse_model(
        orbit_period_s=period_s,
        eclipse_duration_s=eclipse_duration_s,
        t_total=period_s * 5,
        dt=60,
        plot3d=True,
        verbose=False,
    )
    orbit_buf = plot_orbit_to_buffer(env)

    data = {
        "orbit_plot": base64.b64encode(orbit_buf.getvalue()).decode("utf-8"),
        "thermal_plot": (
            base64.b64encode(thermal_buf.getvalue()).decode("utf-8")
            if thermal_buf
            else None
        ),
    }
    return jsonify(data)


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    data = request.get_json()

    idx = int(data.get("orbit", 0))
    if idx < 0 or idx >= len(ORBIT_CONFIGS):
        idx = 0
    orbit_cfg = ORBIT_CONFIGS[idx]

    if orbit_cfg.get("tle_lines"):
        env = OrbitEnvironment(tle_lines=orbit_cfg.get("tle_lines"))
    else:
        env = OrbitEnvironment(
            altitude_km=orbit_cfg.get("altitude_km"),
            inclination_deg=orbit_cfg.get("inclination_deg"),
        )

    period_s = env.orbit.period.to(u.s).value
    eclipse_duration_s = env.eclipse_fraction * period_s
    _, _, thermal_buf, temp_stats = run_thermal_eclipse_model(
        orbit_period_s=period_s,
        eclipse_duration_s=eclipse_duration_s,
        t_total=period_s * 5,
        dt=60,
        plot3d=True,
        verbose=False,
    )

    if orbit_cfg.get("tle_lines"):
        rf = full_rf_visibility_simulation(
            tle=orbit_cfg.get("tle_lines"), duration_days=1, verbose=False
        )
    else:
        rf = {}

    orbit_buf = plot_orbit_to_buffer(env)

    result = {
        "orbit": orbit_cfg.get("name"),
        "thermal_stats": temp_stats,
        "rf_summary": rf,
        "orbit_plot": base64.b64encode(orbit_buf.getvalue()).decode("utf-8"),
        "thermal_plot": (
            base64.b64encode(thermal_buf.getvalue()).decode("utf-8")
            if thermal_buf
            else None
        ),
    }
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
