# --------- User-supplied fields (placeholders, e.g., from web form) ---------
form_name = "Jane Doe"
form_email = "jane@user.com"
# ---------------------------------------------------------------------------

import json
import pandas as pd
import numpy as np
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

def load_orbit_configs(path: str = "config/orbits_to_test.json") -> list:
    with open(path, "r") as f:
        return json.load(f)

def run_simulation(return_df: bool = False, verbose: bool = False):
    orbits          = load_orbit_configs()
    radiation_model = RadiationModel()
    power_model     = PowerModel()
    launch_model    = LaunchModel()
    payload_mass_kg = 1
    all_results     = []

    for orbit in orbits:
        if verbose:
            print("\n--- ORBIT CONFIG ---")
        # Build environment (env)
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
            "Orbit Label"         : label,
            "Orbit Name"          : name,
            "Altitude (km)"       : alt,
            "Inclination (deg)"   : inc,
            "Sunlight Fraction"   : round(sunlight, 3) if sunlight is not None else None,
            "Eclipse Minutes"     : round(eclipse_minutes, 1) if eclipse_minutes is not None else None,
            "Avg Power (W/m²)"    : round(avg_power_w_m2, 1) if avg_power_w_m2 is not None else None,
            "TID (krad over 5yr)" : rad["estimated_tid_krad"],
            "SEU Risk"            : rad["seu_rating"],
            "Launch Cost"         : launch_cost_str,
            "Launch Cost ($)"     : launch_cost_num,
            "tle_lines"           : orbit.get("tle_lines", None)  # <-- Add TLE lines if present
        }
        all_results.append(result)
        if verbose:
            for k, v in result.items():
                print(f"{k:20}: {v}")

    df = pd.DataFrame(all_results)
    if return_df:
        return df

# ---------------------------------------------------------------------------
# Script entry-point
# ---------------------------------------------------------------------------
# Script entry-point
if __name__ == "__main__":
    df = run_simulation(return_df=True, verbose=VERBOSE)
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
        eclipse_duration_s=1800,
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
            "Eclipse Minutes": best_row['Eclipse Minutes']
        },
        cost_summary=cost_dict,
        performance_summary=perf_dict,
        thermal_summary=thermal_dict,
        rf_summary=rf_dict,
        summary_table_df=valid,
        thermal_plot_buf=thermal_plot_buf
    )
