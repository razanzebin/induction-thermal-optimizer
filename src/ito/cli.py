from __future__ import annotations

from pathlib import Path
import json
import time
import typer

from ito.geometry.render_scad import TipParams, render_tip_stl, render_all, SHAPES
from ito.em.mock_em import EMParams, estimate_power_w_from_stl
from ito.thermal.lumped import ThermalParams, simulate_tip_temp

app = typer.Typer(help="Induction Thermal Optimizer (OpenSCAD -> EM -> Thermal -> Optuna)")

@app.command()
def hello():
    typer.echo("ito: ok")

@app.command()
def run(
    outdir: Path = typer.Option(Path("runs"), help="Output directory for runs"),
    shape: str = typer.Option("solid_cone", help=f"Shape: {', '.join(SHAPES)} or 'all'"),

    # Geometry
    l: float = typer.Option(12.0, help="Length (mm)"),
    d: float = typer.Option(3.0, help="Outer diameter (mm)"),
    wall: float = typer.Option(0.4, help="Wall thickness for hollow cone (mm)"),
    tipr: float = typer.Option(0.6, help="Tip radius for blunt cone (mm)"),
    a: float = typer.Option(None, help="Ellipsoid semi-axis a (mm)"),
    b: float = typer.Option(None, help="Ellipsoid semi-axis b (mm)"),
    c: float = typer.Option(None, help="Ellipsoid semi-axis c (mm)"),

    # EM (mock for now)
    f: float = typer.Option(40_000.0, help="Frequency (Hz)"),
    i: float = typer.Option(150.0, help="Current amplitude (A) [placeholder]"),
):
    run_id = time.strftime("%Y%m%d_%H%M%S")
    run_dir = outdir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    geom_params = TipParams(shape=shape if shape != "all" else "solid_cone", L=l, D=d, wall=wall, tipR=tipr, a=a, b=b, c=c)
    em_params = EMParams(f_hz=f, I_a=i)

    cfg = {
        "run_id": run_id,
        "geometry": {"shape": shape, "L": l, "D": d, "wall": wall, "tipR": tipr, "a": a, "b": b, "c": c},
        "em": {"f_hz": f, "I_a": i},
        "thermal": "lumped_default",
    }
    (run_dir / "config.json").write_text(json.dumps(cfg, indent=2))

    geom_dir = run_dir / "geometry"
    metrics = {"run_id": run_id}

    if shape == "all":
        outs = render_all(geom_dir, base=geom_params)
        per_shape = {}
        for stl in outs:
            P = estimate_power_w_from_stl(stl, em_params)
            th = simulate_tip_temp(P, ThermalParams())
            per_shape[stl.stem] = {"P_tip_W": P, **th}
        metrics["per_shape"] = per_shape
        typer.echo(f"Run: {run_dir}")
        typer.echo(f"Generated {len(outs)} STL files + metrics.json")
    else:
        stl_path = geom_dir / "tip.stl"
        render_tip_stl(stl_path, params=geom_params)

        P = estimate_power_w_from_stl(stl_path, em_params)
        th = simulate_tip_temp(P, ThermalParams())

        metrics.update({"shape": shape, "P_tip_W": P, **th})
        typer.echo(f"Run: {run_dir}")
        typer.echo(f"STL: {stl_path}")
        typer.echo(f"P_tip_W: {P:.4f}  T_final_C: {metrics['T_final_C']:.2f}")

    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    app()
