# -*- coding: utf-8 -*-
"""
Created on Sat Jun 14 11:29:31 2025
@author: elder
"""

import numpy as np
import pandas as pd

class RadiationModel:
    def __init__(self):
        # Use a detailed published TID table; here's a dummy version
        # Replace with the real (or your) high-resolution TID data
        data = [
            # altitude_km, inclination_deg, tid_krad_per_year, seu_rating
            [500,   0.0,   2,    "low"],
            [550,  28.5,   3,    "low-medium"],
            [550,  53.0,   5,    "medium"],
            [600,  97.8,  10,    "high"],
            [600,  98.0,  10,    "high"],
            [800,  98.6,  15,    "high"],
            [1000, 63.4,  12,    "high"],
            [19100,64.8,  25,    "extreme"],
            [23222,56.0,  28,    "extreme"],
            [35786,27.0,  20,    "high"],
            [35786, 0.0,  20,    "high"]
        ]
        self.tid_table = pd.DataFrame(data, columns=["altitude_km","inclination_deg","tid_krad_per_year","seu_rating"])

    def estimate_tid(self, altitude_km, inclination_deg, years=5):
        # Use 2D interpolation across the table for a more realistic result
        df = self.tid_table
        # 1) Exact match?
        match = df[(df.altitude_km==altitude_km) & (np.isclose(df.inclination_deg,inclination_deg, atol=1e-2))]
        if not match.empty:
            row = match.iloc[0]
            tid = float(row.tid_krad_per_year) * years
            return {
                "altitude_km"       : altitude_km,
                "inclination_deg"   : inclination_deg,
                "estimated_tid_krad": tid,
                "years"             : years,
                "seu_rating"        : row.seu_rating
            }
        # 2) Bilinear interpolation on TID; nearest for seu_rating
        grid = df.pivot_table(index='altitude_km',columns='inclination_deg',values='tid_krad_per_year')
        altitudes = np.array(grid.index)
        inclinations = np.array(grid.columns)
        # Find closest grid points for bilinear interp
        alt_lo = altitudes[altitudes <= altitude_km].max() if any(altitudes <= altitude_km) else altitudes.min()
        alt_hi = altitudes[altitudes >= altitude_km].min() if any(altitudes >= altitude_km) else altitudes.max()
        inc_lo = inclinations[inclinations <= inclination_deg].max() if any(inclinations <= inclination_deg) else inclinations.min()
        inc_hi = inclinations[inclinations >= inclination_deg].min() if any(inclinations >= inclination_deg) else inclinations.max()
        # Get corners for interpolation
        corners = [grid.loc[a,i] for a in [alt_lo,alt_hi] for i in [inc_lo,inc_hi] if not pd.isna(grid.loc[a,i])]
        if len(corners)==4:
            # Bilinear interpolation
            def lerp(a,b,t): return a+(b-a)*t
            alt_t = 0 if alt_hi==alt_lo else (altitude_km-alt_lo)/(alt_hi-alt_lo)
            inc_t = 0 if inc_hi==inc_lo else (inclination_deg-inc_lo)/(inc_hi-inc_lo)
            # Corners: (alt_lo,inc_lo), (alt_hi,inc_lo), (alt_lo,inc_hi), (alt_hi,inc_hi)
            ll = grid.loc[alt_lo,inc_lo]; lh = grid.loc[alt_lo,inc_hi]
            hl = grid.loc[alt_hi,inc_lo]; hh = grid.loc[alt_hi,inc_hi]
            tid = lerp(lerp(ll,hl,alt_t), lerp(lh,hh,alt_t), inc_t) * years
        else:
            # fallback to nearest
            tid = float(df.iloc[((df.altitude_km-altitude_km)**2 + (df.inclination_deg-inclination_deg)**2).idxmin()].tid_krad_per_year) * years
        # For seu_rating, nearest
        idx = ((df.altitude_km-altitude_km)**2 + (df.inclination_deg-inclination_deg)**2).idxmin()
        seu_rating = df.loc[idx,'seu_rating']
        return {
            "altitude_km"       : altitude_km,
            "inclination_deg"   : inclination_deg,
            "estimated_tid_krad": tid,
            "years"             : years,
            "seu_rating"        : seu_rating
        }

if __name__ == "__main__":
    model = RadiationModel()
    for alt, inc in [(600, 97.8), (550, 28.5), (19100, 64.8), (700, 97.9)]:
        print(model.estimate_tid(alt, inc))