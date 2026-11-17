#!/usr/bin/env python3
"""Chen §6.6 two-stream algebra redone for two cold counter-streaming electron beams
(his Problem 6.6), with his figures redrawn for that case and every analytic result
checked against an Entity run. Derivation: twostream/theory/chen_ee_derivation.md.

Notation follows Chen: omega_p is the plasma frequency of ALL the electrons (each beam
has half the density, omega_p^2 = 2 omega_b^2), x = omega/omega_p, y = k v0/omega_p.

Figures (PREFIX_*.png):
  fig6_8_6_9   F(x, y) = 1 graphically: Chen's ion-electron case (his Figs 6.8/6.9)
               and the electron-electron case, stable and unstable
  roots        Re x and Im x vs y: exact e-e roots, measured points, Chen's
               ion-electron (Buneman) roots for contrast
  growth       |E_m(t)| vs the no-fit prediction exp(gamma(k)(t - t0))
  eigenvector  bunching phase and amplitude of the growing mode vs theory
  fig7_11_7_12 measured electron potential energy and constant-energy contours
               (trajectories) over the phase-space density, at saturation
  fig7_13      phase-space density at increasing times, empty region shaded
  fig7_19      f(u_x): double-humped start, positive-slope region, plateau

Usage:
    conda run -n analysis python twostream/analysis/chen_ee.py RUN --out DIR [--window 60 140]
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from adios2 import FileReader
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import twostream_analysis as ta  # noqa: E402

MU = 1 / 1836.15  # m/M for Chen's ion-electron case


# ======================================================================= theory


class ChenEE:
    """Cold symmetric e-e two-stream, Chen's notation."""

    def __init__(self, th, cfg):
        self.wb, self.v0, self.nb = th.omega_b, th.v0, th.n_beam
        self.wp = np.sqrt(2.0) * th.omega_b
        self.rl0 = float(cfg["scales.larmor0"])
        self.meff = th.gamma0**3  # longitudinal mass for small oscillations of a drifting beam

    def y(self, k):
        return np.asarray(k) * self.v0 / self.wp

    @staticmethod
    def F(x, y):
        return 0.5 * (1 / (x - y) ** 2 + 1 / (x + y) ** 2)

    @staticmethod
    def x2(y):
        """the two roots for x^2: y^2 + 1/2 +- (1/2) sqrt(1 + 8 y^2)"""
        s = 0.5 * np.sqrt(1 + 8 * np.asarray(y) ** 2)
        return y**2 + 0.5 + s, y**2 + 0.5 - s

    def growth_x(self, y):
        return np.sqrt(np.clip(-self.x2(y)[1], 0, None))

    def gamma(self, k):
        return self.wp * self.growth_x(self.y(k))

    def alpha(self, k):
        return np.arctan2(self.gamma(k), np.asarray(k) * self.v0)

    def dn_over_E(self, k, sign):
        """dn_j/n_b per unit E_k (code units), growing root; sign=+1 for the +v0 beam."""
        w = 1j * self.gamma(k)
        return -1j * k / (self.meff * self.rl0 * (w - sign * k * self.v0) ** 2)


def F_ie(x, y):
    return MU / x**2 + 1 / (x - y) ** 2


def buneman_growth(y):
    """max Im root of Chen Eq. 6.30 (ion-electron): (x^2-mu)(x-y)^2 - x^2 = 0."""
    out = []
    for yy in np.atleast_1d(y):
        r = np.roots([1, -2 * yy, yy**2 - MU - 1, 2 * MU * yy, -MU * yy**2])
        out.append(max(0.0, r.imag.max()))
    return np.asarray(out)


# ======================================================================= data


def file_times(files):
    out = []
    for p in files:
        with FileReader(str(p)) as f:
            out.append(float(f.read("Time")))
    return np.asarray(out)


def modes(files, name):
    t, A, x = ta.read_field_series(files, name)
    return t, np.fft.rfft(A, axis=1) * 2.0 / A.shape[1], A, x


def read_particles(path):
    with FileReader(str(path)) as f:
        t = float(f.read("Time"))
        X = np.concatenate([np.asarray(f.read(f"pX1_{s}")) for s in (1, 3)])
        U = np.concatenate([np.asarray(f.read(f"pU1_{s}")) for s in (1, 3)])
        W = np.concatenate([np.asarray(f.read(f"pW_{s}")) for s in (1, 3)])
    return t, X, U, W


def smooth2d(H, sx, su):
    """Gaussian smoothing via FFT (periodic in both axes; f is ~0 at the u edges)."""
    nx, nu = H.shape
    kx = np.fft.fftfreq(nx)[:, None]
    ku = np.fft.fftfreq(nu)[None, :]
    G = np.exp(-2 * np.pi**2 * ((sx * kx) ** 2 + (su * ku) ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(H) * G))


def phase_hist(path, L, x0, umax, nx=128, nu=96, sm=(1.2, 1.2)):
    t, X, U, W = read_particles(path)
    H, xe, ue = np.histogram2d(X, U, bins=(nx, nu), range=((x0, x0 + L), (-umax, umax)), weights=W)
    return t, smooth2d(H, *sm), xe, ue


def lowpass(a, mmax):
    A = np.fft.rfft(a, axis=-1)
    A[..., mmax + 1 :] = 0
    return np.fft.irfft(A, n=a.shape[-1], axis=-1)


def linfit(t, y):
    p, cov = np.polyfit(t, y, 1, cov=True)
    return p[0], np.sqrt(cov[0, 0])


def circ(z):
    u = z / np.abs(z)
    R = np.abs(u.mean())
    return np.degrees(np.angle(u.mean())), np.degrees(np.sqrt(max(-2 * np.log(max(R, 1e-12)), 0)))


def wrap(a):
    return (np.asarray(a) + 180.0) % 360.0 - 180.0


def masked(F, top):
    F = np.array(F, dtype=float)
    F[F > 1.5 * top] = np.nan
    return F


# ======================================================================= figures


def fig_F(ee, out):
    fig, axs = plt.subplots(2, 2, figsize=(10, 6.6))
    yc_ie = (1 + MU ** (1 / 3)) ** 1.5
    cases = [
        (axs[0, 0], F_ie, 1.6, (-0.8, 3.2), "Chen Fig. 6.8 (ion–electron), stable: y = 1.6"),
        (axs[0, 1], F_ie, 0.8, (-0.8, 3.2), "Chen Fig. 6.9 (ion–electron), unstable: y = 0.8"),
        (axs[1, 0], ChenEE.F, 1.4, (-2.6, 2.6), "electron–electron, stable: y = 1.4"),
        (axs[1, 1], ChenEE.F, np.sqrt(3 / 8), (-2.6, 2.6),
         r"electron–electron, unstable: $y=\sqrt{3/8}$ (fastest)"),
    ]
    for ax, F, yv, xr, title in cases:
        x = np.linspace(*xr, 20001)
        Fx = F(x, yv)
        ax.plot(x, masked(Fx, 3), "k-", lw=1.4)
        ax.axhline(1, color="k", ls="--", lw=0.8)
        poles = (0.0, yv) if F is F_ie else (-yv, yv)
        for p in poles:
            ax.axvline(p, color="k", lw=0.6)
        cross = np.where(np.diff(np.sign(np.nan_to_num(Fx - 1, nan=1e9))) != 0)[0]
        cross = [i for i in cross if abs(Fx[i] - 1) < 0.5 and abs(Fx[i + 1] - 1) < 0.5]
        ax.plot(x[cross], np.ones(len(cross)), "o", color="C3", ms=5)
        ax.text(0.98, 0.95, f"{len(cross)} real roots\n{4 - len(cross)} complex",
                transform=ax.transAxes, ha="right", va="top", fontsize=8, color="C3")
        ax.set_ylim(0, 3)
        ax.set_xlim(*xr)
        ax.set_title(title, fontsize=9)
        ax.set_xlabel(r"$x=\omega/\omega_p$")
        ax.set_ylabel(r"$F(x,y)$")
    axs[0, 0].text(0.02, 0.95, r"$F=\frac{m/M}{x^2}+\frac{1}{(x-y)^2}$" + f"\nunstable for y < {yc_ie:.3f}",
                   transform=axs[0, 0].transAxes, va="top", fontsize=8)
    axs[1, 0].text(0.02, 0.95, r"$F=\frac{1}{2}\left[\frac{1}{(x-y)^2}+\frac{1}{(x+y)^2}\right]$"
                   + "\n" + r"min $F(0,y)=1/y^2$: unstable for $y<1$",
                   transform=axs[1, 0].transAxes, va="top", fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "fig6_8_6_9.png", dpi=150)
    plt.close(fig)


def fig_roots(ee, M, out, t1, t2):
    y = np.linspace(1e-3, 2.0, 1500)
    xp2, xm2 = ee.x2(y)
    fig, axs = plt.subplots(2, 1, figsize=(6.4, 6.4), sharex=True)
    ax = axs[0]
    ax.plot(y, np.sqrt(xp2), "k-", label="real root pair $\\pm x_+$")
    ax.plot(y, np.where(xm2 >= 0, np.sqrt(np.clip(xm2, 0, None)), np.nan), "k--",
            label="real root pair $\\pm x_-$ (y > 1)")
    ax.plot(y, np.where(xm2 < 0, 0.0, np.nan), color="C3", lw=2, label="complex pair: Re x = 0")
    ax.errorbar(M["y"], M["wr"] / ee.wp, yerr=M["wre"] / ee.wp, fmt="o", ms=3, capsize=2, color="C3",
                label="measured Re x")
    ax.plot(y, y, color="0.6", lw=0.6, label="y (beam Doppler shift)")
    ax.set_ylabel(r"Re $x$")
    ax.set_ylim(-0.4, 3.2)
    ax.legend(fontsize=7, loc="upper left")
    ax = axs[1]
    ax.plot(y, ee.growth_x(y), "k-", label="e–e exact: $\\sqrt{\\frac{1}{2}\\sqrt{1+8y^2}-y^2-\\frac{1}{2}}$")
    ax.errorbar(M["y"], M["g"] / ee.wp, yerr=M["ge"] / ee.wp, fmt="o", ms=3, capsize=2, color="C3",
                label=f"measured (fit t = {t1:.0f}–{t2:.0f})")
    ax.plot(y, buneman_growth(y), color="0.5", ls="-.", lw=1, label="Chen ion–e (Eq. 6.30 roots)")
    ax.axhline(MU ** (1 / 3), color="0.5", ls=":", lw=0.8)
    ax.text(1.55, MU ** (1 / 3) + 0.01, r"Eq. 6.35: $(m/M)^{1/3}$", fontsize=7, color="0.4")
    ax.axhline(1 / (2 * np.sqrt(2)), color="C0", ls=":", lw=0.8)
    ax.text(1.32, 1 / (2 * np.sqrt(2)) + 0.01, r"Prob. 6.6b: $1/(2\sqrt{2})$", fontsize=7, color="C0")
    ax.axvline(1, color="C1", lw=0.6)
    ax.set_ylim(0, 0.5)
    ax.set_xlabel(r"$y = kv_0/\omega_p$")
    ax.set_ylabel(r"Im $x$ = $\gamma/\omega_p$")
    ax.legend(fontsize=7, loc="upper right")
    fig.tight_layout()
    fig.savefig(out / "roots.png", dpi=150)
    plt.close(fig)


def fig_growth(ee, t, Ek, k, band, i_sat, t1, t2, out):
    show = [mm for mm in band if 3 <= mm <= 10][:6]
    fig, axs = plt.subplots(2, 4, figsize=(13, 5.6), sharex=True)
    axs = axs.ravel()
    i0 = int(np.argmin(np.abs(t - t1)))
    sel = t <= t[i_sat] + 60
    tp = t[(t >= t[i0]) & sel]
    for ax, mm in zip(axs, show):
        ax.semilogy(t[sel], np.abs(Ek[sel, mm]), "C0", lw=1, label="simulation")
        ax.semilogy(tp, np.abs(Ek[i0, mm]) * np.exp(ee.gamma(k[mm]) * (tp - t[i0])), "k--", lw=1,
                    label=f"theory, no fit, from t = {t[i0]:.0f}")
        ax.set_title(f"m = {mm},  y = {ee.y(k[mm]):.3f}", fontsize=8)
    axs[0].legend(fontsize=7)
    W = (np.abs(Ek[:, band]) ** 2).sum(axis=1)
    ax = axs[len(show)]
    ax.semilogy(t[sel], W[sel], "C0", lw=1)
    ax.semilogy(tp, [(np.abs(Ek[i0, band]) ** 2 * np.exp(2 * ee.gamma(k[band]) * (tt - t[i0]))).sum()
                     for tt in tp], "k--", lw=1)
    ax.set_title("unstable band (y < 1): $\\Sigma|E_m|^2$", fontsize=8)
    ax = axs[len(show) + 1]
    stab = (ee.y(k) > 1) & (np.arange(len(k)) <= 2 * band.max())
    ax.semilogy(t[sel], (np.abs(Ek[sel][:, stab]) ** 2).sum(axis=1), "C2", lw=1, label="stable band (y > 1)")
    ax.semilogy(t[sel], W[sel], "C0", lw=0.6, alpha=0.6, label="unstable band")
    ax.set_title("cutoff y = 1", fontsize=8)
    ax.legend(fontsize=7)
    for ax in axs:
        ax.axvspan(t1, t2, color="0.9", zorder=0)
    for ax in axs[4:]:
        ax.set_xlabel("$t$")
    fig.suptitle("Mode amplitudes |E_m(t)| vs analytic growth (grey: linear window)", fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "growth.png", dpi=150)
    plt.close(fig)


def fig_eigen(ee, M, out, ta_, tb):
    y = np.linspace(1e-3, 0.999, 600)
    k = y * ee.wp / ee.v0
    km = M["k"]

    def near(meas, th):  # put each measured angle on the 360-degree branch closest to theory
        return th + wrap(meas - th)

    th13 = 4 * np.degrees(ee.alpha(km))
    th1E = np.degrees(np.angle(ee.dn_over_E(km, 1)))
    th3E = np.degrees(np.angle(ee.dn_over_E(km, -1)))
    fig, axs = plt.subplots(1, 3, figsize=(13, 3.8))
    ax = axs[0]
    ax.plot(y, 4 * np.degrees(ee.alpha(k)), "k-", label=r"theory $4\alpha$, $\tan\alpha=\gamma/kv_0$")
    ax.errorbar(M["y"], near(M["a13"], th13), yerr=M["s13"], fmt="o", ms=3, capsize=2, color="C3",
                label="measured")
    ax.set_ylabel(r"arg($n_{1}/n_{2}$) [deg]")
    ax.set_ylim(-30, 300)
    ax.set_title("phase between the two beams' bunches", fontsize=9)
    ax = axs[1]
    ax.plot(y, np.degrees(np.angle(ee.dn_over_E(k, 1))), "C0-", label="theory, +v0 beam")
    ax.plot(y, np.degrees(np.angle(ee.dn_over_E(k, -1))), "C3-", label="theory, −v0 beam")
    ax.errorbar(M["y"], near(M["a1E"], th1E), yerr=M["s1E"], fmt="o", ms=3, capsize=2, color="C0",
                label="measured, +v0")
    ax.errorbar(M["y"], near(M["a3E"], th3E), yerr=M["s3E"], fmt="s", ms=3, capsize=2, color="C3",
                label="measured, −v0")
    ax.set_ylabel(r"arg($n_{j}/E$) [deg]")
    ax.set_ylim(-250, 70)
    ax.set_title("phase of each bunch relative to $E$", fontsize=9)
    ax = axs[2]
    ax.semilogy(y, np.abs(ee.dn_over_E(k, 1)), "k-", label="theory (both beams)")
    ax.semilogy(M["y"], M["amp1"], "o", ms=3, color="C0", label="measured, +v0")
    ax.semilogy(M["y"], M["amp3"], "s", ms=3, color="C3", label="measured, −v0")
    ax.set_ylim(0.8, 30)
    ax.set_ylabel(r"$|n_{j}/n_b|\ /\ |E_k|$")
    ax.set_title("bunching per unit field", fontsize=9)
    for ax in axs:
        ax.set_xlabel(r"$y = kv_0/\omega_p$")
        ax.set_xlim(0, 1.05)
        ax.axvline(1, color="C1", lw=0.6)
        ax.legend(fontsize=7)
    fig.suptitle(f"Linear eigenvector, Eqs. (6.23′)–(6.27′), measured over t = {ta_:.0f}–{tb:.0f}",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "eigenvector.png", dpi=150)
    plt.close(fig)


def fig_trapping(ee, ffiles, ftimes, pfiles, ptimes, t_sat, L, x0, mlp, out):
    umax = 3 * ee.v0
    p = pfiles[int(np.argmin(np.abs(ptimes - t_sat)))]
    tp, H, xe, ue = phase_hist(p, L, x0, umax, nx=200, nu=120)
    fp = ffiles[int(np.argmin(np.abs(ftimes - tp)))]
    with FileReader(str(fp)) as f:
        E = np.asarray(f.read("fE1"), dtype=float)
        xg = np.asarray(f.read("X1"), dtype=float)
    E = lowpass(E - E.mean(), mlp)
    U = np.cumsum(E) * (L / len(E)) / ee.rl0  # electron potential energy, dU/dx = E/rL0
    U -= U.min()
    fig, axs = plt.subplots(2, 1, figsize=(9, 6.2), sharex=True, gridspec_kw=dict(height_ratios=[1, 2.2]))
    ax = axs[0]
    ax.plot(xg, U, "k-")
    ax.set_ylabel(r"$-e\phi_1$ [$mc^2$]")
    ax.set_title(f"Chen Fig. 7.11: potential energy of an electron in the wave (measured, t = {tp:.0f}; "
                 "Re ω = 0 so the lab frame is the wave frame)", fontsize=8)
    ax = axs[1]
    xc, uc = 0.5 * (xe[1:] + xe[:-1]), 0.5 * (ue[1:] + ue[:-1])
    ax.pcolormesh(xe, ue, H.T, cmap="Greys", shading="auto")
    Ui = np.interp(xc, xg, U)
    Ham = np.sqrt(1 + uc[None, :] ** 2) + Ui[:, None]
    Hs = 1 + U.max()
    lev = np.sort(np.concatenate([1 + np.linspace(0.05, 0.95, 5) * U.max(), Hs + np.array([0.3, 1.0, 2.5]) * U.max()]))
    ax.contour(xc, uc, Ham.T, levels=lev, colors="C0", linewidths=0.6)
    ax.contour(xc, uc, Ham.T, levels=[Hs], colors="C3", linewidths=1.3)
    ax.set_xlabel("$x$")
    ax.set_ylabel(r"$u_x$")
    ax.set_title("Chen Fig. 7.12: trajectories (constant $\\gamma mc^2 - e\\phi$, blue; separatrix red) "
                 "over the simulated $f(x,u_x)$", fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "fig7_11_7_12.png", dpi=150)
    plt.close(fig)


def fig_water_bags(ee, pfiles, ptimes, times, L, x0, out):
    umax = 2.5 * ee.v0
    fig, axs = plt.subplots(len(times), 1, figsize=(8, 2.0 * len(times)), sharex=True)
    for ax, ts in zip(axs, times):
        p = pfiles[int(np.argmin(np.abs(ptimes - ts)))]
        tp, H, xe, ue = phase_hist(p, L, x0, umax, nx=160, nu=90, sm=(1.5, 1.5))
        xc, uc = 0.5 * (xe[1:] + xe[:-1]), 0.5 * (ue[1:] + ue[:-1])
        lvl = 0.12 * np.percentile(H[H > 0], 90)
        lab, _ = ndimage.label(H.T < lvl)
        j0 = int(np.argmin(np.abs(uc)))
        keep = np.setdiff1d(np.unique(lab[j0 - 1 : j0 + 2]), [0])
        edge = np.union1d(lab[0], lab[-1])
        gap = np.isin(lab, np.setdiff1d(keep, edge))
        ax.contourf(xc, uc, gap.astype(float), levels=[0.5, 1.5], colors="none", hatches=["////"])
        ax.contour(xc, uc, H.T, levels=[lvl], colors="k", linewidths=0.8)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_ylabel(r"$u_x$", fontsize=8)
        ax.text(1.01, 0.5, f"t = {tp:.0f}", transform=ax.transAxes, fontsize=8, va="center")
        ax.set_ylim(-umax, umax)
    axs[-1].set_xlabel("$x$")
    axs[0].set_title("Chen Fig. 7.13 from the simulation: contour of $f$; hatched = the initially empty gap "
                     "near $u_x=0$ (time increases downward)", fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "fig7_13.png", dpi=150)
    plt.close(fig)


def fig_f(ee, pfiles, ptimes, snaps, out):
    umax = 3 * ee.v0
    edges = np.linspace(-umax, umax, 121)
    uc = 0.5 * (edges[1:] + edges[:-1])
    fig, ax = plt.subplots(figsize=(6.5, 4))
    for lab, ts in snaps.items():
        p = pfiles[int(np.argmin(np.abs(ptimes - ts)))]
        tp, X, U, W = read_particles(p)
        h, _ = np.histogram(U, bins=edges, weights=W, density=True)
        ax.plot(uc, h, lw=1.2, label=f"{lab}, t = {tp:.0f}")
    ax.axvline(0, color="C2", lw=1, ls="--")
    ax.text(0.004, ax.get_ylim()[1] * 0.55,
            "$v_\\phi = 0$ (Re ω = 0):\nthe wave sits at the\nminimum of $f_0$,\nwhere Chen requires it", fontsize=7,
            color="C2")
    ax.set_xlabel(r"$u_x$")
    ax.set_ylabel(r"$f(u_x)$")
    ax.set_title("Chen Fig. 7.19 analog: double-humped $f_0$ relaxes to a plateau", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out / "fig7_19.png", dpi=150)
    plt.close(fig)


# ======================================================================= main


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
    ee = ChenEE(th, cfg)
    ext = cfg["grid.extent"]
    x0, L = float(ext[0]), float(ext[1]) - float(ext[0])

    t, Ek, Ex, xg = modes(ffiles, "fE1")
    _, N1, _, _ = modes(ffiles, "fN_1")
    _, N3, _, _ = modes(ffiles, "fN_3")
    m = np.arange(Ek.shape[1])
    k = 2 * np.pi * m / L
    band = m[(m > 0) & (ee.y(k) < 1)]
    win = (t >= t1) & (t <= t2)
    late = (t >= 0.5 * (t1 + t2)) & (t <= t2)

    rows = []
    for mm in band:
        g, ge = linfit(t[win], np.log(np.abs(Ek[win, mm])))
        wr, wre = linfit(t[win], -np.unwrap(np.angle(Ek[win, mm])))
        a13, s13 = circ(N1[late, mm] * np.conj(N3[late, mm]))
        a1E, s1E = circ(N1[late, mm] * np.conj(Ek[late, mm]))
        a3E, s3E = circ(N3[late, mm] * np.conj(Ek[late, mm]))
        rows.append(dict(m=mm, k=k[mm], y=ee.y(k[mm]), g=g, ge=ge, wr=wr, wre=wre,
                         a13=a13, s13=s13, a1E=a1E, s1E=s1E, a3E=a3E, s3E=s3E,
                         amp1=np.median(np.abs(N1[late, mm]) / ee.nb / np.abs(Ek[late, mm])),
                         amp3=np.median(np.abs(N3[late, mm]) / ee.nb / np.abs(Ek[late, mm]))))
    M = {key: np.array([r[key] for r in rows]) for key in rows[0]}

    W = (np.abs(Ek[:, band]) ** 2).sum(axis=1)
    first = t <= t2 + 3.0 / th.gamma_max
    i_sat = int(np.argmax(np.where(first, W, -1)))
    m_dom = band[int(np.argmax(np.abs(Ek[i_sat, band])))]
    E_sat = np.abs(Ek[i_sat, m_dom])
    wB = np.sqrt(k[m_dom] * E_sat / (ee.meff * ee.rl0))

    # ------------------------------------------------------------- report
    print(th.summary())
    print(f"omega_p (all electrons, eff) = {ee.wp:.5f};  y = k v0/omega_p;  y_cut = 1 -> k = {ee.wp/ee.v0:.4f}")
    print(f"theory: gamma_max/omega_p = 1/(2 sqrt2) = {1/(2*np.sqrt(2)):.4f} at y = sqrt(3/8) = {np.sqrt(3/8):.4f}")
    print(f"Chen ion-e (Buneman): max Im x from Eq. 6.30 roots = {buneman_growth(np.linspace(0.5,1.2,300)).max():.4f}"
          f";  Eq. 6.35 (m/M)^(1/3) = {MU**(1/3):.4f}")
    print(f"linear window t=[{t1:.0f},{t2:.0f}], eigenvector average t=[{0.5*(t1+t2):.0f},{t2:.0f}]")
    hdr = (f"{'m':>3} {'y':>6} {'g_meas/wp':>9} {'g_th/wp':>8} {'ratio':>6} {'Re x':>7} {'(y)':>6} "
           f"{'arg12':>6} {'th':>5} {'arg1E':>6} {'th':>5} {'arg2E':>6} {'th':>5} {'|n/E|':>6} {'th':>6}")
    print(hdr)
    for r in rows:
        kk = r["k"]
        print(f"{r['m']:3d} {r['y']:6.3f} {r['g']/ee.wp:9.4f} {ee.gamma(kk)/ee.wp:8.4f} "
              f"{r['g']/ee.gamma(kk):6.2f} {r['wr']/ee.wp:7.3f} {r['y']:6.3f} "
              f"{r['a13']:6.0f} {wrap(4*np.degrees(ee.alpha(kk))):5.0f} "
              f"{r['a1E']:6.0f} {np.degrees(np.angle(ee.dn_over_E(kk,1))):5.0f} "
              f"{r['a3E']:6.0f} {np.degrees(np.angle(ee.dn_over_E(kk,-1))):5.0f} "
              f"{0.5*(r['amp1']+r['amp3']):6.2f} {abs(ee.dn_over_E(kk,1)):6.2f}")
    core = (M["y"] > 0.3) & (M["y"] < 0.95)
    print(f"core band (0.3<y<0.95): gamma ratio mean {np.mean(M['g'][core]/ee.gamma(M['k'][core])):.2f} "
          f"+- {np.std(M['g'][core]/ee.gamma(M['k'][core])):.2f};  |Re x| max {np.max(np.abs(M['wr'][core]))/ee.wp:.3f}")
    print(f"first saturation t = {t[i_sat]:.0f}: dominant m = {m_dom} (y = {ee.y(k[m_dom]):.3f}), |E_m| = {E_sat:.4f}, "
          f"bounce omega_B = {wB:.4f}, omega_B/gamma(k) = {wB/ee.gamma(k[m_dom]):.2f}")
    with open(a.out / "chen_ee_comparison.csv", "w") as fh:
        keys = list(rows[0])
        fh.write(",".join(keys + ["gamma_th", "arg12_th", "arg1E_th", "arg2E_th", "n_over_E_th"]) + "\n")
        for r in rows:
            kk = r["k"]
            extra = [ee.gamma(kk), wrap(4 * np.degrees(ee.alpha(kk))), np.degrees(np.angle(ee.dn_over_E(kk, 1))),
                     np.degrees(np.angle(ee.dn_over_E(kk, -1))), abs(ee.dn_over_E(kk, 1))]
            fh.write(",".join(f"{r[q]:.6g}" for q in keys) + "," + ",".join(f"{v:.6g}" for v in extra) + "\n")

    # ------------------------------------------------------------- figures
    pfiles = sorted((run / "particles").glob("particles.*.bp"))
    ptimes = file_times(pfiles)
    ftimes = t
    mlp = int(2 * band.max())
    fig_F(ee, a.out)
    fig_roots(ee, M, a.out, t1, t2)
    fig_growth(ee, t, Ek, k, band, i_sat, t1, t2, a.out)
    fig_eigen(ee, M, a.out, 0.5 * (t1 + t2), t2)
    fig_trapping(ee, ffiles, ftimes, pfiles, ptimes, t[i_sat], L, x0, mlp, a.out)
    fig_water_bags(ee, pfiles, ptimes, [t2 - 40, t2, t[i_sat], t[i_sat] + 80], L, x0, a.out)
    fig_f(ee, pfiles, ptimes, {"$f_0$": 0.0, "linear": t2, "saturation": t[i_sat], "late": ptimes.max()}, a.out)
    print(f"wrote figures + chen_ee_comparison.csv to {a.out}")


if __name__ == "__main__":
    main()
