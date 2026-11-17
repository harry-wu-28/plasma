#!/usr/bin/env python3
"""Talk figures from the quiet-start smoke run (job 11092712), plus the canonical numbers.

  growth_rate_vs_k.png          showcase: theory + quiet-start γ(k), slow growers lighter
  growth_fastest_mode.png       |E_7(t)| with the no-fit e^{γt} line
  spacetime_Ex.png (+_normalized)
  gamma_k_quiet_vs_random.png   backup: quiet vs random-start γ(k)

Growth rates are medians over 40-unit fit windows sliding across the clean-growth range,
with the window spread as the error bar (same method as slide_figures.py).

Usage:
    conda run -n analysis python twostream/results/talk/scripts/talk_quiet_figures.py QUIET RANDOM --out twostream/results/talk/figures
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "analysis"))  # chen_ee, twostream_analysis
import slide_figures as sf  # noqa: E402  (shared style)
import quiet_visuals as qv  # noqa: E402
import chen_ee as ce  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

LIGHT = "0.62"
MIN_EFOLDS = 3.0


def gamma_k_axes(ax, ee):
    y = np.linspace(0, 1.15, 600)
    ax.plot(y, ee.growth_x(y), color=sf.THEORY, label="theory (Chen)")
    ax.set_xlabel("wavenumber  $kv_0/\\omega_p$")
    ax.set_ylabel("growth rate  γ/ω$_p$")
    ax.set_xlim(0, 1.15)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("quiet")
    ap.add_argument("random")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--quiet-window", nargs=2, type=float, default=(115.0, 280.0))
    ap.add_argument("--random-window", nargs=2, type=float, default=(40.0, 160.0))
    ap.add_argument("--tmax", type=float, default=None,
                    help="cut the quiet run at this code time and mark it as saturation")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    Q, R = qv.load(a.quiet), qv.load(a.random)
    if a.tmax is not None:
        keep = Q["t"] <= a.tmax
        for key in ("t", "Ek", "E"):
            Q[key] = Q[key][keep]
    ee, wp = Q["ee"], Q["ee"].wp
    w0, w1 = a.quiet_window
    starts = np.arange(w0, w1 - qv.WIN + 1, 4.0)

    band = Q["band"]
    gQ, eQ = qv.sliding(Q, starts)
    gR, eR = qv.sliding(R, np.arange(a.random_window[0], a.random_window[1] - qv.WIN + 1, 4.0))
    yb = ee.y(Q["k"][band])
    gth = ee.gamma(Q["k"][band]) / wp
    efolds_th = gth * wp * (w1 - w0)
    clean = efolds_th >= MIN_EFOLDS
    i7 = list(band).index(7)
    core = (band >= 4) & (band <= 9)

    # ------------------------------------------------ canonical numbers
    ratio = gQ[core] / gth[core]
    err_cons = np.sqrt(((eQ[core] / gth[core]) ** 2).sum()) / core.sum()
    win = (Q["t"] >= w0) & (Q["t"] <= w1)
    re_w = [abs(ce.linfit(Q["t"][win], -np.unwrap(np.angle(Q["Ek"][win, m])))[0]) / wp for m in band[core]]
    t0 = int(np.argmin(np.abs(Q["t"] - w0)))
    t1i = int(np.argmin(np.abs(Q["t"] - w1))) if a.tmax is not None else len(Q["t"]) - 1
    efolds_7 = np.log(np.abs(Q["Ek"][t1i, 7]) / np.abs(Q["Ek"][t0, 7]))
    print(f"slow growers (theory < {MIN_EFOLDS:.0f} e-folds over t={w0:.0f}-{w1:.0f}): m = {band[~clean].tolist()}")
    print(f"m=7: γ = {gQ[i7]:.3f} ± {eQ[i7]:.3f} ω_p   (theory {1/(2*np.sqrt(2)):.3f})")
    print(f"m=4-9 mean ratio = {ratio.mean():.2f} ± {err_cons:.2f} (conservative, propagated window spreads); "
          f"ratio scatter SE = {ratio.std(ddof=1)/np.sqrt(core.sum()):.2f}")
    print(f"median window spread m=4-9 = {np.median(eQ[core] / gth[core]):.2f} of theory")
    print(f"clean growth of m=7: {Q['t'][t0]*wp:.1f} -> {Q['t'][t1i]*wp:.1f}/ω_p = {efolds_7:.1f} e-folds "
          f"(amplitude x{np.exp(efolds_7):.0f})"
          + (f"; saturation at {Q['t'][-1]*wp:.1f}/ω_p" if a.tmax is not None else ", still growing at the end"))
    print(f"|Re ω| over the window, m=4-9: max {max(re_w):.3f} ω_p (beam Doppler kv0 = "
          f"{yb[core].min():.2f}-{yb[core].max():.2f} ω_p)")
    for m, y_, g, e, t_ in zip(band, yb, gQ, eQ, gth):
        print(f"  m={m:2d} y={y_:.3f}  γ={g:.3f}±{e:.3f}  theory {t_:.3f}")

    # ------------------------------------------------ 1. showcase γ(k)
    fig, ax = plt.subplots(figsize=sf.SIZE)
    gamma_k_axes(ax, ee)
    ax.errorbar(yb[~clean], gQ[~clean], yerr=eQ[~clean], fmt="o", color=LIGHT, mfc="white", ms=7,
                mew=1.5, capsize=3, lw=1.2, label="slow growers (hard to measure)")
    ax.errorbar(yb[clean], gQ[clean], yerr=eQ[clean], fmt="o", color=sf.BEAM1, ms=11, capsize=5, lw=2.5,
                label="simulation")
    ax.plot(yb[i7], gQ[i7], "o", ms=20, mfc="none", mec=sf.BEAM2, mew=3)
    ax.annotate(f"fastest wave\nsimulation {gQ[i7]:.3f} ± {eQ[i7]:.3f}\ntheory       {1/(2*np.sqrt(2)):.3f}",
                xy=(yb[i7], gQ[i7] - 0.025), xytext=(0.33, 0.12), fontsize=16, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", lw=2, color=sf.BEAM2))
    ax.set_ylim(0, 0.7)
    h, l = ax.get_legend_handles_labels()
    order = [0, 2, 1]
    ax.legend([h[i] for i in order], [l[i] for i in order], loc="upper left", fontsize=14)
    fig.tight_layout()
    sf.save(fig, a.out, "growth_rate_vs_k.png")

    # ------------------------------------------------ 2. fastest mode
    fig, ax = plt.subplots(figsize=sf.SIZE)
    t = Q["t"]
    t_line_end = w1 + 40.0 if a.tmax is not None else t[-1]
    tp = t[(t >= t[t0]) & (t <= t_line_end)]
    ax.axvspan(w0 * wp, (w1 if a.tmax is not None else t[-1]) * wp, color="0.92", zorder=0)
    ax.semilogy(t * wp, np.abs(Q["Ek"][:, 7]), color=sf.BEAM1, label="simulation")
    ax.semilogy(tp * wp, np.abs(Q["Ek"][t0, 7]) * np.exp(ee.gamma(Q["k"][7]) * (tp - t[t0])), "--",
                color=sf.THEORY, label="theory  $e^{\\gamma t}$  (no fitting)")
    if a.tmax is not None:
        ax.axvline(t[-1] * wp, color="k", ls="--", lw=1.2)
        ax.text(t[-1] * wp - 0.3, 3e-5, "growth stops\n(saturation)", ha="right", va="bottom",
                fontsize=14, color="0.2")
    else:
        ax.text(t[-1] * wp - 0.3, 3e-5, "still growing\nwhen the run ends", ha="right", va="bottom",
                fontsize=14, color="0.35")
    ax.set_xlabel("time (1/ω$_p$)")
    ax.set_ylabel("wave amplitude\n(code units, log scale)")
    ax.set_ylim(1e-5, 1.0)
    ax.set_xlim(0, t[-1] * wp + 0.5)
    ax.legend(loc="upper left")
    fig.tight_layout()
    sf.save(fig, a.out, "growth_fastest_mode.png")

    # ------------------------------------------------ 3. space-time
    E = Q["E"]
    nx = E.shape[1] // 12 * 12
    Eb = E[:, :nx].reshape(len(t), -1, 12).mean(axis=2)
    xb = Q["x"][:nx].reshape(-1, 12).mean(axis=1)
    ext = (xb[0] * wp, xb[-1] * wp, t[0] * wp, t[-1] * wp)
    for name, data, lim, label in (
        ("spacetime_Ex.png", Eb, np.percentile(np.abs(Eb), 99.5), "electric field $E_x$ (code units)"),
        ("spacetime_Ex_normalized.png", Eb / np.sqrt((Eb**2).mean(axis=1, keepdims=True)), 2.5,
         "$E_x$ ÷ its rms at that time"),
    ):
        fig, ax = plt.subplots(figsize=sf.SIZE)
        im = ax.imshow(data, origin="lower", aspect="auto", extent=ext, cmap="RdBu_r", vmin=-lim, vmax=lim,
                       interpolation="nearest")
        ax.set_xlabel("position (c/ω$_p$)")
        ax.set_ylabel("time (1/ω$_p$)")
        cb = fig.colorbar(im, ax=ax, pad=0.02)
        cb.set_label(label, fontsize=16)
        if a.tmax is not None:
            ax.axhline(t[-1] * wp, color="k", ls="--", lw=1.2)
            ax.text(ext[1] - 0.05, t[-1] * wp - 0.3, "growth stops (saturation)", ha="right", va="top",
                    fontsize=16, bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=2))
        fig.tight_layout()
        sf.save(fig, a.out, name)

    # ------------------------------------------------ 4. backup: quiet start only, every wave alike
    fig, ax = plt.subplots(figsize=sf.SIZE)
    gamma_k_axes(ax, ee)
    ax.errorbar(yb, gQ, yerr=eQ, fmt="o", color=sf.BEAM1, ms=10, capsize=4, lw=2.2, label="simulation")
    ax.set_ylim(0, 0.8)
    ax.legend(loc="upper left", fontsize=15)
    fig.tight_layout()
    sf.save(fig, a.out, "gamma_k_quiet_vs_random.png")


if __name__ == "__main__":
    main()
