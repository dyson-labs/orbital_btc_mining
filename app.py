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

# === ORBITS FOLDER ===
from orbits.eclipse import OrbitEnvironment

# === POWER FOLDER ===
from power.power_model import PowerModel

# === LAUNCH FOLDER ===
from launch.launch_model import LaunchModel

# === RADIATION FOLDER ===
from radiation.tid_model import RadiationModel
from radiation.Thermal import run_thermal_eclipse_model
from radiation.rf_model import (
    full_rf_visibility_simulation,
    ground_stations_by_network,
    rf_margin_plot_to_buffer,
    constant_margin_plot_to_buffer,
)

# === COSTMODEL FOLDER ===
from costmodel.cost import run_cost_model

app = Flask(__name__)

# ASIC performance defaults
DEFAULT_HASHRATE_PER_ASIC = 0.63  # TH/s
# Default efficiency is ~19 J/TH which implies about 12 W per ASIC
DEFAULT_EFFICIENCY_J_PER_TH = 19.0
DEFAULT_POWER_PER_ASIC = DEFAULT_EFFICIENCY_J_PER_TH * DEFAULT_HASHRATE_PER_ASIC

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
    ("multimw", "MultiMW Class"),
]
BITCOIN_PRICE_APPRECIATION_OPTIONS = [(str(i), f"{i}%") for i in range(-50, 51, 5)]
BITCOIN_HASH_GROWTH_OPTIONS = [(str(i), f"{i}%") for i in range(-50, 51, 5)]
NETWORK_OPTIONS = [("all", "All Ground Stations")] + [
    (n, n) for n in sorted(ground_stations_by_network.keys())
]

# Parameters for satellite classes
SAT_CLASS_LOOKUP = {
    "cubesat": dict(payload_mass_kg=1, power_w=40, solar_area_m2=0.015, asic_count=3),
    "espa": dict(payload_mass_kg=150, power_w=2200, solar_area_m2=8, asic_count=240),
    # MultiMW class parameters will be generated dynamically from these baselines
    "multimw_base_1": dict(
        payload_mass_kg=10000,
        power_w=1_000_000,
        solar_area_m2=3640,
        asic_count=111_111,
    ),
    "multimw_base_40": dict(
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
    # Baseline costs for MultiMW scaling
    "multimw_base_1": dict(
        bus_cost=10_000_000,
        payload_cost=1_700_000,
        integration_cost=5_000_000,
        comms_cost=8_000_000,
        overhead=8_000_000,
        contingency=0.15,
    ),
    "multimw_base_40": dict(
        bus_cost=15_000_000,
        payload_cost=75_000_000,
        integration_cost=10_000_000,
        comms_cost=8_000_000,
        overhead=15_000_000,
        contingency=0.15,
    ),
}


def _interp(val, x0, y0, x1, y1):
    """Linear interpolation/extrapolation helper."""
    return y0 + (y1 - y0) * (val - x0) / (x1 - x0)


def build_multimw_params(power_mw: float):
    """Return spec and cost dicts for a MultiMW satellite."""
    spec1 = SAT_CLASS_LOOKUP["multimw_base_1"]
    spec40 = SAT_CLASS_LOOKUP["multimw_base_40"]
    cost1 = SAT_COST_LOOKUP["multimw_base_1"]
    cost40 = SAT_COST_LOOKUP["multimw_base_40"]

    params = {
        "payload_mass_kg": _interp(
            power_mw, 1, spec1["payload_mass_kg"], 40, spec40["payload_mass_kg"]
        ),
        "power_w": power_mw * 1_000_000,
        "solar_area_m2": _interp(
            power_mw, 1, spec1["solar_area_m2"], 40, spec40["solar_area_m2"]
        ),
        "asic_count": int(
            round(_interp(power_mw, 1, spec1["asic_count"], 40, spec40["asic_count"]))
        ),
    }

    costs = {
        "bus_cost": _interp(power_mw, 1, cost1["bus_cost"], 40, cost40["bus_cost"]),
        "payload_cost": _interp(
            power_mw, 1, cost1["payload_cost"], 40, cost40["payload_cost"]
        ),
        "integration_cost": _interp(
            power_mw, 1, cost1["integration_cost"], 40, cost40["integration_cost"]
        ),
        "comms_cost": _interp(
            power_mw, 1, cost1["comms_cost"], 40, cost40["comms_cost"]
        ),
        "overhead": _interp(power_mw, 1, cost1["overhead"], 40, cost40["overhead"]),
        "contingency": cost1["contingency"],
    }

    return params, costs


@app.route("/")
def index():
    return render_template(
        "index.html",
        orbits=ORBIT_OPTIONS,
        launches=LAUNCH_OPTIONS,
        sat_classes=SAT_CLASS_OPTIONS,
        btc_appreciations=BITCOIN_PRICE_APPRECIATION_OPTIONS,
        btc_hash_grows=BITCOIN_HASH_GROWTH_OPTIONS,
        networks=NETWORK_OPTIONS,
        default_efficiency=round(DEFAULT_EFFICIENCY_J_PER_TH, 1),
    )


@app.route("/orbit_visuals/<int:idx>")
def orbit_visuals(idx: int):
    """Return orbit and thermal plots for the selected orbit.

    The communications mode (``ground`` or ``relay``) may be supplied via the
    ``comms`` query parameter to choose an appropriate RF margin plot.
    """
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
        rf_buf = None
        comms_mode = request.args.get("comms", "ground")
        if comms_mode == "relay":
            rf_buf = constant_margin_plot_to_buffer(margin_dB=1.0, period_s=period_s)
        elif orbit_cfg.get("tle_lines"):
            rf_buf = rf_margin_plot_to_buffer(
                orbit_cfg.get("tle_lines"), networks=None, dt=60, verbose=False
            )

        data = {
            "orbit_plot": base64.b64encode(orbit_buf.getvalue()).decode("utf-8"),
            "thermal_plot": (
                base64.b64encode(thermal_buf.getvalue()).decode("utf-8")
                if thermal_buf
                else None
            ),
            "rf_plot": (
                base64.b64encode(rf_buf.getvalue()).decode("utf-8") if rf_buf else None
            ),
        }
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/estimate_cost", methods=["POST"])
def api_estimate_cost():
    """Return mission cost estimate for current selections."""
    try:
        data = request.get_json()

        efficiency = float(data.get("efficiency", DEFAULT_EFFICIENCY_J_PER_TH))
        power_per_asic = efficiency * DEFAULT_HASHRATE_PER_ASIC

        sat_class = data.get("sat_class", "cubesat")
        if sat_class == "multimw":
            power_mw = float(data.get("multimw_power", 1))
            params, costs = build_multimw_params(power_mw)
        else:
            params = SAT_CLASS_LOOKUP.get(sat_class, SAT_CLASS_LOOKUP["cubesat"])
            costs = SAT_COST_LOOKUP.get(sat_class, SAT_COST_LOOKUP["cubesat"])

        selected_vehicle = data.get("launch")
        launch_model = LaunchModel()
        row = launch_db[launch_db["vehicle"] == selected_vehicle]
        when_available = "current"
        if not row.empty:
            when_available = row.iloc[0]["when_available"].strip().lower()
        launch_opts = launch_model.find_options(
            500, params["payload_mass_kg"], when_available=when_available
        )
        launch_cost = 0
        cost_per_kg = 0
        for o in launch_opts:
            if o["vehicle"] == selected_vehicle:
                launch_cost = o["total_cost_usd"]
                cost_per_kg = o.get("cost_per_kg_usd", 0)
                break
        if launch_cost == 0 and launch_opts:
            best = min(launch_opts, key=lambda x: x["total_cost_usd"])
            launch_cost = best["total_cost_usd"]
            cost_per_kg = best.get("cost_per_kg_usd", 0)

        capex = {
            **costs,
            "launch_cost": launch_cost,
            "asic_count": params["asic_count"],
            "hashrate_per_asic": DEFAULT_HASHRATE_PER_ASIC,
            "power_per_asic": power_per_asic,
        }
        cost_data = run_cost_model(1.0, **capex)
        cost_data["launch_cost_per_kg"] = cost_per_kg

        breakdown = {
            "Bus Cost": {
                "Structure": cost_data["bus_structure_cost"],
                "Electronics": cost_data["bus_electronics_cost"],
                "Total": cost_data["bus_cost"],
            },
            "Payload Cost": cost_data["payload_cost"],
            "Integration Cost": cost_data["integration_cost"],
            "Launch Cost": {
                "Cost per kg": cost_per_kg,
                "Cost": cost_data["launch_cost"],
            },
            "Comms Cost": cost_data["comms_cost"],
            "Overhead": cost_data["overhead"],
            "Contingency": cost_data["contingency"],
            "Total Mission Cost": cost_data["total_cost"],
        }

        return jsonify({"total_cost": cost_data["total_cost"], "breakdown": breakdown})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    try:
        data = request.get_json()

        efficiency = float(data.get("efficiency", DEFAULT_EFFICIENCY_J_PER_TH))
        power_per_asic = efficiency * DEFAULT_HASHRATE_PER_ASIC

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
        gs_network = data.get("gs_network", "all")
        if comms_mode == "relay":
            rf = {
                "mode": "relay",
                "Downlink % of mission": "100",
                "Uplink % of mission": "100",
            }
            rf_buf = constant_margin_plot_to_buffer(margin_dB=1.0, period_s=period_s)
        else:
            if orbit_cfg.get("tle_lines"):
                networks = None if gs_network == "all" else gs_network
                rf = full_rf_visibility_simulation(
                    tle=orbit_cfg.get("tle_lines"),
                    duration_days=1,
                    verbose=False,
                    networks=networks,
                )
                rf_buf = rf_margin_plot_to_buffer(
                    orbit_cfg.get("tle_lines"),
                    networks=networks,
                    dt=60,
                    verbose=False,
                )
            else:
                rf = {}
                rf_buf = None

        orbit_buf = plot_orbit_to_buffer(env)

        # --- Power and Cost Models ---
        sat_class = data.get("sat_class", "cubesat")
        if sat_class == "multimw":
            power_mw = float(data.get("multimw_power", 1))
            params, costs = build_multimw_params(power_mw)
        else:
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
        cost_per_kg = 0
        for o in launch_opts:
            if o["vehicle"] == selected_vehicle:
                launch_cost = o["total_cost_usd"]
                cost_per_kg = o.get("cost_per_kg_usd", 0)
                break
        if launch_cost == 0 and launch_opts:
            best = min(launch_opts, key=lambda x: x["total_cost_usd"])
            launch_cost = best["total_cost_usd"]
            cost_per_kg = best.get("cost_per_kg_usd", 0)

        btc_app = float(data.get("btc_appreciation", 15)) / 100.0
        btc_hash = float(data.get("btc_hash_growth", 25)) / 100.0

        mission_life = float(data.get("mission_life", 5))
        capex = {
            **costs,
            "launch_cost": launch_cost,
            "asic_count": params["asic_count"],
            "hashrate_per_asic": DEFAULT_HASHRATE_PER_ASIC,
            "power_per_asic": power_per_asic,
            "btc_price_growth": btc_app,
            "network_hashrate_growth": btc_hash,
            "mission_lifetime": mission_life,
        }
        cost_data = run_cost_model(env.sunlight_fraction, **capex)
        cost_data["launch_cost_per_kg"] = cost_per_kg

        revenue_curve = project_revenue_curve(
            env.sunlight_fraction,
            mission_life,
            params["asic_count"],
            hashrate_per_asic=capex.get("hashrate_per_asic", DEFAULT_HASHRATE_PER_ASIC),
            btc_price=capex.get("btc_price", 105000.0),
            btc_price_growth=btc_app,
            network_hashrate_ehs=capex.get("network_hashrate_ehs", 700.0),
            network_hashrate_growth=btc_hash,
            block_reward_btc=capex.get("block_reward_btc", 3.125),
        )
        roi_buf = roi_plot_to_buffer(cost_data["total_cost"], revenue_curve, step=0.25)

        rad_model = RadiationModel()
        rad_info = rad_model.estimate_tid(
            env.altitude_km or orbit_cfg.get("altitude_km", 500),
            env.inclination_deg or orbit_cfg.get("inclination_deg", 0),
            years=cost_data["mission_lifetime"],
        )

        power_model = PowerModel(
            power_density_w_m2=(
                params["power_w"] / params["solar_area_m2"]
                if params.get("solar_area_m2")
                else 200
            )
        )
        # Report the rated power for the chosen satellite class so it aligns
        # with the cost model's power value, avoiding inconsistent outputs.
        available_power = params["power_w"]

        specs = {
            "asic_count": params["asic_count"],
            "solar_area_m2": params["solar_area_m2"],
            "power_w": params["power_w"],
            "asic_efficiency_j_per_th": efficiency,
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
            "radiation": rad_info,
            "power_w": available_power,
            "cost_summary": cost_data,
            "specs": specs,
            "orbit_plot": base64.b64encode(orbit_buf.getvalue()).decode("utf-8"),
            "thermal_plot": (
                base64.b64encode(thermal_buf.getvalue()).decode("utf-8")
                if thermal_buf
                else None
            ),
            "rf_plot": (
                base64.b64encode(rf_buf.getvalue()).decode("utf-8") if rf_buf else None
            ),
            "roi_plot": base64.b64encode(roi_buf.getvalue()).decode("utf-8"),
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
