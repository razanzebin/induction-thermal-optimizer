from __future__ import annotations

from pathlib import Path
import json
import optuna

from ito.geometry.render_scad import TipParams, render_tip_stl, SHAPES
from ito.em.api import EMParams, estimate_power_w
from ito.thermal.lumped import ThermalParams, simulate_tip_temp


def _make_tipparams(**kwargs) -> TipParams:
    """
    Create TipParams while safely ignoring keys that TipParams doesn't define.
    Works for pydantic v2 models, pydantic v1, or dataclasses.
    """
    # pydantic v2
    if hasattr(TipParams, "model_fields"):
        allowed = set(TipParams.model_fields.keys())
        clean = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        return TipParams(**clean)

    # pydantic v1
    if hasattr(TipParams, "__fields__"):
        allowed = set(TipParams.__fields__.keys())
        clean = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        return TipParams(**clean)

    # dataclass
    if hasattr(TipParams, "__dataclass_fields__"):
        allowed = set(TipParams.__dataclass_fields__.keys())
        clean = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        return TipParams(**clean)

    # fallback: best effort
    return TipParams(**{k: v for k, v in kwargs.items() if v is not None})


def objective(trial: optuna.Trial, outdir: Path) -> float:
    # --- Suggest geometry + frequency ---
    shape = trial.suggest_categorical("shape", list(SHAPES))
    L_mm = trial.suggest_float("L_mm", 5.0, 20.0)
    D_mm = trial.suggest_float("D_mm", 1.0, 6.0)
    f_hz = trial.suggest_float("f_hz", 1.0e4, 1.5e5)

    # --- Suggest coil params (EM) ---
    I_a = trial.suggest_float("I_a", 50.0, 400.0)
    turns = trial.suggest_int("turns", 2, 30)
    standoff_mm = trial.suggest_float("standoff_mm", 0.5, 20.0)
    coil_od_mm = trial.suggest_float("coil_od_mm", 10.0, 60.0)

    # Shape-specific params (only used if TipParams supports them)
    wall_mm = None
    tipR_mm = None

    if shape == "hollow_cone":
        wall_mm = trial.suggest_float("wall_mm", 0.1, max(0.15, 0.45 * D_mm))
    if shape == "blunt_cone":
        tipR_mm = trial.suggest_float("tipR_mm", 0.1, max(0.15, 0.45 * D_mm))

    params = _make_tipparams(shape=shape, L_mm=L_mm, D_mm=D_mm, wall_mm=wall_mm, tipR_mm=tipR_mm)

    # --- Per-trial folder ---
    run_dir = outdir / f"trial_{trial.number:05d}"
    geom_dir = run_dir / "geometry"
    geom_dir.mkdir(parents=True, exist_ok=True)

    stl_path = geom_dir / "tip.stl"
    render_tip_stl(stl_path, params)

    # --- FEMM proxy (axisymmetric rectangle, quick proxy) ---
    (geom_dir / "tip_proxy.json").write_text(
        json.dumps({"tip_r_mm": float(D_mm) / 2.0, "tip_L_mm": float(L_mm)})
    )

    # --- EM: FEMM power ---
    em = EMParams(
        backend="femm",
        f_hz=float(f_hz),
        I_a=float(I_a),
        turns=int(turns),
        coil_od_mm=float(coil_od_mm),
        standoff_mm=float(standoff_mm),
    )
    P = estimate_power_w(stl_path, em)

    # --- Thermal ---
    th = simulate_tip_temp(P, ThermalParams())

    # Save metrics for debugging / plots
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "trial": trial.number,
                "shape": shape,
                "L_mm": L_mm,
                "D_mm": D_mm,
                "wall_mm": wall_mm,
                "tipR_mm": tipR_mm,
                "f_hz": f_hz,
                "P_tip_W": P,
                **th,
            },
            indent=2,
        )
    )

    return float(th["T_final_C"])


def run_study(outdir: Path, n_trials: int = 50) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda t: objective(t, outdir), n_trials=n_trials)
    return {"best_value": study.best_value, "best_params": study.best_params, "n_trials": n_trials}
