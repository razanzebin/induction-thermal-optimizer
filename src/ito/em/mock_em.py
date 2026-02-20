from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

@dataclass(frozen=True)
class EMParams:
    f_hz: float = 40_000.0   # frequency
    I_a: float = 150.0       # current amplitude (placeholder)
    k: float = 1.0e-6        # scaling constant for mock power

def estimate_power_w_from_stl(stl_path: Path, em: EMParams) -> float:
    """
    Mock induction power model.

    We intentionally keep this simple + deterministic:
    - Parse approximate 'size' from STL file size (bytes) as a proxy for surface complexity/area.
    - Scale with frequency and current.

    Replace with FEMM later, but keep same function signature.
    """
    if not stl_path.exists():
        raise FileNotFoundError(stl_path)

    size_bytes = stl_path.stat().st_size
    # proxy "effective area" ~ sqrt(bytes) (arbitrary but stable)
    A_eff = math.sqrt(max(1.0, float(size_bytes)))

    # power scales with frequency and I^2 in induction-like systems (rough heuristic)
    P = em.k * A_eff * (em.f_hz / 40_000.0) * (em.I_a / 150.0) ** 2

    # clamp to avoid absurd numbers during early testing
    return float(max(0.0, min(P, 50.0)))
