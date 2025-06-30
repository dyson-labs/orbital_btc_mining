import numpy as np
import matplotlib.pyplot as plt
import io

def plot_summary_table_to_buffer(
    df,
    fig_width=7.5,
    fig_height_per_row=1.2,
    font_scale=1.0,
    max_label_len=30
):
    """
    Returns a PNG buffer of the summary plot, optimized for inclusion in a one-pager PDF.
    Includes a title stating clearly that it is a comparison of orbits within the database.
    """
    # --- CONFIGURATION ---
    metrics = [
        "Sunlight Fraction",
        "Avg Power (W/m²)",
        "TID (krad over 5yr)",
        "Eclipse Minutes",
        "Launch Cost ($)"
    ]
    metric_weights = {
        "Sunlight Fraction": 0.15,
        "Avg Power (W/m²)": 0.15,
        "TID (krad over 5yr)": 0.10,
        "Eclipse Minutes": 0.10,
        "Launch Cost ($)": 0.50
    }
    maximize = {
        "Sunlight Fraction": True,
        "Avg Power (W/m²)": True,
        "TID (krad over 5yr)": False,
        "Eclipse Minutes": False,
        "Launch Cost ($)": False
    }

    def norm_vals(series, maximize_):
        arr = np.array(series, dtype=float)
        if arr.max() == arr.min():
            return np.ones_like(arr)
        normed = (arr - arr.min()) / (arr.max() - arr.min())
        return normed if maximize_ else 1 - normed

    # --- Compute scores & find best ---
    score = np.zeros(len(df))
    for m in metrics:
        vals = norm_vals(df[m], maximize[m])
        score += metric_weights[m] * vals
    df = df.copy()
    df["Weighted Score"] = score
    best_idx = int(df["Weighted Score"].idxmax())

    # --- Prep plotting ---
    n_rows = len(metrics) + 1  # +1 for weighted score
    fig_height = fig_height_per_row * n_rows
    plt.rcParams.update({
        'font.size': 13 * font_scale,
        'axes.labelsize': 13 * font_scale,
        'axes.titlesize': 14 * font_scale
    })
    fig, axes = plt.subplots(n_rows, 1, figsize=(fig_width, fig_height))
    fig.subplots_adjust(left=0.05, right=0.9, hspace=1.25, top=0.90, bottom=0.12)
    # --- Main title at the top of the figure ---
    fig.suptitle("   Comparison of Orbits within Database", fontsize=28 * font_scale, fontweight='bold', y=0.98)

    def short_label(s):
        return s if len(s) <= max_label_len else s[:max_label_len - 1] + "…"
    labels = [short_label(l) for l in df["Orbit Label"]]


    # --- Draw bars for each metric, with dummy left bar for margin ---
    for i, m in enumerate(metrics):
        vals = df[m].astype(float)
        best = vals.max() if maximize[m] else vals.min()
        # --- Add dummy value for left margin ---
        bar_vals = np.insert(vals.values, 0, 0)
            '#FFD700' if idx == best_idx else
            ('#90ee90' if abs(v - best) < 1e-6 and idx != best_idx else '#26415B')
            for idx, v in enumerate(vals)
        ]
#<<<<<<< HEAD
#        axes[i].bar(range(len(df)), vals, color=bar_colors, width=0.7)
#=======
        axes[i].bar(range(len(bar_vals)), bar_vals, color=bar_colors, width=0.7)
        axes[i].set_xlim(-0.5, len(bar_vals)-0.5)  # Show all bars including dummy
#>>>>>>> 6c39a73 (Initial production push)
        axes[i].set_title(m, loc='left', fontsize=13 * font_scale, fontweight='bold')
        axes[i].set_xticks([])
        axes[i].set_yticks([])
        axes[i].spines['top'].set_visible(False)
        axes[i].spines['right'].set_visible(False)

    # --- Weighted Score (last plot, with labels/annotation) ---
    ax = axes[-1]
    bar_vals = np.insert(df["Weighted Score"].values, 0, 0)
    bar_colors = ['white'] + [
        '#FFD700' if idx == best_idx else '#26415B' for idx in range(len(df))
    ]
    ax.bar(range(len(bar_vals)), bar_vals, color=bar_colors, width=0.7)
    ax.set_xlim(-0.5, len(bar_vals)-0.5)
    ax.set_title("Weighted Score by Orbit", loc='left', fontsize=14 * font_scale, fontweight='bold')
    ax.set_yticks([])

    # --- Short orbit labels under bars ---
#<<<<<<< HEAD
 #   ax.set_xticks(range(len(df)))
#=======
    ax.set_xticks(range(1, len(bar_vals)))  # skip dummy
#>>>>>>> 6c39a73 (Initial production push)
    ax.set_xticklabels(labels, fontsize=11 * font_scale, rotation=32, ha='right')

    # --- Annotation: Arrow + text above best bar ---
    ymax = df["Weighted Score"].max()
    y_annot = ymax + 0.10 * (ymax if ymax > 1 else 1)
    ax.annotate(
        "Best Orbit in Database",
        xy=(best_idx+1, df.loc[best_idx, "Weighted Score"]),  # +1 for dummy bar offset
        xytext=(best_idx+1, y_annot),
        textcoords='data',
        ha='center',
        va='bottom',
        fontsize=14 * font_scale,
        fontweight='bold',
        color='#333366',
        arrowprops=dict(arrowstyle="->", lw=2, color="#333366")
    )

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # --- Export to buffer ---
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=230)
    plt.close(fig)
    buf.seek(0)
    return buf
