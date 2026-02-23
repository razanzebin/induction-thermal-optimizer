from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

EMBackend = Literal["mock", "femm"]

@dataclass(frozen=True)
class EMParams:
    backend: EMBackend = "mock"
    f_hz: float = 40_000.0
    I_a: float = 150.0
    coil_type: str = "pancake"
    turns: int = 8
    coil_od_mm: float = 30.0
    standoff_mm: float = 10.0

def estimate_power_w(stl_path: Path, p: EMParams) -> float:
    if p.backend == "mock":
        from ito.em.mock_em import estimate_power_w_from_stl, EMParams as MockParams
        return estimate_power_w_from_stl(stl_path, MockParams(f_hz=p.f_hz, I_a=p.I_a))
    if p.backend == "femm":
        from ito.em.run_femm import estimate_power_w_from_femm
        return estimate_power_w_from_femm(stl_path, p)
    raise ValueError(f"Unknown backend: {p.backend}")
