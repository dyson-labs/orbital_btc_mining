import io
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def project_revenue_curve(
    solar_fraction,
    mission_lifetime,
    asic_count,
    step=0.25,
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
    steps = int(mission_lifetime / step)
    for i in range(steps):
        t = (i + 1) * step
        price = btc_price * ((1 + btc_price_growth) ** t)
        net_hash = network_hashrate_ehs * ((1 + network_hashrate_growth) ** t)
        share = total_hashrate / (net_hash * 1_000_000)
        btc_day = share * blocks_per_day * block_reward_btc * solar_fraction
        btc_period = btc_day * 365 * step
        revenue.append(btc_period * price)
    return revenue


def roi_plot_to_buffer(total_cost, revenue_curve, step=0.25):
    """Generate ROI chart and return PNG buffer."""
    years = np.arange(step, step * len(revenue_curve) + 0.0001, step)
    cumulative = np.cumsum(revenue_curve)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(years, cumulative, label="Cumulative Revenue")
    ax.axhline(total_cost, color="r", linestyle="--", label="Total Cost")
    ax.set_xlabel("Years")
    ax.set_ylabel("USD")

    def fmt(val, _):
        abs_v = abs(val)
        if abs_v >= 1e9:
            return f"${val/1e9:.1f}b"
        if abs_v >= 1e6:
            return f"${val/1e6:.1f}m"
        if abs_v >= 1e3:
            return f"${val/1e3:.1f}k"
        return f"${val:.0f}"

    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(fmt))
    ax.set_title("ROI Projection")
    ax.legend()
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf
