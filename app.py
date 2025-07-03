# app.py

from flask import Flask, render_template, request, jsonify, send_file
import matplotlib

matplotlib.use("Agg")

# === ANALYSIS FOLDER ===
import base64
import json
import os
import pandas as pd
from astropy import units as u
from analysis.orbit_plot import plot_orbit_to_buffer
from analysis.roi_plot import project_revenue_curve, roi_plot_to_buffer

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
SAT_CLASS_OPTIONS = [
    ("cubesat", "CubeSat"),
    ("espa", "ESPA-Class"),
    ("mw", "MW-Class"),
    ("40mw", "MMW-Class"),
]
BITCOIN_PRICE_APPRECIATION_OPTIONS = [(str(i), f"{i}%") for i in range(-50, 51, 5)]
BITCOIN_HASH_GROWTH_OPTIONS = [(str(i), f"{i}%") for i in range(-50, 51, 5)]

# Parameters for satellite classes
SAT_CLASS_LOOKUP = {
    "cubesat": dict(payload_mass_kg=1, power_w=40, solar_area_m2=0.015, asic_count=3),
    "espa": dict(payload_mass_kg=150, power_w=2200, solar_area_m2=8, asic_count=240),
    "mw": dict(
        payload_mass_kg=10000, power_w=1_000_000, solar_area_m2=3640, asic_count=111_111
    ),
    "40mw": dict(
        payload_mass_kg=100000,
        power_w=40_000_000,
        solar_area_m2=145_454,
        asic_count=4_444_444,
    ),
}

SAT_COST_LOOKUP = {
    "cubesat": dict(
        bus_cost=60_000,
        payload_cost=60_000,
        integration_cost=45_000,
        comms_cost=100_000,
        overhead=160_000,
        contingency=0.25,
    ),
    "espa": dict(
        bus_cost=300_000,
        payload_cost=150_000,
        integration_cost=250_000,
        comms_cost=500_000,
        overhead=750_000,
        contingency=0.20,
    ),
    "mw": dict(
        bus_cost=10_000_000,
        payload_cost=1_700_000,
        integration_cost=5_000_000,
        comms_cost=8_000_000,
        overhead=8_000_000,
        contingency=0.15,
    ),
    "40mw": dict(
        bus_cost=15_000_000,
        payload_cost=75_000_000,
        integration_cost=10_000_000,
        comms_cost=8_000_000,
        overhead=15_000_000,
        contingency=0.15,
    ),
}


@app.route("/")
def index():
    return render_template(
        "index.html",
        orbits=ORBIT_OPTIONS,
        launches=LAUNCH_OPTIONS,
        sat_classes=SAT_CLASS_OPTIONS,
        btc_appreciations=BITCOIN_PRICE_APPRECIATION_OPTIONS,
        btc_hash_grows=BITCOIN_HASH_GROWTH_OPTIONS,
    )


@app.route("/orbit_visuals/<int:idx>")
def orbit_visuals(idx: int):
    """Return orbit and thermal plots for the selected orbit."""
    try:
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    try:
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

        comms_mode = data.get("comms_mode", "ground")
        if comms_mode == "relay":
            rf = {
                "mode": "relay",
                "Downlink % of mission": "100",
                "Uplink % of mission": "100",
            }
        else:
            if orbit_cfg.get("tle_lines"):
                rf = full_rf_visibility_simulation(
                    tle=orbit_cfg.get("tle_lines"), duration_days=1, verbose=False
                )
            else:
                rf = {}

        orbit_buf = plot_orbit_to_buffer(env)

        # --- Power and Cost Models ---
        sat_class = data.get("sat_class", "cubesat")
        params = SAT_CLASS_LOOKUP.get(sat_class, SAT_CLASS_LOOKUP["cubesat"])
        costs = SAT_COST_LOOKUP.get(sat_class, SAT_COST_LOOKUP["cubesat"])

        launch_model = LaunchModel()
        altitude = env.altitude_km or orbit_cfg.get("altitude_km", 500)
        selected_vehicle = data.get("launch")
        when_available = "current"
        row = launch_db[launch_db["vehicle"] == selected_vehicle]
        if not row.empty:
            when_available = row.iloc[0]["when_available"].strip().lower()
        launch_opts = launch_model.find_options(
            altitude,
            params["payload_mass_kg"],
            when_available=when_available,
        )
        launch_cost = 0
        for o in launch_opts:
            if o["vehicle"] == selected_vehicle:
                launch_cost = o["total_cost_usd"]
                break
        if launch_cost == 0 and launch_opts:
            launch_cost = min(o["total_cost_usd"] for o in launch_opts)

        btc_app = float(data.get("btc_appreciation", 0)) / 100.0
        btc_hash = float(data.get("btc_hash_growth", 0)) / 100.0

        capex = {
            **costs,
            "launch_cost": launch_cost,
            "asic_count": params["asic_count"],
            "btc_price_growth": btc_app,
            "network_hashrate_growth": btc_hash,
        }
        cost_data = run_cost_model(env.sunlight_fraction, **capex)

        revenue_curve = project_revenue_curve(
            env.sunlight_fraction,
            cost_data["mission_lifetime"],
            params["asic_count"],
            hashrate_per_asic=capex.get("hashrate_per_asic", 0.63),
            btc_price=capex.get("btc_price", 105000.0),
            btc_price_growth=btc_app,
            network_hashrate_ehs=capex.get("network_hashrate_ehs", 700.0),
            network_hashrate_growth=btc_hash,
            block_reward_btc=capex.get("block_reward_btc", 3.125),
        )
        roi_buf = roi_plot_to_buffer(cost_data["total_cost"], revenue_curve)

        power_model = PowerModel()
        available_power = (
            power_model.estimate_power(env.sunlight_fraction) * params["solar_area_m2"]
        )

        specs = {
            "asic_count": params["asic_count"],
            "solar_area_m2": params["solar_area_m2"],
            "power_w": params["power_w"],
            "solar_power_density_w_m2": (
                params["power_w"] / params["solar_area_m2"]
                if params["solar_area_m2"]
                else None
            ),
        }

        result = {
            "orbit": orbit_cfg.get("name"),
            "thermal_stats": temp_stats,
            "rf_summary": rf,
            "power_w": available_power,
            "cost_summary": cost_data,
            "specs": specs,
            "orbit_plot": base64.b64encode(orbit_buf.getvalue()).decode("utf-8"),
            "thermal_plot": (
                base64.b64encode(thermal_buf.getvalue()).decode("utf-8")
                if thermal_buf
                else None
            ),
            "roi_plot": base64.b64encode(roi_buf.getvalue()).decode("utf-8"),
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
