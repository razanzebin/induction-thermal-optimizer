from __future__ import annotations

from dataclasses import dataclass
import math

@dataclass(frozen=True)
class ThermalParams:
    T_amb_C: float = 25.0
    m_kg: float = 0.0005     # 0.5 g (placeholder)
    cp_J_per_kgK: float = 500.0
    h_W_per_m2K: float = 250.0
    A_m2: float = 3.0e-5     # ~ (3 mm dia, 12 mm length) order
    t_end_s: float = 10.0
    dt_s: float = 0.05

def simulate_tip_temp(P_w: float, th: ThermalParams) -> dict:
    """
    Lumped capacitance model:
      m cp dT/dt = P - h A (T - Tamb)
    Returns summary metrics.
    """
    T = th.T_amb_C
    Tamb = th.T_amb_C

    n = int(math.ceil(th.t_end_s / th.dt_s))
    max_rate = 0.0
    for _ in range(n):
        # dT/dt in K/s (same as C/s)
        dTdt = (P_w - th.h_W_per_m2K * th.A_m2 * (T - Tamb)) / (th.m_kg * th.cp_J_per_kgK)
        max_rate = max(max_rate, dTdt)
        T += dTdt * th.dt_s

    return {
        "T_final_C": float(T),
        "T_rise_C": float(T - Tamb),
        "max_dTdt_C_per_s": float(max_rate),
    }
