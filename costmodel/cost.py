# cost.py · Now handles price/network growth and custom lifetime.


def run_cost_model(solar_fraction, **kwargs):
    # Accept overrides or use defaults
    bus_cost = kwargs.get("bus_cost", 60000)
    payload_cost = kwargs.get("payload_cost", 60000)
    launch_cost = kwargs.get("launch_cost", 130000)
    overhead = kwargs.get("overhead", 160000)
    integration_cost = kwargs.get("integration_cost", 45000)
    comms_cost = kwargs.get("comms_cost", 100000)
    contingency = kwargs.get("contingency", 0.25)
    # Core technical constants
    asic_count = kwargs.get("asic_count", 3)
    hashrate_per_asic = kwargs.get("hashrate_per_asic", 0.63)
    power_per_asic = kwargs.get("power_per_asic", 9)
    mission_lifetime = float(kwargs.get("mission_lifetime", 5))
    network_hashrate_ehs = float(kwargs.get("network_hashrate_ehs", 700))
    block_reward_btc = float(kwargs.get("block_reward_btc", 3.125))
    blocks_per_day = 144
    btc_price = float(kwargs.get("btc_price", 105000.0))
    # User-supplied projections
    btc_price_growth = (
        float(kwargs.get("btc_price_growth", 10)) / 100
    )  # %/yr to decimal
    network_hashrate_growth = (
        float(kwargs.get("network_hashrate_growth", 25)) / 100
    )  # %/yr to decimal
    # ---- Compounding for price/network growth ----
    # Calculate avg BTC price and avg network hashrate over the mission lifetime
    step = 0.25
    steps = int(mission_lifetime / step)
    btc_price_list = []
    net_hash_list = []
    for i in range(steps):
        t = (i + 1) * step
        btc_price_year = btc_price * ((1 + btc_price_growth) ** t)
        net_hash_year = network_hashrate_ehs * ((1 + network_hashrate_growth) ** t)
        btc_price_list.append(btc_price_year)
        net_hash_list.append(net_hash_year)

    avg_btc_price = sum(btc_price_list) / steps if steps else btc_price
    avg_network_hashrate = sum(net_hash_list) / steps if steps else network_hashrate_ehs

    # ---- Calculations ----
    base_cost = bus_cost + payload_cost + launch_cost + integration_cost + comms_cost
    total_cost = base_cost * (1 + contingency)
    total_hashrate = asic_count * hashrate_per_asic
    total_power = asic_count * power_per_asic
    share = total_hashrate / (avg_network_hashrate * 1_000_000)
    btc_day = share * blocks_per_day * block_reward_btc * solar_fraction
    btc_year = btc_day * 365
    revenue_usd = btc_year * mission_lifetime * avg_btc_price
    profit_usd = revenue_usd - total_cost

    print(f"Total mission cost: ${total_cost:,.0f}")
    print(f"Total mining hashrate: {total_hashrate:.2f} TH/s")
    print(f"Total power draw: {total_power:.1f} W")
    print(
        f"BTC mined per day (factoring {solar_fraction*100:.1f}% uptime): {btc_day:.6f} BTC/day"
    )
    print(f"Total mission BTC mined: {btc_year * mission_lifetime:.4f} BTC")
    print(f"Total mission revenue (USD): ${revenue_usd:,.0f}")
    print(f"Net profit: ${profit_usd:,.0f}")

    return {
        "total_cost": total_cost,
        "bus_cost": bus_cost,
        "payload_cost": payload_cost,
        "launch_cost": launch_cost,
        "overhead": overhead,
        "integration_cost": integration_cost,
        "comms_cost": comms_cost,
        "contingency": contingency,
        "total_hashrate": total_hashrate,
        "total_power": total_power,
        "btc_day": btc_day,
        "btc_year": btc_year,
        "revenue_usd": revenue_usd,
        "profit_usd": profit_usd,
        "avg_btc_price": avg_btc_price,
        "avg_network_hashrate": avg_network_hashrate,
        "mission_lifetime": mission_lifetime,
    }
