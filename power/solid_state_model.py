"""Solid state dynamic model for the mining spacecraft.

This model implements the pseudocode provided in user notes.
State variables:
    x1 : Battery state of charge (Wh)
    x2 : ASIC temperature (°C)
    x3 : Cumulative mined BTC

Inputs:
    u1 : Solar power input (W)
    u2 : Primary mission load (W)
    u3 : Mining ASIC power state (0-1)

Outputs:
    y1 : Battery state of charge (Wh)
    y2 : BTC mined rate (BTC/s)
    y3 : ASIC temperature (°C)

Equations:
    x1_dot = u1 - u2 - P_miner
    P_miner = P_ASIC_max * u3
    x2_dot = (1/eff_heat_cap) * (P_total - Q_rad(x2))
    Q_rad(x2) = emissivity * sigma * panel_area * (T_K^4 - T_env_K^4)
    x3_dot = hash_eff * u3

This is a simple 0-D model with Euler integration performed in ``step``.
"""

from dataclasses import dataclass, field


@dataclass
class SolidStateModel:
    """Simple solid state model with Euler integration."""

    P_ASIC_max: float = 250.0  # W, maximum ASIC power
    eff_heat_cap: float = 500.0  # J/K effective heat capacity
    panel_area: float = 0.2  # m^2 area for radiative cooling
    emissivity: float = 0.9  # dimensionless emissivity
    env_temp: float = 5.0  # °C, environment temperature
    hash_eff: float = 1e-6  # BTC per second at full power
    sigma: float = 5.670374419e-8  # Stefan–Boltzmann constant

    x1_batt_wh: float = 0.0
    x2_temp_c: float = 20.0
    x3_btc: float = 0.0

    def step(self, dt: float, u1_solar_w: float, u2_load_w: float, u3_power: float):
        """Propagate the model one time step.

        Parameters
        ----------
        dt : float
            Time step in seconds.
        u1_solar_w : float
            Available solar power in watts.
        u2_load_w : float
            Power draw from spacecraft subsystems in watts.
        u3_power : float
            ASIC throttle (0=off, 1=on).
        """
        u3_power = max(0.0, min(1.0, u3_power))
        P_miner = self.P_ASIC_max * u3_power
        x1_dot = u1_solar_w - u2_load_w - P_miner

        P_total = P_miner + u2_load_w
        T_K = self.x2_temp_c + 273.15
        T_env_K = self.env_temp + 273.15
        q_rad = self.emissivity * self.sigma * self.panel_area * (T_K ** 4 - T_env_K ** 4)
        x2_dot = (P_total - q_rad) / self.eff_heat_cap

        x3_dot = self.hash_eff * u3_power

        # Euler integration
        self.x1_batt_wh += (x1_dot * dt) / 3600.0
        self.x2_temp_c += x2_dot * dt
        self.x3_btc += x3_dot * dt

        return self.outputs(u3_power)

    def outputs(self, u3_power: float):
        """Return the current outputs."""
        y1 = self.x1_batt_wh
        y2 = self.hash_eff * u3_power
        y3 = self.x2_temp_c
        return y1, y2, y3
