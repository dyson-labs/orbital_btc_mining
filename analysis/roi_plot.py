import io
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def project_revenue_curve(
    solar_fraction,
    mission_lifetime,
    asic_count,
    hashrate_per_asic=0.63,
    btc_price=105000.0,
    btc_price_growth=0.1,
    network_hashrate_ehs=700.0,
    network_hashrate_growth=0.25,
    block_reward_btc=3.125,
    blocks_per_day=144,
):
    """Return list of yearly revenue projections in USD."""
    revenue = []
    total_hashrate = asic_count * hashrate_per_asic
    for year in range(mission_lifetime):
        price = btc_price * ((1 + btc_price_growth) ** year)
        net_hash = network_hashrate_ehs * ((1 + network_hashrate_growth) ** year)
        share = total_hashrate / (net_hash * 1_000_000)
        btc_day = share * blocks_per_day * block_reward_btc * solar_fraction
        btc_year = btc_day * 365
        revenue.append(btc_year * price)
    return revenue


def roi_plot_to_buffer(total_cost, revenue_curve):
    """Generate ROI chart and return PNG buffer."""
    years = np.arange(1, len(revenue_curve) + 1)
    cumulative = np.cumsum(revenue_curve)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(years, cumulative, label="Cumulative Revenue")
    ax.axhline(total_cost, color="r", linestyle="--", label="Total Cost")
    ax.set_xlabel("Years")
    ax.set_ylabel("USD")
    ax.set_title("ROI Projection")
    ax.legend()
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf
