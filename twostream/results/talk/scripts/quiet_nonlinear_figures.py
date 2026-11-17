#!/usr/bin/env python3
"""Nonlinear-phase talk figures from the full quiet-start run, reusing the slide_figures /
slide_movies functions (same style) but only these outputs, so the linear-phase figures made
by talk_quiet_figures.py are not overwritten:

  phase_space.png, phase_space.mp4 / .gif, fv_plateau.png, trapping_separatrix.png

Usage:
    conda run -n analysis python twostream/results/talk/scripts/quiet_nonlinear_figures.py \
        /dartfs-hpc/scratch/f007hd2/twostream/quiet/quiet_visual --out twostream/results/talk/figures
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "analysis"))  # chen_ee, twostream_analysis
import slide_figures as sf  # noqa: E402
import slide_movies as sm  # noqa: E402
import chen_ee as ce  # noqa: E402
import twostream_analysis as ta  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--t-growth", type=float, default=20.0, help="'during growth' still [1/omega_p]")
    ap.add_argument("--t-full", type=float, default=40.0, help="every snapshot up to this time [1/omega_p]")
    ap.add_argument("--stride-late", type=int, default=3)
    ap.add_argument("--late-from", type=float, default=900.0, help="f(v) late average from [code]")
    ap.add_argument("--t-vortex", type=float, default=None,
                    help="'trapped vortices' still and separatrix time [1/omega_p] (default: saturation)")
    ap.add_argument("--no-movie", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    run = Path(a.run)

    ffiles = ta.field_files(run)
    cfg = ta.read_config(ffiles[0])
    th = ta.Theory(cfg)
    ee = ce.ChenEE(th, cfg)
    wp = ee.wp
    L = float(cfg["grid.extent"][1]) - float(cfg["grid.extent"][0])
    t, Ek, _, _ = ce.modes(ffiles, "fE1")
    k = 2 * np.pi * np.arange(Ek.shape[1]) / L
    band = np.arange(1, Ek.shape[1])[ee.y(k[1:]) < 1]
    W = np.convolve((np.abs(Ek[:, band]) ** 2).sum(axis=1), np.ones(3) / 3, mode="same")
    peaks = [i for i in range(2, len(W) - 2) if W[i] >= W[i - 1] and W[i] >= W[i + 1] and W[i] > 0.3 * W.max()]
    t_sat = float(t[peaks[0]])
    print(f"saturation (first field-energy peak): t = {t_sat:.0f} code = {t_sat*wp:.1f}/omega_p")

    pfiles = sorted((run / "particles").glob("particles.*.bp"))
    ptimes = ce.file_times(pfiles)
    t_vort = a.t_vortex / wp if a.t_vortex is not None else t_sat
    stills = [("start", 0.0), ("during growth", a.t_growth / wp), ("trapped vortices", t_vort)]
    print("phase-space stills at t =", ", ".join(f"{s[1]*wp:.1f}/omega_p" for s in stills))
    sf.fig_phase(pfiles, ptimes, wp, stills, a.out)
    sf.fig_fv(pfiles, ptimes, a.out, late_from=a.late_from)
    sf.fig_separatrix(ffiles, t, pfiles, ptimes, ee, t_vort, L, int(2 * band.max()), wp, a.out)
    if not a.no_movie:
        frames = sm.frame_list(ptimes, wp, a.t_full, a.stride_late)
        sm.movie(pfiles, ptimes, wp, frames, a.out)


if __name__ == "__main__":
    main()
