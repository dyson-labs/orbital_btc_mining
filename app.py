# app.py

from flask import Flask, render_template, request, jsonify

# === ANALYSIS FOLDER ===
from analysis.one_pager import generate_one_pager
from analysis.plot_summary_table import plot_summary_table_to_buffer

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

# Example dropdowns (update as you like)
ORBIT_OPTIONS = [
    ("LEO", "Low Earth Orbit (LEO)"),
    ("MEO", "Medium Earth Orbit (MEO)"),
    ("GEO", "Geostationary Orbit (GEO)")
]
LAUNCH_OPTIONS = [
    ("falcon9", "Falcon 9"),
    ("starship", "Starship"),
    ("electron", "Electron")
]
LAUNCH_REGIME_OPTIONS = [
    ("current", "Current"),
    ("early", "Early"),
    ("late", "Late")
]
SAT_CLASS_OPTIONS = [
    ("cubesat", "CubeSat"),
    ("espa", "ESPA-Class"),
    ("mw", "MW-Class"),
    ("40mw", "MMW-Class")
]
BITCOIN_PRICE_APPRECIATION_OPTIONS = [(str(i), f"{i}%") for i in range(0, 46, 5)]
BITCOIN_HASH_GROWTH_OPTIONS = [(str(i), f"{i}%") for i in range(0, 46, 5)]

@app.route('/')
def index():
    return render_template(
        'index.html',
        orbits=ORBIT_OPTIONS,
        launches=LAUNCH_OPTIONS,
        regimes=LAUNCH_REGIME_OPTIONS,
        sat_classes=SAT_CLASS_OPTIONS,
        btc_appreciations=BITCOIN_PRICE_APPRECIATION_OPTIONS,
        btc_hash_grows=BITCOIN_HASH_GROWTH_OPTIONS
    )

@app.route('/api/simulate', methods=['POST'])
def api_simulate():
    data = request.get_json()
    # Example of extracting selections
    selected_orbit = data.get('orbit')
    selected_launch = data.get('launch')
    selected_regime = data.get('regime')
    selected_sat_class = data.get('sat_class')
    btc_appreciation = float(data.get('btc_appreciation', 0)) / 100
    btc_hash_growth = float(data.get('btc_hash_growth', 0)) / 100

    # Here you would map sat_class to actual values, and pass all to your run_simulation()
    # For now, just return what was chosen:
    result = {
        "orbit": selected_orbit,
        "launch": selected_launch,
        "regime": selected_regime,
        "sat_class": selected_sat_class,
        "btc_appreciation": btc_appreciation,
        "btc_hash_growth": btc_hash_growth,
        "message": "You can now call your simulation and return real results here!"
    }
    return jsonify(result)



if __name__ == '__main__':
    app.run(debug=True)