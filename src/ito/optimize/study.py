from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json
import optuna

from ito.geometry.render_scad import TipParams, render_tip_stl, SHAPES
from ito.em.mock_em import EMParams, estimate_power_w_from_stl
from ito.thermal.lumped import ThermalParams, simulate_tip_temp

TEMP_CAP_C = 90.0  # Constraint B

def objective(trial: optuna.Trial, base_dir: Path) -> float:
    shape = trial.suggest_categorical("shape", SHAPES)

    # Geometry ranges (sane starter bounds)
    L = trial.suggest_float("L_mm", 6.0, 20.0)
    D = trial.suggest_float("D_mm", 1.0, 6.0)

    wall = 0.4
    tipR = 0.6
    if shape == "hollow_cone":
        wall = trial.suggest_float("wall_mm", 0.2, 1.0)
    if shape == "blunt_cone":
        tipR = trial.suggest_float("tipR_mm", 0.2, 1.5)

    # Frequency variable
    f = trial.suggest_float("f_hz", 20_000.0, 120_000.0)

    run_dir = base_dir / f"trial_{trial.number:04d}"
    geom_dir = run_dir / "geometry"
    geom_dir.mkdir(parents=True, exist_ok=True)

    params = TipParams(shape=shape, L=L, D=D, wall=wall, tipR=tipR)
    stl_path = geom_dir / "tip.stl"
    render_tip_stl(stl_path, params)

    P = estimate_power_w_from_stl(stl_path, EMParams(f_hz=f))
    th = simulate_tip_temp(P, ThermalParams())

    metrics = {
        "shape": shape,
        "params": asdict(params),
        "f_hz": f,
        "P_tip_W": P,
        **th,
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    # Constraint B: reject if T_final_C > 90C
    if metrics["T_final_C"] > TEMP_CAP_C:
        raise optuna.TrialPruned(f"T_final_C {metrics['T_final_C']:.2f} exceeds cap {TEMP_CAP_C}")

    # Objective A: maximize final temp at t_end
    return metrics["T_final_C"]

def run_study(outdir: Path, n_trials: int = 50) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda t: objective(t, outdir), n_trials=n_trials)

    best = {
        "best_value": study.best_value,
        "best_params": study.best_params,
        "n_trials": n_trials,
        "temp_cap_C": TEMP_CAP_C,
    }
    (outdir / "best.json").write_text(json.dumps(best, indent=2))
    return best
