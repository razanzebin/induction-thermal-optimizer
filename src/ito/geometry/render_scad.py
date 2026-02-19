from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import subprocess
import shutil

SHAPES = [
    "solid_cone",
    "hollow_cone",
    "rod",
    "hemisphere",
    "half_ellipsoid",
    "blunt_cone",
]

@dataclass(frozen=True)
class TipParams:
    shape: str = "solid_cone"
    L: float = 12.0
    D: float = 3.0
    wall: float = 0.4
    tipR: float = 0.6
    # Ellipsoid semi-axes
    a: float | None = None
    b: float | None = None
    c: float | None = None

def _require_openscad() -> str:
    exe = shutil.which("openscad")
    if not exe:
        raise RuntimeError("openscad not found on PATH.")
    return exe

def render_tip_stl(out_stl: Path, params: TipParams, scad_path: Path | None = None) -> None:
    exe = _require_openscad()
    scad_path = scad_path or (Path(__file__).parent / "tip_family.scad")
    out_stl.parent.mkdir(parents=True, exist_ok=True)

    # default ellipsoid axes if not set
    a = params.a if params.a is not None else (params.D / 2)
    b = params.b if params.b is not None else (params.D / 2)
    c = params.c if params.c is not None else (params.L)

    defines = [
        "-D", f'shape="{params.shape}"',
        "-D", f"L={params.L}",
        "-D", f"D={params.D}",
        "-D", f"wall={params.wall}",
        "-D", f"tipR={params.tipR}",
        "-D", f"a={a}",
        "-D", f"b={b}",
        "-D", f"c={c}",
        "-D", f"$fn=96",
    ]

    cmd = [exe, *defines, "-o", str(out_stl), str(scad_path)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"OpenSCAD failed.\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")

def render_all(out_dir: Path, base: TipParams) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for s in SHAPES:
        p = TipParams(**{**asdict(base), "shape": s})
        out = out_dir / f"{s}.stl"
        render_tip_stl(out, p)
        paths.append(out)
    return paths
