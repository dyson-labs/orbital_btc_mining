# -*- coding: utf-8 -*-
"""
Created on Tue Jun 24 14:01:11 2025

@author: elder
"""
import numpy as np

# Constants
k_Cu = 390      # W/mK
k_FR4 = 0.3     # W/mK
t_Cu = 35e-6    # m
t_FR4 = 0.2e-3  # m
A_ASIC = 6e-3 * 8e-3    # m²
n_vias = 72
via_OD = 0.6e-3 / 2  # outer radius, m
via_ID = 0.3e-3 / 2  # inner radius, m

# Copper pour resistance (top/bottom)
R_Cu_top = t_Cu / (k_Cu * A_ASIC)
R_Cu_bot = t_Cu / (k_Cu * A_ASIC)

# Via resistance
A_via_wall = np.pi * (via_OD**2 - via_ID**2)   # single via wall area (m²)
A_via_total = A_via_wall * n_vias

R_vias = t_FR4 / (k_Cu * A_via_total)  # vertical via path

# FR4 (area NOT occupied by vias)
A_FR4 = A_ASIC - A_via_total
R_FR4 = t_FR4 / (k_FR4 * A_FR4) if A_FR4 > 0 else np.inf

# Parallel resistance: vias and FR4 in parallel
R_FR4_vias_parallel = 1.0 / (1/R_vias + 1/R_FR4)

# Total resistance through stack
R_total = R_Cu_top + R_FR4_vias_parallel + R_Cu_bot

# Effective k for total thickness
t_total = t_Cu + t_FR4 + t_Cu
k_eff = t_total / (R_total * A_ASIC)

print(f"Effective k through ASIC region = {k_eff:.1f} W/mK")
print(f"Via path dominates? {'Yes' if R_vias < R_FR4 else 'No'}")
