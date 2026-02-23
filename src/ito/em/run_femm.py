from __future__ import annotations

from pathlib import Path
import subprocess
import json
import shutil

from ito.em.api import EMParams

FEMM_EXE_DEFAULTS = [
    "/mnt/c/femm42/bin/femm.exe",
    "/mnt/c/femm42/bin/femm64.exe",
]

def _find_femm_exe() -> str:
    for p in FEMM_EXE_DEFAULTS:
        if Path(p).exists():
            return p
    exe = shutil.which("femm.exe")
    if exe:
        return exe
    raise FileNotFoundError("Could not find FEMM executable. Expected /mnt/c/femm42/bin/femm.exe")

def _write_lua(lua_path: Path, p: EMParams, tip: dict) -> None:
    out_dir_win = "C:\\\\temp\\\\ito_femm"
    fem_path  = out_dir_win + "\\\\case.fem"
    ptxt_path = out_dir_win + "\\\\p_tip_W.txt"
    meta_path = out_dir_win + "\\\\em_meta.json"
    prog_path = out_dir_win + "\\\\progress.txt"

    tip_r = float(tip.get("tip_r_mm", 1.5))
    tip_L = float(tip.get("tip_L_mm", 12.0))
    # --- coil geometry (paper-like helical coil around a test tube) ---
    # Paper: coil around test tube at swimmer height, with ~8 mm gap.
    coil_od = float(p.coil_od_mm)

    tube_od_mm = getattr(p, "tube_od_mm", 25.0)     # paper uses 25 mm O.D. test tube
    gap_mm     = getattr(p, "gap_mm", 2.5)          # paper states 8 mm gap (tube -> coil)
    coil_h     = getattr(p, "coil_h_mm", max(1.0, coil_od * 0.15))
    coil_t_rad = getattr(p, "coil_t_rad_mm", 3.0)   # radial thickness of copper bundle (choose if unknown)

    tube_r = tube_od_mm / 2.0
    coil_r1 = tube_r + gap_mm
    coil_r2 = coil_r1 + coil_t_rad

    # Place coil at the height of the swimmer (centered along the swimmer length)
    coil_z1 = max(0.0, (tip_L/2.0) - (coil_h/2.0))
    coil_z2 = coil_z1 + coil_h

    Rb = coil_r2 * 6.0
    Zb = (coil_z2 + coil_r2 * 4.0)

    def mark_line(msg: str) -> str:
        # NO function definitions in FEMM lua-script mode; write progress inline
        return f'''
f = openfile("{prog_path}", "w")
write(f, "{msg}\\n")
closefile(f)
'''

    lua = "-- FEMM Lua script (no function defs)\\n" + \
          mark_line("start") + f"""
newdocument(0)
mi_probdef({p.f_hz}, "millimeters", "axi", 1e-8, 0, 30)
""" + mark_line("after_probdef") + f"""
mi_addmaterial("AIR", 1, 1, 0, 0, 0)
mi_getmaterial("Pure Iron")
mi_addmaterial("COPPER", 1, 1, 0, 0, 5.8e7)
""" + mark_line("after_materials") + f"""
mi_drawrectangle(0, 0, {tip_r}, {tip_L})
""" + mark_line("after_tip") + f"""
mi_drawrectangle({coil_r1}, {coil_z1}, {coil_r2}, {coil_z2})
""" + mark_line("after_coil_geom") + f"""
mi_drawrectangle(0, -{Rb}, {Rb}, {Zb})
""" + mark_line("after_boundary_geom") + f"""
mi_addboundprop("A0", 0,0,0,0,0,0,0,0,0)

mi_selectsegment({Rb/2}, -{Rb})
mi_setsegmentprop("A0", 0, 1, 0, 0, 0, 0)
mi_clearselected()

mi_selectsegment({Rb}, {(Zb-Rb)/2})
mi_setsegmentprop("A0", 0, 1, 0, 0, 0, 0)
mi_clearselected()

mi_selectsegment({Rb/2}, {Zb})
mi_setsegmentprop("A0", 0, 1, 0, 0, 0, 0)
mi_clearselected()
""" + mark_line("after_boundary_bc") + f"""
mi_addcircprop("COIL", {p.I_a}, 1)
""" + mark_line("after_circuit") + f"""
mi_addblocklabel({tip_r/2}, {tip_L/2})
mi_selectlabel({tip_r/2}, {tip_L/2})
mi_setblockprop("Pure Iron", 1, 0, "", 0, 0, 0)
mi_clearselected()
""" + mark_line("after_tip_label") + f"""
mi_addblocklabel({(coil_r1+coil_r2)/2}, {(coil_z1+coil_z2)/2})
mi_selectlabel({(coil_r1+coil_r2)/2}, {(coil_z1+coil_z2)/2})
mi_setblockprop("COPPER", 1, 0, "COIL", 0, 0, {p.turns})
mi_clearselected()
""" + mark_line("after_coil_label") + f"""
mi_addblocklabel({Rb*0.7}, -{Rb*0.3})
mi_selectlabel({Rb*0.7}, -{Rb*0.3})
mi_setblockprop("AIR", 1, 0, "", 0, 0, 0)
mi_clearselected()
""" + mark_line("after_air_label") + f"""
mi_smartmesh(1)
mi_saveas("{fem_path}")
""" + mark_line("after_save") + f"""
mi_analyze()
""" + mark_line("after_analyze") + f"""
mi_loadsolution()

""" + mark_line("after_loadsolution") + f"""
mo_selectblock({tip_r/2}, {tip_L/2})
i0 = mo_blockintegral(0)
i1 = mo_blockintegral(1)
i2 = mo_blockintegral(2)
i3 = mo_blockintegral(3)

f = openfile("{ptxt_path}", "w")
write(f, i2)
write(f, "\\n")
closefile(f)

fm = openfile("{meta_path}", "w")
write(fm, "{{\\"i0\\":"..i0..",\\"i1\\":"..i1..",\\"i2\\":"..i2..",\\"i3\\":"..i3.."}}")
closefile(fm)

""" + mark_line("done") + """
mo_close()
mi_close()
quit()
"""
    lua_path.write_text(lua)

def estimate_power_w_from_femm(stl_path: Path, p: EMParams) -> float:
    tip_proxy = stl_path.parent / "tip_proxy.json"
    if tip_proxy.exists():
        tip = json.loads(tip_proxy.read_text())
    else:
        tip = {"tip_r_mm": 1.5, "tip_L_mm": 12.0}

    out_dir_wsl = Path("/mnt/c/temp/ito_femm")
    out_dir_wsl.mkdir(parents=True, exist_ok=True)

    lua_path = out_dir_wsl / "run_femm.lua"
    _write_lua(lua_path, p=p, tip=tip)

    femm_exe = _find_femm_exe()
    cmd = [femm_exe, r"-lua-script=C:\temp\ito_femm\run_femm.lua"]
    subprocess.run(cmd, capture_output=True, text=True)

    ptxt = out_dir_wsl / "p_tip_W.txt"
    prog = out_dir_wsl / "progress.txt"
    if not ptxt.exists():
        prog_msg = prog.read_text().strip() if prog.exists() else "no progress.txt"
        raise RuntimeError(f"FEMM did not produce p_tip_W.txt. progress={prog_msg}.")

    # Create i2.txt for compatibility (some steps expect it)
    i2txt = out_dir_wsl / "i2.txt"
    shutil.copyfile(ptxt, i2txt)

    return float(ptxt.read_text().strip())
