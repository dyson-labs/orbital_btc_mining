import pandas as pd
import os

class LaunchModel:
    def __init__(self, db_path=None, launch_scenario="late"):
        if db_path is None:
            # Always resolve path relative to this file's directory
            root = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(root, "launcher_db.csv")
        self.db = pd.read_csv(db_path)
        self.launch_scenario = launch_scenario

    def classify_orbit(self, altitude_km):
        if altitude_km < 2000:
            return "LEO"
        elif altitude_km < 30000:
            return "GTO"
        else:
            return "GEO"

    def find_options(self, altitude_km, payload_mass_kg, when_available="current"):
        orbit_class = self.classify_orbit(altitude_km)
        matches = self.db[
            (self.db.orbit_class == orbit_class)
            & (self.db.when_available.str.strip().str.lower() == when_available)
            ]

        feasible = matches[matches.max_payload_kg >= payload_mass_kg]
        results = []

    # --- SET PRICE FLOOR for CubeSat class (by regime) ---
    # You could pass in satellite_class explicitly if you want to support all cases.
        if payload_mass_kg <= 5:
            price_floors = {"current": 50000, "early": 50000, "late": 25000}
            min_cost = price_floors.get(when_available, 0)
        else:
                min_cost = 0

        for _, row in feasible.iterrows():
            cost_total = max(row.cost_per_kg_usd * payload_mass_kg, min_cost)
            results.append({
                "vehicle": row.vehicle,
                "orbit_class": orbit_class,
                "max_payload_kg": row.max_payload_kg,
                "cost_per_kg_usd": row.cost_per_kg_usd,
                "total_cost_usd": cost_total
        })
        
        return results
