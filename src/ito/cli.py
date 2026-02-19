from __future__ import annotations

from pathlib import Path
import json
import time
import typer

app = typer.Typer(help="Induction Thermal Optimizer (OpenSCAD -> EM -> Thermal -> Optuna)")

@app.command()
def hello():
    """Sanity check that the package/CLI wiring works."""
    typer.echo("ito: ok")

@app.command()
def run(
    outdir: Path = typer.Option(Path("runs"), help="Output directory for runs"),
):
    """
    Minimal run: creates a timestamped run folder and writes a config.json.
    """
    run_id = time.strftime("%Y%m%d_%H%M%S")
    run_dir = outdir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    cfg = {"run_id": run_id, "outdir": str(run_dir)}
    (run_dir / "config.json").write_text(json.dumps(cfg, indent=2))

    typer.echo(f"Created run folder: {run_dir}")

if __name__ == "__main__":
    app()
