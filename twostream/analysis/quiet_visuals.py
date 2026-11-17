#!/usr/bin/env python3
"""Side-by-side random-start vs quiet-start versions of the talk visuals (same style as
slide_figures.py), from the quiet smoke run and the random-start baseline.

  growth_fastest_mode_compare.png  |E_7(t)| for both starts, each with its no-fit e^{γt} line
  growth_rate_vs_k_compare.png     γ(k): median ± spread over sliding fit windows, both starts
  spacetime_Ex_quiet.png           E_x(x, t) of the quiet run, linear color
  phase_space_quiet.png            quiet-run phase space at three times

Usage:
    conda run -n analysis python twostream/analysis/quiet_visuals.py QUIET_RUN RANDOM_RUN --out DIR
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slide_figures as sf  # noqa: E402  (shared style)
import chen_ee as ce  # noqa: E402
import twostream_analysis as ta  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

QUIET = "#1b7837"
WIN = 40.0


def load(run):
    ff = ta.field_files(run)
    cfg = ta.read_config(ff[0])
    th = ta.Theory(cfg)
    ee = ce.ChenEE(th, cfg)
    t, Ek, E, x = ce.modes(ff, "fE1")
    L = float(cfg["grid.extent"][1]) - float(cfg["grid.extent"][0])
    k = 2 * np.pi * np.arange(Ek.shape[1]) / L
    band = np.arange(1, Ek.shape[1])[ee.y(k[1:]) < 1]
    return dict(run=Path(run), ff=ff, t=t, Ek=Ek, E=E, x=x, k=k, ee=ee, th=th, L=L, band=band)


def sliding(D, starts):
    t, Ek = D["t"], D["Ek"]
    sl = np.array([[ce.linfit(t[(t >= s) & (t <= s + WIN)],
                              np.log(np.abs(Ek[(t >= s) & (t <= s + WIN), m])))[0] for s in starts]
                   for m in D["band"]]) / D["ee"].wp
    return np.median(sl, axis=1), sl.std(axis=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("quiet")
    ap.add_argument("random")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--quiet-window", nargs=2, type=float, default=(115.0, 280.0),
                    help="clean-growth range of the quiet run [code time]")
    ap.add_argument("--random-window", nargs=2, type=float, default=(40.0, 160.0))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    Q, R = load(a.quiet), load(a.random)
    ee, wp = R["ee"], R["ee"].wp
    m7 = 7

    # ---- 1. fastest mode, both starts, each with its own no-fit theory line
    fig, ax = plt.subplots(figsize=sf.SIZE)
    for D, c, lab, (w0, w1) in ((R, sf.BEAM2, "random start", a.random_window),
                                (Q, QUIET, "quiet start", a.quiet_window)):
        sel = D["t"] <= Q["t"].max()
        ax.semilogy(D["t"][sel] * wp, np.abs(D["Ek"][sel, m7]), color=c, label=lab)
        i0 = int(np.argmin(np.abs(D["t"] - w0)))
        tp = D["t"][(D["t"] >= D["t"][i0]) & (D["t"] <= w1 + 30)]
        ax.semilogy(tp * wp, np.abs(D["Ek"][i0, m7]) * np.exp(ee.gamma(D["k"][m7]) * (tp - D["t"][i0])),
                    "--", color=sf.THEORY, lw=2.5)
    ax.plot([], [], "--", color=sf.THEORY, lw=2.5, label="theory  $e^{\\gamma t}$  (no fitting)")
    ax.set_xlabel("time (1/ω$_p$)")
    ax.set_ylabel("fastest-wave amplitude\n(code units, log scale)")
    ax.set_ylim(1e-5, 1.0)
    h, l = ax.get_legend_handles_labels()
    ax.legend(h, l, loc="lower right", fontsize=15)
    fig.tight_layout()
    sf.save(fig, a.out, "growth_fastest_mode_compare.png")

    # ---- 2. gamma(k), both starts, honest window-spread error bars
    gR, eR = sliding(R, np.arange(a.random_window[0], a.random_window[1] - WIN + 1, 4.0))
    gQ, eQ = sliding(Q, np.arange(a.quiet_window[0], a.quiet_window[1] - WIN + 1, 4.0))
    yR, yQ = ee.y(R["k"][R["band"]]), ee.y(Q["k"][Q["band"]])
    fig, ax = plt.subplots(figsize=sf.SIZE)
    y = np.linspace(0, 1.15, 600)
    ax.plot(y, ee.growth_x(y), color=sf.THEORY, label="theory (Chen)")
    ax.errorbar(yR - 0.008, gR, yerr=eR, fmt="o", color=sf.BEAM2, mfc="white", mew=2, ms=8, capsize=4,
                lw=1.5, label="random start")
    ax.errorbar(yQ + 0.008, gQ, yerr=eQ, fmt="o", color=QUIET, ms=9, capsize=4, lw=2, label="quiet start")
    ax.set_xlabel("wavenumber  $kv_0/\\omega_p$")
    ax.set_ylabel("growth rate  γ/ω$_p$")
    ax.set_xlim(0, 1.15)
    ax.set_ylim(0, 0.8)
    ax.legend(loc="upper left", fontsize=15)
    fig.tight_layout()
    sf.save(fig, a.out, "growth_rate_vs_k_compare.png")

    core = (R["band"] >= 4) & (R["band"] <= 9)
    th_core = ee.gamma(R["k"][R["band"][core]]) / wp
    print(f"{'m':>2} {'theory':>7} {'random':>14} {'quiet':>14}")
    for m, gt, gr, er, gq, eq in zip(R["band"], ee.gamma(R["k"][R["band"]]) / wp, gR, eR, gQ, eQ):
        print(f"{m:2d} {gt:7.3f}   {gr:5.3f} ± {er:5.3f}   {gq:5.3f} ± {eq:5.3f}")
    for lab, g, e in (("random", gR, eR), ("quiet", gQ, eQ)):
        r = g[core] / th_core
        print(f"{lab:6s} m=4-9: mean ratio {r.mean():.2f}, ratio scatter {r.std(ddof=1):.2f}, "
              f"median window spread {np.median(e[core] / th_core):.2f} of theory")
    i7 = list(R["band"]).index(m7)
    print(f"fastest wave m=7: random {gR[i7]:.3f} ± {eR[i7]:.3f}, quiet {gQ[i7]:.3f} ± {eQ[i7]:.3f}, "
          f"theory {1/(2*np.sqrt(2)):.3f}")

    # ---- 3. space-time E_x of the quiet run (linear color), same layout as slide_movies
    E = Q["E"]
    nx = E.shape[1] // 12 * 12
    Eb = E[:, :nx].reshape(len(Q["t"]), -1, 12).mean(axis=2)
    xb = Q["x"][:nx].reshape(-1, 12).mean(axis=1)
    lim = np.percentile(np.abs(Eb), 99.5)
    fig, ax = plt.subplots(figsize=sf.SIZE)
    im = ax.imshow(Eb, origin="lower", aspect="auto", cmap="RdBu_r", vmin=-lim, vmax=lim,
                   extent=(xb[0] * wp, xb[-1] * wp, Q["t"][0] * wp, Q["t"][-1] * wp), interpolation="nearest")
    ax.set_xlabel("position (c/ω$_p$)")
    ax.set_ylabel("time (1/ω$_p$)")
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("electric field $E_x$ (code units)", fontsize=16)
    fig.tight_layout()
    sf.save(fig, a.out, "spacetime_Ex_quiet.png")

    # ---- 4. quiet phase space at three times
    pfiles = sorted((Q["run"] / "particles").glob("particles.*.bp"))
    ptimes = ce.file_times(pfiles)
    fig, axs = plt.subplots(1, 3, figsize=sf.SIZE, sharey=True)
    for ax, tw in zip(axs, (0.0, 0.5 * Q["t"].max() * wp, Q["t"].max() * wp)):
        tt, d = sf.beams_at(pfiles, ptimes, tw / wp)
        sf.phase_axes(ax, d, wp)
        ax.set_title(f"$t$ = {tt*wp:.0f} / ω$_p$", fontsize=17)
        ax.set_xlabel("position (c/ω$_p$)")
        ax.set_ylim(-0.25, 0.25)
    axs[0].set_ylabel("velocity (c)")
    fig.tight_layout()
    sf.save(fig, a.out, "phase_space_quiet.png")


if __name__ == "__main__":
    main()
