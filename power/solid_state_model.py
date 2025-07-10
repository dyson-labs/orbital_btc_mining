# Given: initial x1, x2, x3, timestep dt, input arrays u1, u2, u3 over mission duration
for dt:
    P_miner = ASIC_power_max * u3
    x1_dot = u1 - u2 - P_miner
    Q_rad = epsilon * sigma * A * (x2**4 - T_space**4)
    x2_dot = (u2 + P_miner - Q_rad) / C_th
    x3_dot = hashrate_to_BTC * u3
    x1 += x1_dot * dt
    x2 += x2_dot * dt
    x3 += x3_dot * dt
    # Enforce constraints: x1 >= 0, x2 < max_temp, etc.
