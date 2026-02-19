from __future__ import annotations

from pathlib import Path
import json
import time
import typer

from ito.geometry.render_scad import TipParams, render_tip_stl, render_all, SHAPES

app = typer.Typer(help="Induction Thermal Optimizer (OpenSCAD -> FEMM -> OpenFOAM -> Optuna)")

@app.command()
def hello():
    typer.echo("ito: ok")

@app.command()
def run(
    outdir: Path = typer.Option(Path("runs"), help="Output directory for runs"),
    shape: str = typer.Option("solid_cone", help=f"Shape: {', '.join(SHAPES)} or 'all'"),
    L: float = typer.Option(12.0, help="Length (mm)"),
    D: float = typer.Option(3.0, help="Outer diameter (mm)"),
    wall: float = typer.Option(0.4, help="Wall thickness for hollow cone (mm)"),
    tipR: float = typer.Option(0.6, help="Tip radius for blunt cone (mm)"),
    a: float = typer.Option(None, help="Ellipsoid semi-axis a (mm)"),
    b: float = typer.Option(None, help="Ellipsoid semi-axis b (mm)"),
    c: float = typer.Option(None, help="Ellipsoid semi-axis c (mm)"),
):
    run_id = time.strftime("%Y%m%d_%H%M%S")
    run_dir = outdir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    params = TipParams(shape=shape if shape != "all" else "solid_cone", L=L, D=D, wall=wall, tipR=tipR, a=a, b=b, c=c)

    cfg = {
        "run_id": run_id,
        "geometry": {
            "shape": shape,
            "L": L, "D": D, "wall": wall, "tipR": tipR,
            "a": a, "b": b, "c": c,
        },
    }
    (run_dir / "config.json").write_text(json.dumps(cfg, indent=2))

    geom_dir = run_dir / "geometry"
    if shape == "all":
        outs = render_all(geom_dir, base=params)
        typer.echo(f"Run: {run_dir}")
        typer.echo(f"Generated {len(outs)} STL files in {geom_dir}")
    else:
        out_stl = geom_dir / "tip.stl"
        render_tip_stl(out_stl, params=params)
        typer.echo(f"Run: {run_dir}")
        typer.echo(f"STL: {out_stl}")

if __name__ == "__main__":
    app()
