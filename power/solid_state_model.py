"""Simple solid state power/thermal/bitcoin mining model."""

from dataclasses import dataclass
from typing import Iterable, Tuple
import numpy as np


@dataclass
class ModelParams:
    """Parameters for the solid state model."""

    asic_power_max: float = 50.0  # W
    emissivity: float = 0.9
    panel_area: float = 0.1  # m^2
    env_temp: float = 3.0  # K
    eff_heat_cap: float = 100.0  # J/K
    hash_eff: float = 1e-6  # BTC/s at full power
    max_temp: float = 350.0  # K


@dataclass
class ModelState:
    battery_Wh: float
    asic_temp_K: float
    btc_cumulative: float


def step(state: ModelState, u1: float, u2: float, u3: float, dt: float, params: ModelParams) -> ModelState:
    """Advance the model one timestep.

    Parameters
    ----------
    state : ModelState
        Current state of the system.
    u1 : float
        Solar power input in Watts.
    u2 : float
        Primary mission load in Watts.
    u3 : float
        ASIC throttle (0-1).
    dt : float
        Integration timestep in seconds.
    params : ModelParams
        Model configuration parameters.

    Returns
    -------
    ModelState
        Updated state after ``dt`` seconds.
    """

    sigma = 5.670374419e-8  # Stefan-Boltzmann constant
    P_miner = params.asic_power_max * u3
    x1_dot = u1 - u2 - P_miner
    Q_rad = params.emissivity * sigma * params.panel_area * (state.asic_temp_K ** 4 - params.env_temp ** 4)
    x2_dot = (u2 + P_miner - Q_rad) / params.eff_heat_cap
    x3_dot = params.hash_eff * u3

    state = ModelState(
        battery_Wh=state.battery_Wh + x1_dot * dt / 3600.0,
        asic_temp_K=state.asic_temp_K + x2_dot * dt,
        btc_cumulative=state.btc_cumulative + x3_dot * dt,
    )

    if state.battery_Wh < 0:
        state = ModelState(0.0, state.asic_temp_K, state.btc_cumulative)
    if state.asic_temp_K > params.max_temp:
        state = ModelState(state.battery_Wh, params.max_temp, state.btc_cumulative)

    return state


def simulate(
    u1: Iterable[float],
    u2: Iterable[float],
    u3: Iterable[float],
    dt: float,
    initial_state: ModelState,
    params: ModelParams,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run a full simulation over the provided input sequences."""

    u1 = np.asarray(list(u1), dtype=float)
    u2 = np.asarray(list(u2), dtype=float)
    u3 = np.asarray(list(u3), dtype=float)
    n = len(u1)

    x1_hist = np.empty(n)
    x2_hist = np.empty(n)
    x3_hist = np.empty(n)

    state = initial_state
    for i in range(n):
        state = step(state, u1[i], u2[i], u3[i], dt, params)
        x1_hist[i] = state.battery_Wh
        x2_hist[i] = state.asic_temp_K
        x3_hist[i] = state.btc_cumulative

    return x1_hist, x2_hist, x3_hist
