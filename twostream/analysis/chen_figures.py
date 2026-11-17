#!/usr/bin/env python3
"""Chen's two-stream story (F. F. Chen, Introduction to Plasma Physics and Controlled
Fusion: fluid two-stream instability + the kinetic trapping/plateau picture), redrawn
with this run's parameters and checked against its data.

  chen1_dispersion_F.png  graphical dispersion relation F(omega) = 1: Chen's electron
                          stream through ions, and the symmetric beams simulated here
  chen2_roots.png         Re/Im omega(k) from the exact quartic, simulated gamma(k) on top
  chen3_timeline.png      field energy: noise -> linear growth -> trapping saturation;
                          energy drained from the beams
  chen4_bunching.png      linear phase: beam density bunching and E_x; Poisson check
  chen5_trapping.png      phase-space density + separatrix of the measured potential
  chen6_plateau.png       f(u_x, t): two beams -> flat plateau

Usage:
    conda run -n analysis python twostream/analysis/chen_figures.py RUN_DIR --out PLOT_DIR
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
import twostream_analysis as ta  # noqa: E402


def lowpass(a, mmax):
    A = np.fft.rfft(a, axis=-1)
    A[..., mmax + 1 :] = 0
    return np.fft.irfft(A, n=a.shape[-1], axis=-1)


def ddx(a, L):
    k = 2 * np.pi * np.fft.rfftfreq(a.shape[-1], d=L / a.shape[-1])
    return np.fft.irfft(1j * k * np.fft.rfft(a, axis=-1), n=a.shape[-1], axis=-1)


def nearest(files, times, t):
    return files[int(np.argmin(np.abs(np.asarray(times) - t)))]


def file_times(files):
    out = []
    for p in files:
        with FileReader(str(p)) as f:
            out.append(float(f.read("Time")))
    return np.asarray(out)


def read_fields(path, names):
    with FileReader(str(path)) as f:
        return float(f.read("Time")), {n: np.asarray(f.read(n), dtype=np.float64) for n in names}


def read_particles(path):
    with FileReader(str(path)) as f:
        t = float(f.read("Time"))
        d = {s: (np.asarray(f.read(f"pX1_{s}")), np.asarray(f.read(f"pU1_{s}")),
                 np.asarray(f.read(f"pW_{s}"))) for s in (1, 3)}
    return t, d


def masked(F, top):
    F = np.array(F)
    F[F > 1.5 * top] = np.nan
    return F


# --------------------------------------------------------------------- 1: F(omega)


def fig_dispersion(th, out):
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))

    mM = 1 / 1836.15
    Kc = (1 + mM ** (1 / 3)) ** 1.5
    x = np.linspace(-1.0, 3.2, 8001)
    ax = axs[0]
    for K, c in ((0.8, "C3"), (2.2, "C0")):
        F = mM / x**2 + 1 / (x - K) ** 2
        ax.plot(x, masked(F, 4), color=c, label=fr"$kv_0/\omega_p={K}$ ({'unstable' if K < Kc else 'stable'})")
    ax.axhline(1, color="k", lw=0.8)
    ax.set_ylim(0, 4)
    ax.set_xlabel(r"$\omega/\omega_p$")
    ax.set_ylabel(r"$F(\omega)$")
    ax.set_title("Chen: electron stream through cold ions\n"
                 r"$F=\omega_p^2\left[\frac{m/M}{\omega^2}+\frac{1}{(\omega-kv_0)^2}\right]=1$",
                 fontsize=9)
    ax.text(0.02, 0.97, f"unstable if $kv_0/\\omega_p<{Kc:.3f}$\n(min of $F$ between poles > 1)",
            transform=ax.transAxes, va="top", fontsize=8)
    ax.legend(fontsize=7, loc="upper right")

    x = np.linspace(-3.2, 3.2, 8001)
    ax = axs[1]
    for K, c, lab in ((np.sqrt(3) / 2, "C3", r"$\sqrt{3}/2$ (fastest growth)"),
                      (np.sqrt(2), "C1", r"$\sqrt{2}$ (marginal)"),
                      (2.2, "C0", "2.2 (stable)")):
        F = 1 / (x - K) ** 2 + 1 / (x + K) ** 2
        ax.plot(x, masked(F, 4), color=c, label=fr"$kv_0/\omega_b=${lab}")
    ax.axhline(1, color="k", lw=0.8)
    ax.set_ylim(0, 4)
    ax.set_xlabel(r"$\omega/\omega_b$")
    ax.set_title("This run: symmetric counter-streaming e$^-$ beams\n"
                 r"$F=\omega_b^2\left[\frac{1}{(\omega-kv_0)^2}+\frac{1}{(\omega+kv_0)^2}\right]=1$",
                 fontsize=9)
    ax.text(0.02, 0.97, f"$F(0)=2\\omega_b^2/k^2v_0^2$ > 1  ⇔  $k<{th.k_cut:.3f}$\n"
                        f"($\\omega_b$={th.omega_b:.4f}, $v_0$={th.v0:.4f})",
            transform=ax.transAxes, va="top", fontsize=8)
    ax.legend(fontsize=7, loc="upper right")
    fig.tight_layout()
    fig.savefig(out / "chen1_dispersion_F.png", dpi=150)
    plt.close(fig)


# ----------------------------------------------------------------- 2: roots vs k


def fig_roots(r, out):
    th = r["th"]
    K = np.linspace(1e-3, 3.0, 1200)
    s = np.sqrt(1 + 4 * K**2)
    wp2, wm2 = K**2 + 1 + s, K**2 + 1 - s
    fig, axs = plt.subplots(2, 1, figsize=(6.2, 6), sharex=True)
    ax = axs[0]
    ax.plot(K, np.sqrt(wp2), "k-", label="fast branch (beam-plasma osc.)")
    slow = np.where(wm2 >= 0, np.sqrt(np.clip(wm2, 0, None)), np.nan)
    ax.plot(K, slow, "k--", label="slow branch (real only for $kv_0>\\sqrt{2}\\omega_b$)")
    ax.plot(K, K, color="0.6", lw=0.6, label=r"$\omega=kv_0$ (beam Doppler line)")
    ax.set_ylabel(r"Re $\omega/\omega_b$")
    ax.legend(fontsize=7)
    ax = axs[1]
    ax.plot(K, np.sqrt(np.clip(-wm2, 0, None)), "k-", label="cold fluid theory (Re $\\omega$ = 0)")
    Ks = r["k_fit"] * th.v0 / th.omega_b
    ax.errorbar(Ks, r["g"] / th.omega_b, yerr=r["g_err"] / th.omega_b, fmt="o", ms=3, capsize=2,
                color="C3", label=f"simulation, fit t=[{r['t1']:.0f}, {r['t2']:.0f}]")
    ax.axvline(np.sqrt(2), color="C1", lw=0.6)
    ax.axhline(0, color="0.6", lw=0.5)
    ax.set_ylim(-0.1, 0.65)
    ax.set_xlabel(r"$k v_0/\omega_b$")
    ax.set_ylabel(r"Im $\omega/\omega_b$")
    ax.legend(fontsize=7)
    fig.suptitle("Roots of $F(\\omega)=1$: two real roots merge into a growing pair", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "chen2_roots.png", dpi=150)
    plt.close(fig)


# ----------------------------------------------------------------- 3: timeline


def fig_timeline(r, snaps, out):
    th, s = r["th"], r["stats"]
    t = s["time"]
    fe = 0.5 * th.sigma0 * s["E1^2"]
    fig, axs = plt.subplots(2, 1, figsize=(6.5, 5.5), sharex=True)
    ax = axs[0]
    ax.semilogy(t, fe, "k-", lw=1, label=r"field energy $\sigma_0\langle E_x^2\rangle/2$")
    i0 = int(np.argmin(np.abs(t - r["t1"])))
    tt = t[(t >= r["t1"] - 20) & (t <= r["t2"] + 30)]
    ax.semilogy(tt, fe[i0] * np.exp(2 * th.gamma_max * (tt - t[i0])), "C3--", lw=1,
                label=r"$\propto e^{2\gamma_{max}t}$, $\gamma_{max}=\omega_b/2$")
    for lab, ts in snaps.items():
        ax.axvline(ts, color="0.5", lw=0.6, ls=":")
        ax.text(ts, fe.max() * 3, lab, rotation=90, fontsize=7,
                ha="right", va="top")
    ax.set_ylim(fe[fe > 0].min() / 3, fe.max() * 5)
    ax.set_ylabel("energy density [$n_0 mc^2$]")
    ax.legend(fontsize=7, loc="lower right")
    ax = axs[1]
    dk = s["T00"] - s["T00"][0]
    ax.plot(t, fe - fe[0], "C0", label="field energy gained")
    ax.plot(t, -dk, "C3", label="particle energy lost ($-\\Delta T^{00}$)")
    ax.plot(t, fe - fe[0] + dk, "k", lw=0.8, label="sum (numerical heating)")
    ax.set_xlabel("$t$")
    ax.set_ylabel(r"$\Delta$ energy density")
    ax.legend(fontsize=7)
    fig.suptitle("Free energy of the streams feeds the wave until trapping saturates it", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "chen3_timeline.png", dpi=150)
    plt.close(fig)


# ------------------------------------------------------------ 4: linear bunching


def fig_bunching(r, ffiles, ftimes, t_lin, mlp, out):
    th, L = r["th"], r["L"]
    t, d = read_fields(nearest(ffiles, ftimes, t_lin), ["fN_1", "fN_3", "fE1"])
    x = r["x"]
    n1, n3, E = (lowpass(d[k], mlp) for k in ("fN_1", "fN_3", "fE1"))
    rho = lowpass(2 * th.n_beam - d["fN_1"] - d["fN_3"], mlp)
    dEdx = ddx(E, L)
    C = float(np.dot(dEdx, rho) / np.dot(rho, rho))

    fig, axs = plt.subplots(2, 1, figsize=(8, 5.5), sharex=True)
    ax = axs[0]
    ax.plot(x, (n1 - n1.mean()) / th.n_beam, "C0", lw=1, label=r"$\delta n/n_b$, +x beam")
    ax.plot(x, (n3 - n3.mean()) / th.n_beam, "C3", lw=1, label=r"$\delta n/n_b$, $-$x beam")
    ax.set_ylabel(r"$\delta n / n_b$")
    ax2 = ax.twinx()
    ax2.plot(x, E, "k", lw=0.8, alpha=0.6)
    ax2.set_ylabel("$E_x$ (black)")
    ax.legend(fontsize=7, loc="upper right")
    ax.set_title(f"Linear phase, t = {t:.0f}: both beams bunch, E_x grows from the charge "
                 f"(modes m ≤ {mlp})", fontsize=9)
    ax = axs[1]
    ax.plot(x, dEdx, "k", lw=1, label=r"$\partial_x E_x$")
    ax.plot(x, C * rho, "C2--", lw=1, label=fr"$C\,\rho$, fitted $C$ = {C:.3f}")
    ax.set_xlabel("$x$")
    ax.set_ylabel("Poisson check")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out / "chen4_bunching.png", dpi=150)
    plt.close(fig)
    return C


# ------------------------------------------------------------- 5: trapping


def fig_trapping(r, ffiles, ftimes, pfiles, ptimes, snaps, C, mlp, out):
    th, L, x = r["th"], r["L"], r["x"]
    d0 = float(r["cfg"]["scales.skindepth0"])
    force = 1.0 / (d0**2 * C)
    umax = 4 * th.u0
    fig, axs = plt.subplots(1, len(snaps), figsize=(3.3 * len(snaps), 3.6), sharey=True)
    for ax, (lab, ts) in zip(axs, snaps.items()):
        tp, P = read_particles(nearest(pfiles, ptimes, ts))
        X = np.concatenate([P[s][0] for s in (1, 3)])
        U = np.concatenate([P[s][1] for s in (1, 3)])
        W = np.concatenate([P[s][2] for s in (1, 3)])
        H, xe, ue = np.histogram2d(X, U, bins=(160, 120), range=((x[0] - (x[1] - x[0]) / 2,
                                    x[0] + L - (x[1] - x[0]) / 2), (-umax, umax)), weights=W)
        ax.pcolormesh(xe, ue, H.T, cmap="magma", shading="auto")
        _, d = read_fields(nearest(ffiles, ftimes, tp), ["fE1"])
        E = lowpass(d["fE1"], mlp)
        phi = -np.cumsum(E) * (L / len(E))
        Upot = -force * phi  # q = -1, m = 1
        vs = np.sqrt(np.clip(2 * (Upot.max() - Upot), 0, None))
        for sgn in (1, -1):
            ax.plot(x, sgn * vs, color="c", lw=0.7)
        ax.set_title(f"{lab}: t = {tp:.0f}", fontsize=9)
        ax.set_xlabel("$x$")
    axs[0].set_ylabel(r"$u_x$")
    fig.suptitle("Phase space (both beams); cyan = separatrix of the measured potential "
                 "(wave frame = lab frame, Re ω = 0)", fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "chen5_trapping.png", dpi=150)
    plt.close(fig)


# ------------------------------------------------------------- 6: plateau


def fig_plateau(r, pfiles, ptimes, snaps, out):
    th = r["th"]
    umax = 4 * th.u0
    edges = np.linspace(-umax, umax, 161)
    uc = 0.5 * (edges[1:] + edges[:-1])
    order = np.argsort(ptimes)
    F = []
    for i in order:
        _, P = read_particles(pfiles[i])
        U = np.concatenate([P[s][1] for s in (1, 3)])
        W = np.concatenate([P[s][2] for s in (1, 3)])
        h, _ = np.histogram(U, bins=edges, weights=W, density=True)
        F.append(h)
    F = np.asarray(F)
    tt = np.asarray(ptimes)[order]

    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    ax = axs[0]
    ax.pcolormesh(uc, tt, np.log10(F + F[F > 0].min()), cmap="viridis", shading="auto")
    ax.set_xlabel(r"$u_x$")
    ax.set_ylabel("$t$")
    ax.set_title(r"$\log_{10} f(u_x, t)$", fontsize=9)
    ax = axs[1]
    for lab, ts in {"t = 0": 0.0, **snaps}.items():
        i = int(np.argmin(np.abs(tt - ts)))
        ax.plot(uc, F[i], lw=1, label=f"{lab} (t={tt[i]:.0f})")
    for sgn in (1, -1):
        ax.axvline(sgn * th.u0, color="0.6", lw=0.5, ls=":")
    ax.set_yscale("log")
    ax.set_ylim(F[F > 0].min(), None)
    ax.set_xlabel(r"$u_x$")
    ax.set_ylabel(r"$f(u_x)$")
    ax.legend(fontsize=7)
    ax.set_title("Two cold beams flatten into a plateau between $\\pm u_0$", fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "chen6_plateau.png", dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fit-window", nargs=2, type=float, metavar=("T1", "T2"))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    r = ta.analyse(a.run, a.fit_window)
    ta.report(r)
    th = r["th"]
    run = Path(a.run)
    ffiles = ta.field_files(run)
    ftimes = file_times(ffiles)
    pfiles = sorted((run / "particles").glob("particles.*.bp"))
    ptimes = file_times(pfiles)
    s = r["stats"]
    t_sat = float(s["time"][int(np.argmax(s["E1^2"]))])
    t_end = float(min(ftimes.max(), ptimes.max()))
    snaps = {"linear": r["t2"], "saturation": t_sat,
             "nonlinear": 0.5 * (t_sat + t_end), "late": t_end}
    mlp = int(2 * th.k_cut * r["L"] / (2 * np.pi)) + 1
    print(f"snapshots: {snaps}  low-pass m <= {mlp}")

    fig_dispersion(th, a.out)
    fig_roots(r, a.out)
    fig_timeline(r, snaps, a.out)
    C = fig_bunching(r, ffiles, ftimes, r["t2"], mlp, a.out)
    d0 = float(r["cfg"]["scales.skindepth0"])
    rl0 = float(r["cfg"]["scales.larmor0"])
    print(f"Poisson: dE/dx = C rho with C = {C:.4f}  (expected larmor0/skindepth0^2 = {rl0/d0**2:.4f})")
    fig_trapping(r, ffiles, ftimes, pfiles, ptimes, snaps, C, mlp, a.out)
    fig_plateau(r, pfiles, ptimes, snaps, a.out)
    print(f"wrote chen1..chen6 to {a.out}")


if __name__ == "__main__":
    main()
