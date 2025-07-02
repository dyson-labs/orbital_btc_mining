import sys
print("INITIAL sys.path:")
for i, p in enumerate(sys.path):
    print(f"{i}: {p}")
dev_path = r"C:\Users\elder\OneDrive\Desktop\LOCAL Dyson\Python\btc_orbital_trade_study_dev"
if dev_path not in sys.path:
    sys.path.insert(0, dev_path)
print("AFTER INSERT sys.path (first 3):", sys.path[:3])

# --------- User-supplied fields (for testing/demo) ---------
form_name = "Jane Doe"
form_email = "jane@user.com"

# Example: Gather these from user input or Google Sheet
launch_regime = "early"
geo_isr_relay = True  # <-- Set based on user input

# ---- Select a satellite class for test ----
sat_class_lookup = {
    "cubesat": dict(
        payload_mass_kg=1,
        power_w=40,
        solar_area_m2=0.015,
        desc="CubeSat-class",
        asic_count=3,
    ),
    "espa": dict(
        payload_mass_kg=150,
        power_w=2200,
        solar_area_m2=8,
        desc="ESPA-class",
        asic_count=240,
    ),
    "mw": dict(
        payload_mass_kg=10_000,
        power_w=1_000_000,
        solar_area_m2=3_640,
        desc="MW-class",
        asic_count=111_111,
    ),
    "40mw": dict(
        payload_mass_kg=100_000,
        power_w=40_000_000,
        solar_area_m2=145_454,
        desc="MMW-class",
        asic_count=4_444_444,
    ),
}

satellite_class = "40mw"  # options: "cubesat", "espa", "mw", "40mw"

sat_cost_lookup = {
    "cubesat": dict(
        bus_cost=60_000,
        payload_cost=60_000,
        integration_cost=45_000,
        comms_cost=100_000,
        overhead=160_000,
        contingency=0.25
    ),
    "espa": dict(
        bus_cost=300_000,
        payload_cost=150_000, 
        integration_cost=250_000,
        comms_cost=500_000,
        overhead=750_000,
        contingency=0.20
    ),
    "mw": dict(
        bus_cost=10_000_000,
        payload_cost=1_700_000,
        integration_cost=5_000_000,
        comms_cost=8_000_000,
        overhead=8_000_000,
        contingency=0.15
    ),
    "40mw": dict(
        bus_cost=15_000_000,
        payload_cost=75_000_000,
        integration_cost=10_000_000,
        comms_cost=8_000_000,
        overhead=15_000_000,
        contingency=0.15
    ),
}

sat_costs = sat_cost_lookup.get(satellite_class, sat_cost_lookup["cubesat"])

import json
import pandas as pd
import numpy as np
import os
from orbits.eclipse import OrbitEnvironment
from radiation.tid_model import RadiationModel
from power.power_model import PowerModel
from launch.launch_model import LaunchModel

from analysis.plot_summary_table import plot_summary_table_to_buffer
from astropy import units as u
from costmodel.cost import run_cost_model
from radiation.Thermal import run_thermal_eclipse_model
from radiation.rf_model import full_rf_visibility_simulation
from analysis.one_pager import generate_one_pager

VERBOSE = False  # Control print output

def keplerian_period_seconds(alt_km, mu_earth=3.986004418e14, r_earth_km=6371.0):
    r = (r_earth_km + alt_km) * 1e3  # m
    T = 2 * np.pi * np.sqrt(r**3 / mu_earth)
    return T

def orbit_info_from_env(env):
    out = {
        "sunlight_fraction": env.sunlight_fraction,
        "eclipse_fraction": env.eclipse_fraction,
        "eclipse_minutes": env.eclipse_minutes,
    }
    try:
        r = env.orbit.r
        inc = env.orbit.inc
        out["altitude_km"] = float(np.linalg.norm(r.to(u.km).value) - 6371)
        out["inclination_deg"] = float(inc.to(u.deg).value)
    except Exception as e:
        if VERBOSE:
            print(f"Extraction failed: {e}")
        out["altitude_km"] = None
        out["inclination_deg"] = None
    return out

def orbit_label(orbit: dict, alt, inc):
    if "name" in orbit and orbit["name"]:
        return orbit["name"]
    if alt is not None and inc is not None:
        return f"{int(round(alt))} km / {inc:.1f}°"
    return "Unknown"

def load_orbit_configs(path: str = None) -> list:
    if path is None:
        root = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(root, "config", "orbits_to_test.json")
    with open(path, "r") as f:
        return json.load(f)

def run_simulation(return_df=True, verbose=False,
                   launch_regime="current", payload_mass_kg=1, power_w=40, solar_area_m2=2, geo_isr_relay=False):

    orbits          = load_orbit_configs()
    radiation_model = RadiationModel()
    power_model     = PowerModel()
    launch_model    = LaunchModel()

    all_results     = []

    for orbit in orbits:
        if verbose:
            print("\n--- ORBIT CONFIG ---")

        if "tle_lines" in orbit:
            name = orbit.get("name", "Unnamed TLE Orbit")
            env = OrbitEnvironment(tle_lines=orbit["tle_lines"])
        else:
            alt = orbit["altitude_km"]
            inc = orbit["inclination_deg"]
            name = orbit.get("name", f"{alt} km / {inc} deg")
            env = OrbitEnvironment(altitude_km=alt, inclination_deg=inc)

        orbit_info = orbit_info_from_env(env)
        alt = orbit_info["altitude_km"]
        inc = orbit_info["inclination_deg"]
        sunlight = orbit_info["sunlight_fraction"]
        eclipse_minutes = orbit_info["eclipse_minutes"]

        label = orbit_label(orbit, alt, inc)

        avg_power_w_m2 = power_model.estimate_power(sunlight)
        if alt is not None and inc is not None:
            rad = radiation_model.estimate_tid(altitude_km=alt, inclination_deg=inc)
            launch_options = launch_model.find_options(
                altitude_km=alt,
                payload_mass_kg=payload_mass_kg,
                when_available=launch_regime,
            )
            if launch_options:
                cheapest = min(launch_options, key=lambda x: x["total_cost_usd"])
                launch_cost_str = (
                    f"{cheapest['vehicle']} – ${cheapest['total_cost_usd']:,}"
                )
                launch_cost_num = cheapest['total_cost_usd']
            else:
                launch_cost_str = "Unlaunchable"
                launch_cost_num = np.nan
        else:
            rad = {"estimated_tid_krad": None, "seu_rating": "Unknown"}
            launch_cost_str = "N/A for TLE-only orbits"
            launch_cost_num = np.nan

        result = {
            "Orbit Label": label,
            "Orbit Name": name,
            "Altitude (km)": alt,
            "Inclination (deg)": inc,
            "Sunlight Fraction": round(sunlight, 3) if sunlight is not None else None,
            "Eclipse Minutes": round(eclipse_minutes, 1) if eclipse_minutes is not None else None,
            "Avg Power (W/m²)": round(avg_power_w_m2, 1) if avg_power_w_m2 is not None else None,
            "TID (krad over 5yr)": rad["estimated_tid_krad"],
            "SEU Risk": rad["seu_rating"],
            "Launch Cost": launch_cost_str,
            "Launch Cost ($)": launch_cost_num,
            "tle_lines": orbit.get("tle_lines", None),
            "Payload Mass (kg)": payload_mass_kg,
            "Power (W)": power_w,
            "Solar Area (m²)": solar_area_m2,
        }
        all_results.append(result)
        if verbose:
            for k, v in result.items():
                print(f"{k:20}: {v}")

    df = pd.DataFrame(all_results)
    if return_df:
        return df

if __name__ == "__main__":
    sat_params = sat_class_lookup.get(satellite_class, sat_class_lookup["cubesat"])
    sat_costs = sat_cost_lookup.get(satellite_class, sat_cost_lookup["cubesat"])

    df = run_simulation(
        return_df=True, verbose=VERBOSE,
        launch_regime=launch_regime,
        payload_mass_kg=sat_params["payload_mass_kg"],
        power_w=sat_params["power_w"],
        solar_area_m2=sat_params["solar_area_m2"],
        geo_isr_relay=geo_isr_relay
    )
    valid = df.dropna(subset=["Altitude (km)", "Inclination (deg)", "Launch Cost ($)"])
    plot_summary_table_to_buffer(valid)

    metrics = ["Sunlight Fraction", "Avg Power (W/m²)", "TID (krad over 5yr)", "Eclipse Minutes", "Launch Cost ($)"]
    metric_weights = {"Sunlight Fraction": 0.15, "Avg Power (W/m²)": 0.15, "TID (krad over 5yr)": 0.10, "Eclipse Minutes": 0.10, "Launch Cost ($)": 0.50}
    maximize = {"Sunlight Fraction": True, "Avg Power (W/m²)": True, "TID (krad over 5yr)": False, "Eclipse Minutes": False, "Launch Cost ($)": False}

    def norm_vals(series, maximize_):
        arr = np.array(series, dtype=float)
        return np.ones_like(arr) if arr.max() == arr.min() else (arr - arr.min()) / (arr.max() - arr.min()) if maximize_ else 1 - (arr - arr.min()) / (arr.max() - arr.min())

    score = sum(metric_weights[m] * norm_vals(valid[m], maximize[m]) for m in metrics)
    valid["Weighted Score"] = score
    best_idx = valid["Weighted Score"].idxmax()
    best_row = valid.loc[best_idx]

    # Run cost model
    solar_fraction = float(best_row["Sunlight Fraction"])
    capex_opex = {"bus_cost": 60000, "payload_cost": 60000, "launch_cost": 130000, "integration_cost": 45000, "comms_cost": 100000, "overhead": 160000, "contingency": 0.25, "btc_price": 105000}
    cost_data = run_cost_model(solar_fraction, **capex_opex)

    # RF Model & Mining Efficiency Regime Logic
    rf_dict = full_rf_visibility_simulation(
        tle=best_row["tle_lines"],
        uplink_bps=10000,
        downlink_bps=10000,
        duration_days=30,
        verbose=False
    )
    rf_downlink = rf_dict.get("downlink_fraction", 0.25)
    rf_uplink   = rf_dict.get("uplink_fraction", 0.5)

    if geo_isr_relay:
        downlink_fraction = 1.0
        uplink_fraction = 1.0
        rf_dict["Note"] = "GEO/ISR relay enabled: comms/mining at 100% regardless of regime/orbit."
    elif launch_regime == "late":
        downlink_fraction = 1.0
        uplink_fraction = 1.0
        rf_dict["Note"] = "Late regime: comms/mining at 100%."
    elif launch_regime == "early":
        downlink_fraction = 0.5 * rf_downlink + 0.5
        uplink_fraction   = 0.5 * rf_uplink + 0.5
        rf_dict["Note"] = "Early regime: comms/mining 50% orbit-based, 50% ideal."
    else:  # current
        downlink_fraction = rf_downlink
        uplink_fraction = rf_uplink
        rf_dict["Note"] = "Current regime: comms/mining from orbit/network only."

    effective_comms_fraction = min(downlink_fraction, uplink_fraction)
    solar_fraction = float(best_row["Sunlight Fraction"])
    mining_fraction = solar_fraction * effective_comms_fraction

    # --- Update RF summary for the PDF ---
    rf_dict["Effective Comms Fraction (%)"] = f"{effective_comms_fraction*100:.1f}%"
    rf_dict["Regime-Adjusted Mining Fraction (%)"] = f"{mining_fraction*100:.1f}%"
    rf_dict["Launch Regime"] = launch_regime.title()
    rf_dict["GEO/ISR Relay Enabled"] = "Yes" if geo_isr_relay else "No"

    print(f"geo_isr_relay: {geo_isr_relay}")
    print(f"sunlight_fraction: {solar_fraction}")
    print(f"effective_comms_fraction: {effective_comms_fraction}")
    print(f"mining_fraction (input to cost model): {mining_fraction}")

    # Run cost model (uses mining_fraction, not solar_fraction!)
    capex_opex = {
        "bus_cost": sat_costs["bus_cost"],
        "payload_cost": sat_costs["payload_cost"],
        "launch_cost": float(best_row["Launch Cost ($)"]),
        "integration_cost": sat_costs["integration_cost"],
        "comms_cost": sat_costs["comms_cost"],
        "overhead": sat_costs["overhead"],
        "contingency": sat_costs["contingency"],
        "btc_price": 105000,
        "asic_count": sat_params["asic_count"],
    }
    cost_data = run_cost_model(mining_fraction, **capex_opex)

    cost_dict = {
        "Bus": f"${cost_data['bus_cost']:,.0f}",
        "Payload": f"${cost_data['payload_cost']:,.0f}",
        "Launch": f"${cost_data['launch_cost']:,.0f}",
        "Integration": f"${cost_data['integration_cost']:,.0f}",
        "Communication": f"${cost_data['comms_cost']:,.0f}",
        "Overhead": f"${cost_data['overhead']:,.0f}",
        "Contingency": f"{int(cost_data['contingency']*100)}%",
        "Total Mission Cost": f"${cost_data['total_cost']:,.0f}"
    }

    perf_dict = {
        "BTC mined (total)": f"{cost_data['btc_year'] * capex_opex.get('mission_lifetime', 5):.4f}",
        "Power draw (W)": f"{cost_data['total_power']:.0f}",
        "Net profit": f"${cost_data['profit_usd']:,.0f}"
    }

    # Thermal Model
    T_hist, x, thermal_plot_buf, temp_stats = run_thermal_eclipse_model(
        orbit_period_s=5400,
        eclipse_duration_s=0,
        t_total=5 * 5400,
        dt=1.0,
        plot3d=True,
        verbose=False
    )

    thermal_dict = {
        "Max board temp (°C)": f"{temp_stats['Max board temp (°C)']:.0f}",
        "Min board temp (°C)": f"{temp_stats['Min board temp (°C)']:.0f}",
        "Avg board temp (°C)": f"{temp_stats['Avg board temp (°C)']:.0f}"
    }

    rf_dict = full_rf_visibility_simulation(
        tle=best_row["tle_lines"],
        uplink_bps=10000,
        downlink_bps=10000,
        duration_days=30,
        verbose=False
    )

    # Generate PDF one-pager
    generate_one_pager(
        filename="user_report.pdf",
        user_name=form_name,
        user_email=form_email,
        orbit_label=best_row['Orbit Label'],
        mission_params={
            "Altitude (km)": best_row['Altitude (km)'],
            "Inclination (deg)": best_row['Inclination (deg)'],
            "Sunlight Fraction": best_row['Sunlight Fraction'],
            "Eclipse Minutes": best_row['Eclipse Minutes'],
            "Launch Regime": launch_regime,
            "Satellite Class": satellite_class,
            "Payload Mass (kg)": sat_params["payload_mass_kg"],
            "Power (W)": sat_params["power_w"],
            "Solar Area (m²)": sat_params["solar_area_m2"],
            "Class Description": sat_params["desc"],
            "Mining Fraction": mining_fraction,
            "Comms Fraction": effective_comms_fraction,
            "GEO/ISR Relay Enabled": "Yes" if geo_isr_relay else "No"
        },
        cost_summary=cost_dict,
        performance_summary=perf_dict,
        thermal_summary=thermal_dict,
        rf_summary=rf_dict,
        summary_table_df=valid,
        thermal_plot_buf=thermal_plot_buf
    )
