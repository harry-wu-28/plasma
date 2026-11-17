#!/usr/bin/env python3
"""Electron beam through stationary ions (Chen §6.6, the Buneman instability):
measured growth rate and frequency of each box mode vs Chen's Eq. 6.30.

Usage (analysis env has adios2):
    conda run -n analysis python twostream/analysis/buneman_analysis.py \
        /dartfs-hpc/scratch/f007hd2/twostream/cpu/buneman \
        --out twostream/runs/buneman/plots [--window T1 T2]

Theory (Chen Eq. 6.30, both species cold):
    1 = w_pi^2 / w^2 + w_pe^2 / (w - k v0)^2
solved as a quartic for every k. w_pe uses the longitudinal mass gamma0^3 m
(0.75% shift at u0 = 0.1). The "warm" curve replaces the electron term with
w_pe^2 / ((w - k v0)^2 - 3 k^2 v_th^2) (Bohm-Gross pressure), a fluid estimate of
how much the finite beam temperature reduces the growth.

Species (1-based): 1 = beam e-, 2 = ions, 3/4 = rigid return current + its
neutralizing background (see runs/buneman/inputs/buneman.toml).

Outputs in --out:
    buneman_dispersion.png   Re/Im w(k): Chen roots vs measured gamma and Re w per mode
    buneman_modes.png        |E_m(t)| for band modes, field energy, theory slope
    buneman_k0.png           mean Ex (k = 0) vs the band amplitude: return current check
    buneman_energy.png       field energy vs electron kinetic energy loss
    buneman_phase.png        electron and ion x-u phase space at selected times
    buneman_gamma_k.csv      per-mode measured gamma, Re w, theory values
"""

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from adios2 import FileReader

sys.path.insert(0, str(Path(__file__).resolve().parent))
import twostream_analysis as ta  # noqa: E402


class Buneman:
    def __init__(self, cfg):
        d0 = float(cfg["scales.skindepth0"])
        self.sigma0 = (d0 / float(cfg["scales.larmor0"])) ** 2
        dens = cfg["setup.densities"]
        drifts = cfg["setup.drifts_in_x"]
        temps = cfg["setup.temperatures"]
        masses = [float(cfg[k]) for k in sorted(cfg) if k.startswith("particles.species") and k.endswith(".mass")]
        self.M = float(cfg.get("particles.species[1].mass", masses[1] if len(masses) > 1 else 1836.0))
        self.u0 = float(drifts[0])
        self.gamma0 = np.sqrt(1 + self.u0**2)
        self.v0 = self.u0 / self.gamma0
        n = float(dens[0]) / 2.0
        self.wpe_nr = np.sqrt(n) / d0
        self.wpe = self.wpe_nr / self.gamma0**1.5
        self.wpi = np.sqrt(n / self.M) / d0
        self.vth = np.sqrt(float(temps[0])) / self.gamma0  # rough, beam-frame spread
        mu = (self.wpi / self.wpe) ** 2
        self.gamma_est = np.sqrt(3) / 2 * (mu / 2) ** (1 / 3) * self.wpe

    def roots(self, k, warm=False):
        """All 4 roots of (w^2 - wpi^2)((w-kv)^2 - a) - wpe^2 w^2 = 0, a = 3k^2vth^2 if warm."""
        out = []
        for kk in np.atleast_1d(k):
            kv = kk * self.v0
            a = 3 * (kk * self.vth) ** 2 if warm else 0.0
            p1 = np.poly1d([1, 0, -self.wpi**2])
            p2 = np.poly1d([1, -2 * kv, kv**2 - a])
            p = p1 * p2 - np.poly1d([self.wpe**2, 0, 0])
            out.append(np.sort_complex(np.roots(p.coeffs)))
        return np.asarray(out)

    def growing(self, k, warm=False):
        r = self.roots(k, warm)
        i = np.argmax(r.imag, axis=1)
        w = r[np.arange(len(r)), i]
        return np.where(w.imag > 0, w.imag, 0.0), np.where(w.imag > 0, w.real, np.nan)


def read_species_particles(path, s):
    with FileReader(str(path)) as f:
        t = float(f.read("Time"))
        X = np.asarray(f.read(f"pX1_{s}"))
        U = np.asarray(f.read(f"pU1_{s}"))
    return t, X, U


def auto_window(t, Ek, band, gam):
    """Stretch where the smoothed d ln W/dt of the band energy stays > 1/2 its max, before the peak."""
    W = (np.abs(Ek[:, band]) ** 2).sum(axis=1)
    lnW = np.log(W)
    dt = np.median(np.diff(t))
    nsm = max(1, int(round(0.5 / gam / dt)))
    s = np.gradient(np.convolve(lnW, np.ones(nsm) / nsm, mode="same"), t)
    ipk = int(np.argmax(W))
    ok = (np.arange(len(t)) <= ipk) & (np.arange(len(t)) >= nsm)
    s = np.where(ok, s, -np.inf)
    im = int(np.argmax(s))
    i1 = i2 = im
    while i1 > 0 and s[i1 - 1] > 0.5 * s[im]:
        i1 -= 1
    while i2 < len(t) - 1 and s[i2 + 1] > 0.5 * s[im]:
        i2 += 1
    return t[i1], t[i2], ipk


def fit_mode(t, c, t1, t2):
    sel = (t >= t1) & (t <= t2)
    if sel.sum() < 4:
        return (np.nan,) * 3
    pg, cov = np.polyfit(t[sel], np.log(np.abs(c[sel])), 1, cov=True)
    ph = np.unwrap(np.angle(c[sel]))
    pw = np.polyfit(t[sel], ph, 1)
    # rfft of A cos(kx - wt) gives coefficient ~ exp(-i w t): phase slope = -w
    return pg[0], np.sqrt(cov[0, 0]), -pw[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--window", nargs=2, type=float, default=None)
    ap.add_argument("--min-efolds", type=float, default=1.5,
                    help="count a mode only if gamma_cold*(t2-t1) >= this (same rule as the e-e figure)")
    ap.add_argument("--phase-times", nargs="+", type=float, default=None)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    files = ta.field_files(a.run)
    cfg = ta.read_config(files[0])
    th = Buneman(cfg)
    t, E, x = ta.read_field_series(files, "fE1")
    nx = E.shape[1]
    L = nx * (x[1] - x[0])
    Ek = np.fft.rfft(E, axis=1) * 2.0 / nx
    m = np.arange(Ek.shape[1])
    k = 2 * np.pi * m / L

    kk = np.linspace(1e-3, 2.0 * th.wpe / th.v0, 600)
    g_cold, wr_cold = th.growing(kk)
    g_warm, wr_warm = th.growing(kk, warm=True)
    g_m, wr_m = th.growing(k[1:])
    g_m = np.r_[0, g_m]
    wr_m = np.r_[np.nan, wr_m]
    band = np.where(g_m > 0.3 * g_m.max())[0]
    gmax = g_cold.max()
    print(f"u0={th.u0} v0={th.v0:.4f} M/m={th.M:g} wpe={th.wpe:.5f} (nr {th.wpe_nr:.5f}) wpi={th.wpi:.3e}")
    print(f"Chen cold: gamma_max={gmax:.5f} ({gmax/th.wpe:.4f} wpe) at k={kk[np.argmax(g_cold)]:.3f} "
          f"(k v0/wpe={kk[np.argmax(g_cold)]*th.v0/th.wpe:.3f}); estimate (sqrt3/2)(m/2M)^1/3 wpe={th.gamma_est:.5f}")
    print(f"warm (Bohm-Gross): gamma_max={g_warm.max():.5f}; box modes in band: m={band.min()}..{band.max()}")

    if a.window:
        t1, t2 = a.window
        ipk = int(np.argmax((np.abs(Ek[:, band]) ** 2).sum(axis=1)))
    else:
        t1, t2, ipk = auto_window(t, Ek, band, gmax)
    print(f"fit window t = [{t1:g}, {t2:g}] (auto unless --window); band energy peaks at t = {t[ipk]:g}")

    rows = []
    for mm in range(1, int(1.6 * band.max()) + 1):
        gfit, gerr, wfit = fit_mode(t, Ek[:, mm], t1, t2)
        efolds = g_m[mm] * (t2 - t1)
        rows.append(dict(m=mm, k=k[mm], kv0_wpe=k[mm] * th.v0 / th.wpe, gamma_fit=gfit, gamma_err=gerr,
                         gamma_cold=g_m[mm], gamma_warm=th.growing([k[mm]], warm=True)[0][0],
                         re_w_fit=wfit, re_w_cold=wr_m[mm], efolds_th=efolds,
                         counted=int(efolds >= a.min_efolds)))
    with open(a.out / "buneman_gamma_k.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"window covers {gmax * (t2 - t1):.2f} e-folds at gamma_max; modes need >= {a.min_efolds} theoretical e-folds")
    print(" m     k   kv0/wpe  gamma_fit    ±       cold   fit/cold  e-folds  counted  Re w fit  Re w cold")
    for r in rows:
        ratio = r["gamma_fit"] / r["gamma_cold"] if r["gamma_cold"] > 0 else np.nan
        print(f"{r['m']:2d} {r['k']:6.3f} {r['kv0_wpe']:6.3f}  {r['gamma_fit']:8.5f} {r['gamma_err']:7.5f} "
              f"{r['gamma_cold']:8.5f} {ratio:7.2f}  {r['efolds_th']:6.2f}   {'yes' if r['counted'] else ' - '}    "
              f"{r['re_w_fit']:8.5f}  {r['re_w_cold']:8.5f}")

    R = {key: np.array([r[key] for r in rows]) for key in rows[0]}
    inb = R["counted"].astype(bool)

    # ---- dispersion
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    xk = kk * th.v0 / th.wpe
    ax[0].plot(xk, g_cold / th.wpe, "k-", label="Chen Eq. 6.30 (cold)")
    ax[0].plot(xk, g_warm / th.wpe, "k--", lw=1, label=r"warm e$^-$ (Bohm–Gross)")
    ax[0].errorbar(R["kv0_wpe"][inb], R["gamma_fit"][inb] / th.wpe, R["gamma_err"][inb] / th.wpe,
                   fmt="o", color="C3", label=f"PIC, >= {a.min_efolds:g} e-folds in window")
    ax[0].plot(R["kv0_wpe"][~inb], R["gamma_fit"][~inb] / th.wpe, "o", mfc="none", color="C3", alpha=0.5,
               label="PIC, too few e-folds (not counted)")
    ax[0].set(xlabel=r"$k v_0/\omega_{pe}$", ylabel=r"$\mathrm{Im}\,\omega/\omega_{pe}$",
              title=f"growth rate, fit t = [{t1:g}, {t2:g}]")
    ax[0].axhline(0, color="0.7", lw=0.5)
    ax[0].legend(fontsize=8)
    ax[1].plot(xk, wr_cold / th.wpe, "k-", label="Chen (growing root)")
    ax[1].plot(R["kv0_wpe"][inb], R["re_w_fit"][inb] / th.wpe, "o", color="C0", label="PIC (counted modes)")
    ax[1].set(xlabel=r"$k v_0/\omega_{pe}$", ylabel=r"$\mathrm{Re}\,\omega/\omega_{pe}$", title="real frequency")
    ax[1].legend(fontsize=8)
    fig.suptitle(f"Electron beam through ions, M/m = {th.M:g}, u0 = {th.u0:g}")
    fig.tight_layout()
    fig.savefig(a.out / "buneman_dispersion.png", dpi=150)
    plt.close(fig)

    # ---- mode histories
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    mpk = band[np.argmax(g_m[band])]
    for mm in sorted(set([band.min(), mpk, band.max(), max(1, band.min() // 2)])):
        ax.semilogy(t, np.abs(Ek[:, mm]), lw=1, label=f"m={mm} (k v0/wpe={k[mm]*th.v0/th.wpe:.2f})")
    Wb = np.sqrt((np.abs(Ek[:, band]) ** 2).sum(axis=1))
    ax.semilogy(t, Wb, "k", lw=1.5, label="band rms")
    sel = (t >= t1) & (t <= t2)
    i0 = np.argmax(sel)
    ax.semilogy(t[sel], Wb[i0] * np.exp(gmax * (t[sel] - t[i0])), "r--", label=r"$e^{\gamma_{max} t}$ (Chen)")
    ax.axvspan(t1, t2, color="0.9")
    ax.set(xlabel=r"t  ($\omega_{pe}^{-1}$ = " f"{1/th.wpe:.1f})", ylabel=r"$|E_m|$", title="mode growth")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(a.out / "buneman_modes.png", dpi=150)
    plt.close(fig)

    # ---- k = 0 check
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.semilogy(t, np.abs(Ek[:, 0]) / 2, label=r"|mean $E_x$| (k = 0)")
    ax.semilogy(t, Wb, label="band rms")
    # without the return current: dEx/dt = -Jx gives |Ex| ~ J0/wpe; in these units
    # J0 = (n e v0) and the Poisson constant C = larmor0/skindepth0^2 (README).
    J0 = th.v0 * float(cfg["setup.densities"][0]) / 2 * float(cfg["scales.larmor0"]) / float(cfg["scales.skindepth0"]) ** 2
    ax.axhline(J0 / th.wpe_nr, color="r", ls="--", lw=1, label=r"$J_0/\omega_{pe}$ (uncompensated)")
    ax.set(xlabel="t", ylabel=r"$|E|$", title="return-current check")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(a.out / "buneman_k0.png", dpi=150)
    plt.close(fig)

    # ---- energy
    s = ta.read_stats(a.run)
    if s is not None:
        tt = s["time"] if "time" in s else s[list(s)[0]]
        e2 = sum(s[c] for c in s if c.startswith("E") and c.endswith("^2"))  # E1^2, E2^2, E3^2
        Wf = th.sigma0 / 2 * e2
        ke = [c for c in s if c.startswith("T00") and c.endswith("_1")]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.semilogy(tt, Wf, label="field energy")
        if ke:
            dK = s[ke[0]][0] - s[ke[0]]
            ax.semilogy(tt, np.abs(dK), label=r"electron energy lost $|\Delta T^{00}_1|$")
            Kb = s[ke[0]][0] - float(cfg["setup.densities"][0]) / 2
            ax.axhline(Kb, color="0.5", ls=":", label="initial beam kinetic energy")
        ax.set(xlabel="t", ylabel=r"energy density ($n_0 m c^2$)", title="energy exchange")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(a.out / "buneman_energy.png", dpi=150)
        plt.close(fig)
        print("stats columns:", ", ".join(s))

    # ---- phase space
    pfiles = sorted((a.run / "particles").glob("particles.*.bp"))
    if pfiles:
        ptimes = np.array([read_species_particles(p, 1)[0] for p in pfiles])
        want = a.phase_times or [0.0, t2, t[ipk], ptimes[-1]]
        idx = sorted(set(int(np.argmin(np.abs(ptimes - w))) for w in want))
        fig, ax = plt.subplots(2, len(idx), figsize=(3.4 * len(idx), 5.5), squeeze=False)
        for j, i in enumerate(idx):
            for row, sp, col in ((0, 1, "C0"), (1, 2, "C3")):
                tp, X, U = read_species_particles(pfiles[i], sp)
                ax[row, j].plot(X, U, ",", color=col, alpha=0.4)
                ax[row, j].set_title(f"{'electrons' if sp == 1 else 'ions'}, t = {tp:g}", fontsize=9)
                ax[row, j].set_xlim(x[0], x[0] + L / 4)
            ax[1, j].set_xlabel("x")
        ax[0, 0].set_ylabel(r"$u_x$ (e$^-$)")
        ax[1, 0].set_ylabel(r"$u_x$ (ion, per mass)")
        fig.tight_layout()
        fig.savefig(a.out / "buneman_phase.png", dpi=150)
        plt.close(fig)


if __name__ == "__main__":
    main()
