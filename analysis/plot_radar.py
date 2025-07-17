# analysis/plot_radar.py
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from plot_utils import DEFAULT_FIGSIZE
from math import pi

# ------------------------------------------------------------------
# Public function: plot_radar(df)
# ------------------------------------------------------------------
def plot_radar(df):
    """Draw a radar / spider chart from the trade-study DataFrame."""
    # --- helpers ---------------------------------------------------
    normalize = lambda s: (s - s.min()) / (s.max() - s.min())
    invert    = lambda s: 1.0 - normalize(s)           # lower = better

    # extract numeric launch cost
    df = df.copy()
    df["Launch Cost ($)"] = (
        df["Launch Cost"]
          .str.extract(r"\$([\d,]+)")[0]
          .str.replace(",", "")
          .astype(float)
    )
    df.dropna(subset=["Launch Cost ($)"], inplace=True)

    metrics = {
        "Sunlight Fraction"   : normalize(df["Sunlight Fraction"]),
        "Avg Power (W/m²)"    : normalize(df["Avg Power (W/m²)"]),
        "TID (krad over 5yr)" : normalize(df["TID (krad over 5yr)"]),
        "Eclipse Minutes"     : normalize(df["Eclipse Minutes"]),
        "Launch Cost ($)"     : normalize(df["Launch Cost ($)"])
        }


    data        = np.vstack([v.values for v in metrics.values()]).T
    labels      = list(metrics.keys())
    orbit_names = (
        df["Altitude (km)"].astype(str) + " km / " +
        df["Inclination (deg)"].astype(str) + "°"
    )

    # --- radar plot ------------------------------------------------
    N      = len(labels)
    angles = [n / float(N) * 2 * pi for n in range(N)] + [0]

    fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE, subplot_kw=dict(polar=True))

    for row, name in zip(data, orbit_names):
        values = list(row) + [row[0]]
        ax.plot(angles, values, label=name)
        ax.fill(angles, values, alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_yticks([])
    ax.set_title("Bitcoin-Mining Orbit Trade Study", fontsize=14, pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    plt.tight_layout()
    plt.show()


# ------------------------------------------------------------------
# Allow standalone plotting when this file is run directly
# ------------------------------------------------------------------
if __name__ == "__main__":
    import main                # local import avoids circularity at top level
    df = main.run_simulation(return_df=True)
    plot_radar(df)
