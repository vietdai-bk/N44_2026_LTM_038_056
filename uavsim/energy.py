"""Công suất bay của UAV cánh quay: Zeng, Xu, Zhang, IEEE TWC 2019."""
import numpy as np

P0 = 79.86      # W, blade profile power khi hover
PI = 88.63      # W, induced power khi hover
U_TIP = 120.0   # m/s
V0 = 4.03       # m/s, vận tốc cảm ứng trung bình của rotor khi hover
D0 = 0.6        # tỷ số fuselage drag
RHO = 1.225     # kg/m^3
S = 0.05        # rotor solidity
A = 0.503       # m^2, diện tích đĩa rotor


def rotary_power(v):
    """Công suất (W) khi bay ngang với vận tốc v (m/s)."""
    v = np.asarray(v, dtype=float)
    blade = P0 * (1 + 3 * v**2 / U_TIP**2)
    induced = PI * np.sqrt(np.sqrt(1 + v**4 / (4 * V0**4)) - v**2 / (2 * V0**2))
    parasite = 0.5 * D0 * RHO * S * A * v**3
    return blade + induced + parasite
