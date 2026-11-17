#!/usr/bin/env python3
"""Quiet-start vs random-start noise comparison for the e-e two-stream runs.

For modes m = 4-9 it reports, versus time over the first T/omega_p:
  - |dn_m|/n_b (beam 1) and |E_m| in both runs,
  - the effective seed: the amplitude the instability amplifies, i.e. a fit of
    ln|E_m| over its clean exponential stretch extrapolated back to t = 0,
  - the delay of the m=4-9 band energy reaching a common threshold, which converts to
    extra clean e-folds as gamma_max * delay.

Usage:
    conda run -n analysis python twostream/analysis/quiet_compare.py QUIET_RUN RANDOM_RUN --out DIR
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chen_ee as ce  # noqa: E402
import twostream_analysis as ta  # noqa: E402

BAND = list(range(4, 10))


def load(run, tmax_code):
    ff = ta.field_files(run)
    cfg = ta.read_config(ff[0])
    th = ta.Theory(cfg)
    ee = ce.ChenEE(th, cfg)
    t, Ek, _, _ = ce.modes(ff, "fE1")
    _, N1, _, _ = ce.modes(ff, "fN_1")
    keep = t <= tmax_code
    L = float(cfg["grid.extent"][1]) - float(cfg["grid.extent"][0])
    k = 2 * np.pi * np.arange(Ek.shape[1]) / L
    return dict(t=t[keep], E=np.abs(Ek[keep]), N=np.abs(N1[keep]) / ee.nb, k=k, ee=ee, th=th)


def clean_fit(t, a, g_th, lo=0.6, hi=1.4, min_len=8):
    """Longest stretch where the local log-slope stays within [lo, hi] x theory; fit it."""
    la = np.log(np.maximum(a, 1e-300))
    s = np.gradient(la, t)
    nsm = 5
    s = np.convolve(s, np.ones(nsm) / nsm, mode="same")
    ok = (s > lo * g_th) & (s < hi * g_th)
    best, cur = (0, 0), None
    for i, v in enumerate(ok):
        if v and cur is None:
            cur = i
        if (not v or i == len(ok) - 1) and cur is not None:
            j = i if v else i - 1
            if j - cur > best[1] - best[0]:
                best = (cur, j)
            cur = None
    i0, i1 = best
    if i1 - i0 + 1 < min_len:
        return np.nan, np.nan, (np.nan, np.nan)
    p = np.polyfit(t[i0 : i1 + 1], la[i0 : i1 + 1], 1)
    return p[0], np.exp(p[1]), (t[i0], t[i1])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("quiet")
    ap.add_argument("random")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tmax", type=float, default=20.0, help="[1/omega_p]")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    Rr = load(a.random, 1e9)
    wp = Rr["ee"].wp
    tmax = a.tmax / wp
    Q = load(a.quiet, tmax)
    R = load(a.random, tmax)
    ee, th = R["ee"], R["th"]

    print(f"{'m':>2} {'g_th/wp':>7} | {'seed_random':>11} {'fit window':>13} | {'seed_quiet':>10} "
          f"{'fit window':>13} | {'ratio':>6} {'+e-folds':>8}")
    rows = []
    for m in BAND:
        g = ee.gamma(R["k"][m])
        gr, sr, wr = clean_fit(R["t"], R["E"][:, m], g)
        gq, sq, wq = clean_fit(Q["t"], Q["E"][:, m], g)
        ratio = sr / sq
        rows.append((m, ratio))
        print(f"{m:2d} {g/wp:7.3f} | {sr:11.2e} {wr[0]*wp:5.1f}-{wr[1]*wp:5.1f}/wp | {sq:10.2e} "
              f"{wq[0]*wp:5.1f}-{wq[1]*wp:5.1f}/wp | {ratio:6.1f} {np.log(ratio):8.2f}")
    rat = np.array([r for _, r in rows])
    fin = np.isfinite(rat) & (rat > 0)
    if fin.any():
        print(f"geometric-mean seed reduction (m=4-9): {np.exp(np.log(rat[fin]).mean()):.1f}x "
              f"= +{np.log(rat[fin]).mean():.2f} clean e-folds")

    WR = (R["E"][:, BAND] ** 2).sum(axis=1)
    WQ = (Q["E"][:, BAND] ** 2).sum(axis=1)
    thr = 1e-2 * WR.max()
    tR = R["t"][np.argmax(WR >= thr)] if (WR >= thr).any() else np.nan
    tQ = Q["t"][np.argmax(WQ >= thr)] if (WQ >= thr).any() else np.nan
    print(f"band energy reaches 1% of random-start peak: random t = {tR*wp:.1f}/wp, quiet t = {tQ*wp:.1f}/wp"
          f" -> delay {(tQ-tR)*wp:.1f}/wp = +{th.gamma_max*(tQ-tR):.2f} e-folds at gamma_max")
    for lab, D in (("random", R), ("quiet", Q)):
        early = D["t"] * wp <= 1.0
        mid = (D["t"] * wp > 4) & (D["t"] * wp <= 6)
        print(f"{lab:6s} median |dn_m|/n_b m=4-9:  t<=1/wp {np.median(D['N'][early][:, BAND]):.2e}   "
              f"t=4-6/wp {np.median(D['N'][mid][:, BAND]):.2e}")

    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax, key, lab in ((axs[0], "N", r"$|\delta n_m|/n_b$ (beam 1)"), (axs[1], "E", r"$|E_m|$")):
        for D, c, name in ((R, "C3", "random start"), (Q, "C0", "quiet start")):
            for j, m in enumerate(BAND):
                ax.semilogy(D["t"] * wp, D[key][:, m], color=c, lw=0.8, alpha=0.6,
                            label=name if j == 0 else None)
        ax.set_xlabel("time (1/ω$_p$)")
        ax.set_ylabel(lab + "  (log scale)")
        ax.legend(fontsize=9)
    fig.suptitle("Modes m = 4–9: quiet vs random start", fontsize=10)
    fig.tight_layout()
    fig.savefig(a.out / "quiet_vs_random_noise.png", dpi=150)
    print("wrote", a.out / "quiet_vs_random_noise.png")


if __name__ == "__main__":
    main()
