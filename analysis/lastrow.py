"""
Dyson Labs: BTC Mining Mission Report Generator
Watches a Google Sheet, generates 1-page custom mission reports, and emails users.
"""

import os
import sys
import time

import gspread
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv
import yagmail

# --- Path/Env setup ---
BTC_STUDY_PATH = r"C:\Users\elder\OneDrive\Desktop\LOCAL Dyson\Python\btc_orbital_trade_study_dev"
sys.path.append(BTC_STUDY_PATH)
load_dotenv()

from analysis.one_pager import generate_one_pager

SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/1XHFuT4TPP81sl36p_tCEf0pvpb5YP5Gl82ZdP8oEaRg/edit?resourcekey=&gid=2120846308#gid=2120846308"
)
LAST_ROW_FILE = "last_row.txt"
POLL_INTERVAL = 60  # seconds

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")

SATELLITE_CLASSES = {
    "cubesat": {
        "payload_mass_kg": 1,
        "power_w": 40,
        "solar_area_m2": 0.015,
        "desc": "CubeSat-class",
        "asic_count": 3,
    },
    "espa": {
        "payload_mass_kg": 150,
        "power_w": 2200,
        "solar_area_m2": 8,
        "desc": "ESPA-class",
        "asic_count": 240,
    },
    "mw": {
        "payload_mass_kg": 10_000,
        "power_w": 1_000_000,
        "solar_area_m2": 3_640,
        "desc": "MW-class",
        "asic_count": 111_111,
    },
    "40mw": {
        "payload_mass_kg": 99_999,
        "power_w": 40_000_000,
        "solar_area_m2": 145_454,
        "desc": "MMW-class",
        "asic_count": 4_444_444,
    },
}

def authenticate_gsheets():
    from google_auth_oauthlib.flow import InstalledAppFlow

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    flow = InstalledAppFlow.from_client_secrets_file("client.json", SCOPES)
    creds = flow.run_local_server(port=8080)
    return creds

def get_last_processed_row():
    if os.path.exists(LAST_ROW_FILE):
        with open(LAST_ROW_FILE, "r") as f:
            return int(f.read())
    else:
        return 1  # Usually 1: skip header row

def set_last_processed_row(idx):
    with open(LAST_ROW_FILE, "w") as f:
        f.write(str(idx))

def process_row(row):
    row = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}
    print("Processing row:", row)
    print("\n--- Raw Google Sheet Keys ---")
    for key in row.keys():
        print(repr(key))

    user_name = f"{row.get('First Name', '')} {row.get('Last name', '')}".strip()
    user_email = row.get("Email")
    if not user_email:
        print("No email found in row, skipping.")
        return

    SATELLITE_CLASS_MAP = {
        "CubeSat": "cubesat",
        "ESPA-class": "espa",
        "MegaWatt-class": "mw",
        "40MegaWatt-class": "40mw"
    }
    LAUNCH_REGIME_MAP = {
        "Current launch options": "current",
        "Coming soon launch options": "early",
        "Future launch options": "late",   # <-- Map "future" regime to "late"
        }


    sat_class_raw = (
        row.get("What class of satellite would you like to review?")
        or row.get("Satellite Class")
        or "CubeSat"
    )
    sat_class = SATELLITE_CLASS_MAP.get(sat_class_raw, "cubesat")

    launch_regime_raw = (
        row.get("What launch regime would you like to review?")
        or row.get("Launch Cost Regime")
        or "Current launch options"
    )
    launch_regime = LAUNCH_REGIME_MAP.get(launch_regime_raw, "current")

    geo_isr_raw = row.get("Use GEO/ISR (intersatellite relays) in study?", "No")
    geo_isr_relay = geo_isr_raw.strip().lower() in ["yes", "y", "true"]

    print(f"Parsed launch_regime: {launch_regime} (raw: {launch_regime_raw})")
    print(f"Parsed sat_class: {sat_class} (raw: {sat_class_raw})")
    print(f"Parsed geo_isr_relay: {geo_isr_relay} (raw: {geo_isr_raw})")

    params = SATELLITE_CLASSES[sat_class]

    mission_params = {
        "First Name": row.get("First Name", ""),
        "Last Name": row.get("Last name", ""),
        "Email": user_email,
        "Phone": row.get("Phone number", ""),
        "Signed up for updates?": row.get("Sign up for news and updates?", ""),
        "Interested Services": row.get("What services are you interested in? ", ""),
        "Budget": row.get("What is your budget?", ""),
        "How did you hear about us?": row.get("How did you hear about us? ", ""),
        "Message": row.get("Message", ""),
        "Timestamp": row.get("Timestamp", ""),
        "Launch Cost Regime": launch_regime,
        "Satellite Class": SATELLITE_CLASSES[sat_class]["desc"],
        "Satellite Mass (kg)": params["payload_mass_kg"],
        "Satellite Power (W)": params["power_w"],
        "Solar Array Area (m²)": params["solar_area_m2"],
        "GEO/ISR Relay Used": "Yes" if geo_isr_relay else "No",
    }

    # ----------------------
    # Run the real pipeline!
    # ----------------------
    import pandas as pd
    import numpy as np
    from orbits.eclipse import OrbitEnvironment
    from radiation.tid_model import RadiationModel
    from power.power_model import PowerModel
    from launch.launch_model import LaunchModel
    from costmodel.cost import run_cost_model
    from radiation.Thermal import run_thermal_eclipse_model
    from radiation.rf_model import full_rf_visibility_simulation
    from main import run_simulation

    df = run_simulation(
        return_df=True,
        verbose=False,
        launch_regime=launch_regime,
        payload_mass_kg=params["payload_mass_kg"],
        power_w=params["power_w"],
        solar_area_m2=params["solar_area_m2"],
        geo_isr_relay=geo_isr_relay,
    )
    valid = df.dropna(subset=["Altitude (km)", "Inclination (deg)", "Launch Cost ($)"])
    metrics = [
        "Sunlight Fraction",
        "Avg Power (W/m²)",
        "TID (krad over 5yr)",
        "Eclipse Minutes",
        "Launch Cost ($)",
    ]
    metric_weights = {
        "Sunlight Fraction": 0.15,
        "Avg Power (W/m²)": 0.15,
        "TID (krad over 5yr)": 0.10,
        "Eclipse Minutes": 0.10,
        "Launch Cost ($)": 0.50,
    }
    maximize = {
        "Sunlight Fraction": True,
        "Avg Power (W/m²)": True,
        "TID (krad over 5yr)": False,
        "Eclipse Minutes": False,
        "Launch Cost ($)": False,
    }

    def norm_vals(series, maximize_):
        arr = np.array(series, dtype=float)
        if arr.max() == arr.min():
            return np.ones_like(arr)
        normed = (arr - arr.min()) / (arr.max() - arr.min())
        return normed if maximize_ else 1 - normed

    score = sum(metric_weights[m] * norm_vals(valid[m], maximize[m]) for m in metrics)
    valid["Weighted Score"] = score
    best_idx = valid["Weighted Score"].idxmax()
    best_row = valid.loc[best_idx]

    # --- Calculate effective comms and mining fraction as in main.py ---
    rf_dict = full_rf_visibility_simulation(
        tle=best_row["tle_lines"],
        uplink_bps=10000,
        downlink_bps=10000,
        duration_days=30,
        verbose=False,
    )
    rf_downlink = rf_dict.get("downlink_fraction", 0.25)
    rf_uplink = rf_dict.get("uplink_fraction", 0.5)

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
        uplink_fraction = 0.5 * rf_uplink + 0.5
        rf_dict["Note"] = "Early regime: comms/mining 50% orbit-based, 50% ideal."
    else:  # current
        downlink_fraction = rf_downlink
        uplink_fraction = rf_uplink
        rf_dict["Note"] = "Current regime: comms/mining from orbit/network only."

    effective_comms_fraction = min(downlink_fraction, uplink_fraction)
    solar_fraction = float(best_row["Sunlight Fraction"])
    mining_fraction = solar_fraction * effective_comms_fraction

    # Update RF summary fields for PDF (optional)
    rf_dict["Effective Comms Fraction (%)"] = f"{effective_comms_fraction*100:.1f}%"
    rf_dict["Regime-Adjusted Mining Fraction (%)"] = f"{mining_fraction*100:.1f}%"
    rf_dict["Launch Regime"] = launch_regime.title()
    rf_dict["GEO/ISR Relay Enabled"] = "Yes" if geo_isr_relay else "No"

    # Get cost values for correct satellite class
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

    capex_opex = {
        **sat_cost_lookup.get(sat_class, sat_cost_lookup["cubesat"]),
        "btc_price": 105000,
        "launch_cost": float(best_row["Launch Cost ($)"]),
        "asic_count": params["asic_count"],
    }

    # 🚨 HERE'S THE KEY LINE: Pass mining_fraction, not solar_fraction
    cost_data = run_cost_model(mining_fraction, **capex_opex)

    cost_dict = {
        "Bus": f"${cost_data['bus_cost']:,.0f}",
        "Payload": f"${cost_data['payload_cost']:,.0f}",
        "Launch": f"${cost_data['launch_cost']:,.0f}",
        "Integration": f"${cost_data['integration_cost']:,.0f}",
        "Communication": f"${cost_data.get('comms_cost', 0):,.0f}",
        "Overhead": f"${cost_data['overhead']:,.0f}",
        "Contingency": f"{int(cost_data['contingency']*100)}%",
        "Total Mission Cost": f"${cost_data['total_cost']:,.0f}",
    }
    perf_dict = {
        "BTC mined (total)": f"{cost_data['btc_year'] * capex_opex.get('mission_lifetime', 5):.4f}",
        "Power draw (W)": f"{cost_data['total_power']:.0f}",
        "Net profit": f"${cost_data['profit_usd']:,.0f}",
    }

    # Thermal Model
    T_hist, x, thermal_plot_buf, temp_stats = run_thermal_eclipse_model(
        orbit_period_s=5400,
        eclipse_duration_s=0,
        t_total=5 * 5400,
        dt=1.0,
        plot3d=True,
        verbose=False,
    )
    thermal_dict = {
        "Max board temp (°C)": f"{temp_stats['Max board temp (°C)']:.0f}",
        "Min board temp (°C)": f"{temp_stats['Min board temp (°C)']:.0f}",
        "Avg board temp (°C)": f"{temp_stats['Avg board temp (°C)']:.0f}",
    }

    print("\n=== DEBUG DUMP BEFORE PDF ===")
    print("User Name:", user_name)
    print("User Email:", user_email)
    print("Orbit Label:", best_row['Orbit Label'])
    print("Mission Params:", mission_params)
    print("Cost Summary:", cost_dict)
    print("Performance Summary:", perf_dict)
    print("Thermal Summary:", thermal_dict)
    print("RF Summary:", rf_dict)
    print("Thermal Plot Buf Exists:", thermal_plot_buf is not None)

    # --- Generate the PDF report ---
    output_pdf_path = os.path.join(BTC_STUDY_PATH, "user_reports")
    os.makedirs(output_pdf_path, exist_ok=True)
    pdf_filename = os.path.join(output_pdf_path, f"{user_email}_report.pdf")
    generate_one_pager(
        filename=pdf_filename,
        user_name=user_name,
        user_email=user_email,
        orbit_label=best_row["Orbit Label"],
        mission_params=mission_params,
        cost_summary=cost_dict,
        performance_summary=perf_dict,
        thermal_summary=thermal_dict,
        rf_summary=rf_dict,
        summary_table_df=valid,
        thermal_plot_buf=thermal_plot_buf,
    )
    print("PDF generated:", pdf_filename)

    # --- Email PDF to user ---
    subject = "Your Custom Bitcoin Mining Mission Report"
    body = (
        f"Hi {user_name or 'there'},\n\n"
        "Attached is your custom mission report. Want to check our math? "
        "https://github.com/dyson-labs/orbital_btc_mining\n"
        "Thank you for using Dyson Labs!\n\n- Calvin"
    )
    yag = yagmail.SMTP(SENDER_EMAIL, APP_PASSWORD)
    yag.send(
        to=user_email,
        subject=subject,
        contents=body,
        attachments=[pdf_filename],
    )
    print(f"Sent email to {user_email} with report {pdf_filename}")




def main():
    creds = authenticate_gsheets()
    gc = gspread.authorize(creds)
    worksheet = gc.open_by_url(SHEET_URL).get_worksheet(0)
    while True:
        data = worksheet.get_all_records()
        last_idx = get_last_processed_row()
        print(f"Sheet has {len(data)} rows. Last processed: {last_idx}")
        if len(data) > last_idx:
            for i in range(last_idx, len(data)):
                row = data[i]
                process_row(row)
            set_last_processed_row(len(data))
        else:
            print("No new responses.")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
