import pandas as pd

class LaunchModel:
    def __init__(self, db_path="launch/launcher_db.csv"):
        self.db = pd.read_csv(db_path)

    def classify_orbit(self, altitude_km):
        if altitude_km < 2000:
            return "LEO"
        elif altitude_km < 30000:
            return "GTO"
        else:
            return "GEO"

    def find_options(self, altitude_km, payload_mass_kg):
        orbit_class = self.classify_orbit(altitude_km)
        matches = self.db[self.db.orbit_class == orbit_class]

        feasible = matches[matches.max_payload_kg >= payload_mass_kg]
        results = []

        for _, row in feasible.iterrows():
            cost_total = row.cost_per_kg_usd * payload_mass_kg
            results.append({
                "vehicle": row.vehicle,
                "orbit_class": orbit_class,
                "max_payload_kg": row.max_payload_kg,
                "cost_per_kg_usd": row.cost_per_kg_usd,
                "total_cost_usd": cost_total
            })

        return results
