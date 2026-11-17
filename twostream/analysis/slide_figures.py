#!/usr/bin/env python3
"""Simplified, slide-ready figures for the e-e two-stream talk (one idea per figure).

Units on every axis: time in 1/omega_p, position in c/omega_p, velocity in c, where
omega_p is the plasma frequency of all the electrons (Chen's notation).
Colors everywhere: beam 1 (moving right) blue, beam 2 (moving left) red, theory black.

Usage:
    conda run -n analysis python twostream/analysis/slide_figures.py \
        /dartfs-hpc/scratch/f007hd2/twostream/cpu/twostream_baseline --out talk/figures
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from adios2 import FileReader

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chen_ee as ce  # noqa: E402
import twostream_analysis as ta  # noqa: E402

BEAM1, BEAM2, THEORY = "#2166ac", "#d6604d", "black"
START, LATE = "0.45", "#1b7837"
SIZE = (10, 5.6)
DPI = 200

plt.rcParams.update({
    "font.size": 18, "axes.labelsize": 19, "axes.titlesize": 19, "legend.fontsize": 16,
    "xtick.labelsize": 16, "ytick.labelsize": 16, "lines.linewidth": 3,
    "axes.linewidth": 1.4, "figure.facecolor": "white", "axes.facecolor": "white",
    "savefig.facecolor": "white", "axes.spines.top": False, "axes.spines.right": False,
})


def save(fig, out, name):
    fig.savefig(out / name, dpi=DPI)
    plt.close(fig)
    print("wrote", out / name)


def beams_at(pfiles, ptimes, t):
    p = pfiles[int(np.argmin(np.abs(ptimes - t)))]
    with FileReader(str(p)) as f:
        tt = float(f.read("Time"))
        d = {s: (np.asarray(f.read(f"pX1_{s}")), np.asarray(f.read(f"pU1_{s}"))) for s in (1, 3)}
    return tt, d


def speed(u):
    return u / np.sqrt(1 + u**2)


# ---------------------------------------------------------------- 1 dispersion


def fig_dispersion(out):
    fig, axs = plt.subplots(1, 2, figsize=SIZE, sharey=True)
    x = np.linspace(-2.6, 2.6, 20001)
    for ax, y, title in ((axs[0], 1.4, "$kv_0/\\omega_p = 1.4$:  4 crossings → stable"),
                         (axs[1], np.sqrt(3 / 8), "$kv_0/\\omega_p = 0.61$:  2 crossings → grows")):
        F = ce.ChenEE.F(x, y)
        F[F > 4.5] = np.nan
        ax.plot(x, F, color=THEORY)
        ax.axhline(1, color="0.5", ls="--", lw=2)
        Fz = np.nan_to_num(F - 1, nan=1e9)
        idx = [i for i in np.where(np.diff(np.sign(Fz)) != 0)[0] if abs(Fz[i]) < 0.5]
        ax.plot(x[idx], np.ones(len(idx)), "o", color=BEAM2, ms=12, zorder=5)
        ax.set_title(title, pad=10, fontsize=17)
        ax.set_xlabel("frequency  ω/ω$_p$")
        ax.set_ylim(0, 3.2)
        ax.set_xlim(-2.6, 2.6)
    axs[0].set_ylabel("$F(\\omega)$")
    axs[1].text(0, 1.08, "$F = 1$", ha="center", va="bottom", fontsize=15, color="0.4")
    fig.tight_layout()
    save(fig, out, "dispersion_stable_unstable.png")


# ---------------------------------------------------------------- 2 phase space


def phase_axes(ax, d, wp, every=1, ms=1.2):
    for s, c in ((1, BEAM1), (3, BEAM2)):
        X, U = d[s]
        ax.plot(X[::every] * wp, speed(U[::every]), ".", color=c, ms=ms, alpha=0.6, rasterized=True)


def fig_phase(pfiles, ptimes, wp, times, out):
    fig, axs = plt.subplots(1, 3, figsize=SIZE, sharey=True)
    for ax, (lab, t) in zip(axs, times):
        tt, d = beams_at(pfiles, ptimes, t)
        phase_axes(ax, d, wp)
        ax.set_title(f"{lab}\n$t$ = {tt*wp:.0f} / ω$_p$", fontsize=17)
        ax.set_xlabel("position (c/ω$_p$)")
        ax.set_ylim(-0.25, 0.25)
    axs[0].set_ylabel("velocity (c)")
    h = [plt.Line2D([], [], marker="o", ls="", color=c, ms=9) for c in (BEAM1, BEAM2)]
    axs[0].legend(h, ["beam 1 (→)", "beam 2 (←)"], loc="lower left", fontsize=14, framealpha=0.9)
    fig.tight_layout()
    save(fig, out, "phase_space.png")


# ---------------------------------------------------------------- 3 fastest mode


def fig_growth(t, Ek, k, ee, m7, t1, t2, wp, out):
    fig, ax = plt.subplots(figsize=SIZE)
    sel = t <= 300
    i0 = int(np.argmin(np.abs(t - t1)))
    tp = t[(t >= t[i0]) & (t <= 210)]
    g = ee.gamma(k[m7])
    ax.axvspan(t1 * wp, t2 * wp, color="0.92", zorder=0)
    ax.semilogy(t[sel] * wp, np.abs(Ek[sel, m7]), color=BEAM1, label="simulation")
    ax.semilogy(tp * wp, np.abs(Ek[i0, m7]) * np.exp(g * (tp - t[i0])), "--", color=THEORY,
                label="theory  $e^{\\gamma t}$  (no fitting)")
    ax.text(0.5 * (t1 + t2) * wp, 2.0 * np.abs(Ek[sel, m7]).max(), "linear\ngrowth", ha="center",
            va="top", fontsize=14, color="0.35")
    ax.set_xlabel("time (1/ω$_p$)")
    ax.set_ylabel("wave amplitude\n(code units, log scale)")
    ax.set_ylim(np.abs(Ek[sel, m7])[5:].min() / 3, 3 * np.abs(Ek[sel, m7]).max())
    ax.legend(loc="lower right")
    fig.tight_layout()
    save(fig, out, "growth_fastest_mode.png")


# ---------------------------------------------------------------- 4 gamma(k)


def fig_gamma_k(ee, ys, gs, ges, m_idx, out):
    """gs, ges: median and spread of the growth rate over sliding fit windows (honest error)."""
    fig, ax = plt.subplots(figsize=SIZE)
    y = np.linspace(0, 1.15, 600)
    ax.plot(y, ee.growth_x(y), color=THEORY, label="theory (Chen)")
    ax.errorbar(ys, gs, yerr=ges, fmt="o", color=BEAM1, ms=10, capsize=5, lw=2,
                label="simulation (bar = spread over fit windows)")
    ax.plot(ys[m_idx], gs[m_idx], "o", ms=18, mfc="none", mec=BEAM2, mew=3)
    ax.annotate(f"fastest wave\nsimulation {gs[m_idx]:.2f} ± {ges[m_idx]:.2f}\ntheory       {1/(2*np.sqrt(2)):.2f}",
                xy=(ys[m_idx], gs[m_idx]), xytext=(0.74, 0.70), textcoords="data", fontsize=15,
                arrowprops=dict(arrowstyle="->", lw=2, color=BEAM2), ha="left", va="center")
    ax.set_xlabel("wavenumber  $kv_0/\\omega_p$")
    ax.set_ylabel("growth rate  γ/ω$_p$")
    ax.set_xlim(0, 1.15)
    ax.set_ylim(0, 0.8)
    ax.legend(loc="upper left", fontsize=15)
    fig.tight_layout()
    save(fig, out, "growth_rate_vs_k.png")


# ---------------------------------------------------------------- 5 f(v)


def fig_fv(pfiles, ptimes, out, late_from=900.0):
    """Both curves normalized to unit area (same number of electrons); the late curve is
    averaged over all snapshots with t >= late_from to smooth particle noise."""
    edges = np.linspace(-0.3, 0.3, 41)
    vc = 0.5 * (edges[1:] + edges[:-1])

    def f_of_v(paths):
        v = []
        for p in paths:
            with FileReader(str(p)) as f:
                v.append(speed(np.concatenate([np.asarray(f.read(f"pU1_{s}")) for s in (1, 3)])))
        h, _ = np.histogram(np.concatenate(v), bins=edges, density=True)
        return h

    order = np.argsort(ptimes)
    start = [pfiles[order[0]]]
    late = [pfiles[i] for i in order if ptimes[i] >= late_from]
    fig, ax = plt.subplots(figsize=SIZE)
    ax.plot(vc, f_of_v(start), color=START, label="start")
    ax.plot(vc, f_of_v(late), color=LATE, label="end of run")
    ax.set_xlabel("velocity (c)")
    ax.set_ylabel("electrons per unit velocity\n(same total in both)")
    ax.set_xlim(-0.3, 0.3)
    ax.set_ylim(0, None)
    ax.legend(loc="upper right")
    print(f"f(v): late average over {len(late)} snapshots, t = {ptimes[order][ptimes[order] >= late_from].min():.0f}"
          f"-{ptimes.max():.0f}")
    fig.tight_layout()
    save(fig, out, "fv_plateau.png")


# ---------------------------------------------------------------- 6 backup


def fig_separatrix(ffiles, ftimes, pfiles, ptimes, ee, t_sat, L, mlp, wp, out):
    tt, d = beams_at(pfiles, ptimes, t_sat)
    fp = ffiles[int(np.argmin(np.abs(ftimes - tt)))]
    with FileReader(str(fp)) as f:
        E = np.asarray(f.read("fE1"), dtype=float)
        xg = np.asarray(f.read("X1"), dtype=float)
    E = ce.lowpass(E - E.mean(), mlp)
    U = np.cumsum(E) * (L / len(E)) / ee.rl0
    vs = np.sqrt(np.clip(2 * (U.max() - U), 0, None))
    fig, ax = plt.subplots(figsize=SIZE)
    phase_axes(ax, d, wp, ms=1.6)
    for sgn in (1, -1):
        ax.plot(xg * wp, sgn * speed(vs), color=THEORY, lw=2.5)
    ax.plot([], [], color=THEORY, lw=2.5, label="trapping boundary (from measured field)")
    ax.set_xlabel("position (c/ω$_p$)")
    ax.set_ylabel("velocity (c)")
    ax.set_ylim(-0.25, 0.25)
    ax.legend(loc="lower left", fontsize=14, framealpha=0.9)
    fig.tight_layout()
    save(fig, out, "trapping_separatrix.png")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--window", nargs=2, type=float, default=(60.0, 140.0))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    t1, t2 = a.window
    run = Path(a.run)

    ffiles = ta.field_files(run)
    cfg = ta.read_config(ffiles[0])
    th = ta.Theory(cfg)
    ee = ce.ChenEE(th, cfg)
    wp = ee.wp
    ext = cfg["grid.extent"]
    L = float(ext[1]) - float(ext[0])

    t, Ek, _, _ = ce.modes(ffiles, "fE1")
    m = np.arange(Ek.shape[1])
    k = 2 * np.pi * m / L
    band = m[(m > 0) & (ee.y(k) < 1)]
    win = (t >= t1) & (t <= t2)
    fits = np.array([ce.linfit(t[win], np.log(np.abs(Ek[win, mm]))) for mm in band])
    gs, ges = fits[:, 0] / wp, fits[:, 1] / wp
    ys = ee.y(k[band])
    m7 = int(band[np.argmin(np.abs(ys - np.sqrt(3 / 8)))])
    W = (np.abs(Ek[:, band]) ** 2).sum(axis=1)
    i_sat = int(np.argmax(np.where(t <= t2 + 3.0 / th.gamma_max, W, -1)))
    print(f"fastest box mode m={m7}: gamma/wp = {gs[band == m7][0]:.3f} vs theory {1/(2*np.sqrt(2)):.3f}; "
          f"saturation t = {t[i_sat]:.0f} ({t[i_sat]*wp:.1f}/wp)")

    pfiles = sorted((run / "particles").glob("particles.*.bp"))
    ptimes = ce.file_times(pfiles)

    fig_dispersion(a.out)
    fig_phase(pfiles, ptimes, wp, [("start", 0.0), ("during growth", t2), ("trapped vortices", t[i_sat])], a.out)
    fig_growth(t, Ek, k, ee, m7, t1, t2, wp, a.out)
    # honest uncertainty: fit 40-unit windows sliding across t = 40-160 (before saturation)
    starts = np.arange(40.0, 121.0, 4.0)
    sl = np.array([[ce.linfit(t[(t >= s) & (t <= s + 40)], np.log(np.abs(Ek[(t >= s) & (t <= s + 40), mm])))[0]
                    for s in starts] for mm in band]) / wp
    gmed, gspread = np.median(sl, axis=1), sl.std(axis=1)
    core = (band >= 4) & (band <= 9)
    print("sliding-window gamma/wp (median +- std):",
          ", ".join(f"m{mm}: {g:.2f}+-{e:.2f}" for mm, g, e in zip(band, gmed, gspread)))
    print(f"core m=4-9 mean(sim)/mean(theory) = {gmed[core].mean() / (ee.gamma(k[band[core]]).mean() / wp):.2f}")
    fig_gamma_k(ee, ys, gmed, gspread, int(np.where(band == m7)[0][0]), a.out)
    fig_fv(pfiles, ptimes, a.out)
    fig_separatrix(ffiles, t, pfiles, ptimes, ee, t[i_sat], L, int(2 * band.max()), wp, a.out)


if __name__ == "__main__":
    main()
