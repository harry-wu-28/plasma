#!/usr/bin/env python3
"""Two-stream run analysis: measured growth rate gamma(k) vs cold-beam theory,
mode histories, energy conservation (numerical heating), x-t and phase space.

Usage (on Discovery, the analysis env is the one with adios2):
    conda run -n analysis python twostream/analysis/twostream_analysis.py \
        /dartfs-hpc/scratch/f007hd2/twostream/twostream_baseline \
        [--fit-window T1 T2] [--out twostream/runs/baseline/plots]

Compare several runs (e.g. the numerics scan) on one gamma(k) plot:
    ... twostream_analysis.py RUN_A RUN_B RUN_C --out twostream/runs/scan/plots

Everything physical is read from the run's own config attributes, so the
script works unchanged for every scan variant.

Conventions (verified 2026-11-16 against an Entity v1.3.3 CPU test run):
- setup.densities[i] is the TOTAL density of species pair (2i+1, 2i+2), in n0;
  arch::InjectUniformMaxwellians splits it evenly, so each electron beam has
  n_b = densities[0]/2 = 0.25 n0 (fN_1 mean = 0.25 confirmed).
- omega_p for density n (n0 units, unit charge/mass) = sqrt(n)/skindepth0.
- For longitudinal oscillations of a relativistic beam the effective mass is
  gamma0^3 m, so omega_b,eff = omega_b / gamma0^1.5 (0.75% at u = 0.1).
- Stats: T00 is particle energy density (incl. rest mass) in n0 m c^2; the
  E^2/B^2 columns are in B0 units, so field energy density in the same units is
  (sigma0/2)(E^2 + B^2), sigma0 = (skindepth0/larmor0)^2. Checked: dT00 matches
  -(sigma0/2) dE1^2 through the linear phase.
- 1D field output: fE1 etc. are 1D arrays of length nx at cell centers X1.
"""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from adios2 import FileReader

# --------------------------------------------------------------------- reading


def parse_attr(raw):
    s = str(raw).strip()
    if s.startswith("{"):
        inner = s.strip("{} ").strip()
        return [] if not inner else [parse_attr(t) for t in inner.split(",")]
    if s.startswith('"'):
        return s.strip('"')
    try:
        return float(s)
    except ValueError:
        return s


def field_files(run_dir):
    files = sorted((Path(run_dir) / "fields").glob("fields.*.bp"))
    if not files:
        raise FileNotFoundError(f"no fields/fields.*.bp under {run_dir}")
    return files


def read_config(path):
    with FileReader(str(path)) as f:
        return {k: parse_attr(v.get("Value", "")) for k, v in f.available_attributes().items()}


def read_field_series(files, name="fE1"):
    times, data, x = [], [], None
    for p in files:
        with FileReader(str(p)) as f:
            times.append(float(f.read("Time")))
            data.append(np.asarray(f.read(name), dtype=np.float64))
            if x is None:
                x = np.asarray(f.read("X1"), dtype=np.float64)
    order = np.argsort(times)
    return np.asarray(times)[order], np.asarray(data)[order], x


def read_stats(run_dir):
    run_dir = Path(run_dir)
    hits = sorted(run_dir.glob("*_stats.csv"))
    if not hits:
        return None
    with open(hits[0]) as fh:
        rows = [[c.strip() for c in r] for r in csv.reader(fh)]
    header = [h for h in rows[0] if h]
    cols = {h: [] for h in header}
    for r in rows[1:]:
        for h, v in zip(header, r):
            cols[h].append(float(v))
    return {h: np.asarray(v) for h, v in cols.items()}


# ---------------------------------------------------------------------- theory


class Theory:
    """Cold, symmetric, counter-streaming electron beams on an immobile background."""

    def __init__(self, cfg):
        d0 = float(cfg["scales.skindepth0"])
        rl0 = float(cfg["scales.larmor0"])
        dens = cfg.get("setup.densities", [0.5, 0.5])
        drifts = cfg.get("setup.drifts_in_x", [0.1, 0.0, -0.1, 0.0])
        temps = cfg.get("setup.temperatures", [0.0] * 4)
        if abs(abs(drifts[0]) - abs(drifts[2])) > 1e-12 or abs(dens[0] - dens[1]) > 1e-12:
            print("WARNING: beams are not symmetric; symmetric theory is approximate")
        self.u0 = abs(float(drifts[0]))
        self.gamma0 = np.sqrt(1.0 + self.u0**2)
        self.v0 = self.u0 / self.gamma0
        self.n_beam = float(dens[0]) / 2.0
        self.omega_b_nr = np.sqrt(self.n_beam) / d0
        self.omega_b = self.omega_b_nr / self.gamma0**1.5
        self.gamma_max = self.omega_b / 2.0
        self.k_max = np.sqrt(3.0) / 2.0 * self.omega_b / self.v0
        self.k_cut = np.sqrt(2.0) * self.omega_b / self.v0
        self.sigma0 = (d0 / rl0) ** 2
        self.vth = np.sqrt(float(temps[0]))
        self.lambda_D = self.vth / (np.sqrt(2 * self.n_beam) / d0)

    def growth(self, k):
        """Imag. part of omega from omega^2 = k^2v^2 + wb^2 - wb sqrt(wb^2 + 4k^2v^2)."""
        kv = np.asarray(k) * self.v0
        wb = self.omega_b
        w2 = kv**2 + wb**2 - wb * np.sqrt(wb**2 + 4 * kv**2)
        return np.sqrt(np.clip(-w2, 0, None))

    def summary(self):
        return (
            f"u0={self.u0:g}  v0={self.v0:.4f}c  gamma0={self.gamma0:.4f}  n_beam={self.n_beam:g} n0\n"
            f"omega_b={self.omega_b:.5f} (nonrel {self.omega_b_nr:.5f})  "
            f"gamma_max=omega_b/2={self.gamma_max:.5f}\n"
            f"k_max={self.k_max:.4f} (lambda={2*np.pi/self.k_max:.2f})  k_cut={self.k_cut:.4f}  "
            f"lambda_D={self.lambda_D:.4f}  sigma0={self.sigma0:g}"
        )


# -------------------------------------------------------------------- analysis


def mode_amplitudes(E):
    """|E_m(t)| for m = 0..nx/2 (real FFT, amplitude normalization)."""
    nx = E.shape[1]
    return np.abs(np.fft.rfft(E, axis=1)) * 2.0 / nx


def auto_window(t, amp, m_band, th):
    """Linear-phase window from the unstable-band field energy W(t) = sum |E_m|^2.

    PIC starts from shot noise: E jumps to a thermal-fluctuation level within a
    few 1/omega_p, then the unstable band grows until trapping saturates it.
    Take the stretch where d ln W/dt (smoothed over ~1/gamma_max) stays above half
    its maximum, ignoring the first 10/omega_pe start-up transient and
    everything after W first reaches its peak. Always check *_modes.png and
    override with --fit-window if this picks something unphysical.
    """
    W = (amp[:, m_band] ** 2).sum(axis=1)
    lnW = np.log(W)
    dt = np.median(np.diff(t))
    nsm = max(1, int(round(1.0 / th.gamma_max / dt)))
    lnW_s = np.convolve(lnW, np.ones(nsm) / nsm, mode="same")
    slope = np.gradient(lnW_s, t)
    i_peak = int(np.argmax(W))
    omega_pe = th.omega_b_nr * np.sqrt(2.0)
    ok = (t > 10.0 / omega_pe) & (np.arange(len(t)) <= i_peak)
    ok[: nsm // 2] = False
    if ok.sum() < 3:
        ok = np.arange(len(t)) <= i_peak
    s = np.where(ok, slope, -np.inf)
    i_max = int(np.argmax(s))
    i1 = i2 = i_max
    while i1 > 0 and ok[i1 - 1] and s[i1 - 1] > 0.5 * s[i_max]:
        i1 -= 1
    while i2 < len(t) - 1 and ok[i2 + 1] and s[i2 + 1] > 0.5 * s[i_max]:
        i2 += 1
    sub = amp[i1 : i2 + 1, m_band]
    m_dom = m_band[np.argmax(sub[-1] / np.maximum(sub[0], 1e-300))]
    return t[i1], t[i2], m_dom


def fit_growth(t, amp, m, t1, t2):
    sel = (t >= t1) & (t <= t2) & (amp[:, m] > 0)
    if sel.sum() < 3:
        return np.nan, np.nan
    p, cov = np.polyfit(t[sel], np.log(amp[sel, m]), 1, cov=True)
    return p[0], np.sqrt(cov[0, 0])


def analyse(run_dir, fit_window=None):
    files = field_files(run_dir)
    cfg = read_config(files[0])
    th = Theory(cfg)
    t, E, x = read_field_series(files, "fE1")
    L = float(cfg["grid.extent"][1]) - float(cfg["grid.extent"][0]) if isinstance(
        cfg.get("grid.extent"), list) and len(cfg["grid.extent"]) == 2 else x[-1] - x[0] + (x[1] - x[0])
    nx = E.shape[1]
    amp = mode_amplitudes(E)
    m = np.arange(amp.shape[1])
    k = 2 * np.pi * m / L
    m_band = m[(m > 0) & (k < th.k_cut)]
    if fit_window:
        t1, t2 = fit_window
        m_dom = m_band[np.argmax(amp[:, m_band].max(axis=0))]
    else:
        t1, t2, m_dom = auto_window(t, amp, m_band, th)
    m_fit = m[(m > 0) & (k < 1.5 * th.k_cut)]
    g = np.array([fit_growth(t, amp, mm, t1, t2) for mm in m_fit])
    return dict(run=Path(run_dir), name=cfg.get("simulation.name", Path(run_dir).name), cfg=cfg,
                th=th, t=t, E=E, x=x, L=L, nx=nx, amp=amp, k=k, m_dom=m_dom, t1=t1, t2=t2,
                m_fit=m_fit, k_fit=k[m_fit], g=g[:, 0], g_err=g[:, 1],
                stats=read_stats(run_dir))


def report(r):
    th = r["th"]
    print(f"\n=== {r['name']}  ({r['run']})")
    print(f"nx={r['nx']}  L={r['L']:g}  dx={r['L']/r['nx']:.4g}  lambda_D/dx={th.lambda_D/(r['L']/r['nx']):.2f}"
          f"  ppc0={r['cfg'].get('particles.ppc0')}  filters={r['cfg'].get('algorithms.current_filters')}")
    print(th.summary())
    print(f"fit window t = [{r['t1']:.1f}, {r['t2']:.1f}]  (dominant mode m={r['m_dom']}, "
          f"k={r['k'][r['m_dom']]:.4f})")
    print(f"{'m':>4} {'k':>8} {'gamma_meas':>11} {'+-':>8} {'gamma_th':>9} {'ratio':>6}")
    for mm, kk, gg, ee in zip(r["m_fit"], r["k_fit"], r["g"], r["g_err"]):
        gt = th.growth(kk)
        ratio = gg / gt if gt > 0 else np.nan
        print(f"{mm:4d} {kk:8.4f} {gg:11.5f} {ee:8.5f} {gt:9.5f} {ratio:6.2f}")
    i = int(np.argmax(np.nan_to_num(r["g"], nan=-1)))
    print(f"max measured gamma = {r['g'][i]:.5f} at k = {r['k_fit'][i]:.4f}   "
          f"(theory {th.gamma_max:.5f} at k = {th.k_max:.4f})")
    s = r["stats"]
    if s is not None and "T00" in s:
        etot = total_energy(s, th)
        rel = (etot - etot[0]) / etot[0]
        print(f"energy: max |dE_tot/E_tot| = {np.nanmax(np.abs(rel)):.3e}, final = {rel[-1]:+.3e}")


def total_energy(s, th):
    fe = sum(s[c] for c in s if c.endswith("^2") or c.endswith("²"))
    return s["T00"] + 0.5 * th.sigma0 * fe


# ---------------------------------------------------------------------- plots


def plot_run(r, out):
    out.mkdir(parents=True, exist_ok=True)
    th, t, amp, k = r["th"], r["t"], r["amp"], r["k"]
    tag = r["name"]

    # mode histories
    fig, ax = plt.subplots(figsize=(6, 4))
    order = np.argsort(-np.nan_to_num(r["g"], nan=-1))[:6]
    for j in order:
        mm = r["m_fit"][j]
        (ln,) = ax.semilogy(t, amp[:, mm], lw=1, label=f"m={mm}, k={k[mm]:.3f}")
        sel = (t >= r["t1"]) & (t <= r["t2"])
        if np.isfinite(r["g"][j]) and sel.any():
            a0 = np.exp(np.polyfit(t[sel], np.log(amp[sel, mm]), 1)[1])
            ax.semilogy(t[sel], a0 * np.exp(r["g"][j] * t[sel]), "--", color=ln.get_color(), lw=1)
    ax.axvspan(r["t1"], r["t2"], color="0.9", zorder=0)
    ax.set_xlabel(r"$t$ [code units]")
    ax.set_ylabel(r"$|\hat E_{x}(k,t)|$")
    ax.set_title(f"{tag}: fastest modes (dashed = fit)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out / f"{tag}_modes.png", dpi=150)
    plt.close(fig)

    # x-t
    fig, ax = plt.subplots(figsize=(6, 4))
    lim = np.nanmax(np.abs(r["E"]))
    pc = ax.pcolormesh(r["x"], t, r["E"], cmap="RdBu_r", vmin=-lim, vmax=lim, shading="auto")
    fig.colorbar(pc, ax=ax, label=r"$E_x$")
    ax.set_xlabel(r"$x$")
    ax.set_ylabel(r"$t$")
    ax.set_title(f"{tag}: $E_x(x,t)$")
    fig.tight_layout()
    fig.savefig(out / f"{tag}_Ex_xt.png", dpi=150)
    plt.close(fig)

    # energy
    s = r["stats"]
    if s is not None and "T00" in s:
        fig, axs = plt.subplots(2, 1, figsize=(6, 5.5), sharex=True)
        fe = 0.5 * th.sigma0 * sum(s[c] for c in s if c.startswith("E"))
        axs[0].semilogy(s["time"], fe, label="field energy (E)")
        tt = s["time"]
        i0 = np.searchsorted(tt, r["t1"])
        if i0 < len(tt):
            axs[0].semilogy(tt, fe[i0] * np.exp(2 * th.gamma_max * (tt - tt[i0])), "k--", lw=0.8,
                            label=r"$\propto e^{2\gamma_{\max} t}$ (theory)")
        axs[0].set_ylim(fe[fe > 0].min() / 3, fe.max() * 3)
        axs[0].set_ylabel(r"$\langle E^2\rangle\sigma_0/2$ [$n_0 m c^2$]")
        axs[0].legend(fontsize=8)
        etot = total_energy(s, th)
        axs[1].plot(tt, (etot - etot[0]) / etot[0], label="total")
        kin = s["T00"]
        axs[1].plot(tt, (kin - kin[0]) / etot[0], label="particles", lw=0.8)
        axs[1].set_ylabel(r"$\Delta\mathcal{E}/\mathcal{E}_0$")
        axs[1].set_xlabel(r"$t$")
        axs[1].legend(fontsize=8)
        fig.suptitle(f"{tag}: energy history (heating = drift in total)")
        fig.tight_layout()
        fig.savefig(out / f"{tag}_energy.png", dpi=150)
        plt.close(fig)

    # phase space
    pfiles = sorted((r["run"] / "particles").glob("particles.*.bp"))
    if pfiles:
        picks = [pfiles[0], pfiles[np.argmin(np.abs(np.arange(len(pfiles)) - len(pfiles) * r["t2"] / t[-1]))],
                 pfiles[-1]]
        fig, axs = plt.subplots(1, 3, figsize=(11, 3.4), sharey=True)
        for ax, p in zip(axs, picks):
            with FileReader(str(p)) as f:
                time = float(f.read("Time"))
                for s_, c in ((1, "C0"), (3, "C3")):
                    ax.plot(f.read(f"pX1_{s_}"), f.read(f"pU1_{s_}"), ",", color=c, alpha=0.5)
            ax.set_title(f"t = {time:.0f}")
            ax.set_xlabel(r"$x$")
        axs[0].set_ylabel(r"$u_x = \gamma v_x / c$")
        fig.suptitle(f"{tag}: phase space (blue +x beam, red -x beam)")
        fig.tight_layout()
        fig.savefig(out / f"{tag}_phase.png", dpi=150)
        plt.close(fig)


def plot_gamma_k(runs, out, fname="gamma_k.png"):
    out.mkdir(parents=True, exist_ok=True)
    th = runs[0]["th"]
    fig, ax = plt.subplots(figsize=(6, 4))
    kk = np.linspace(0, 1.3 * th.k_cut, 400)
    ax.plot(kk * th.v0 / th.omega_b, th.growth(kk) / th.omega_b, "k-", label="cold theory")
    for r in runs:
        ax.errorbar(r["k_fit"] * r["th"].v0 / r["th"].omega_b, r["g"] / r["th"].omega_b,
                    yerr=r["g_err"] / r["th"].omega_b, fmt="o", ms=3, capsize=2, label=r["name"])
    ax.axhline(0, color="0.6", lw=0.5)
    ax.set_xlabel(r"$k v_0 / \omega_b$")
    ax.set_ylabel(r"$\gamma / \omega_b$")
    ax.set_ylim(-0.1, 0.65)
    ax.legend(fontsize=7)
    ax.set_title("Two-stream growth rate")
    fig.tight_layout()
    fig.savefig(out / fname, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", help="run dir(s): <WORK_DIR>/<simulation.name>")
    ap.add_argument("--fit-window", nargs=2, type=float, metavar=("T1", "T2"))
    ap.add_argument("--out", type=Path, default=None, help="plot dir (default: <run>/plots)")
    a = ap.parse_args()
    results = []
    for rd in a.runs:
        r = analyse(rd, a.fit_window)
        report(r)
        plot_run(r, a.out or Path(rd) / "plots")
        results.append(r)
        with open((a.out or Path(rd) / "plots") / f"{r['name']}_gamma_k.csv", "w") as fh:
            fh.write("m,k,gamma_meas,gamma_err,gamma_theory\n")
            for mm, kk, gg, ee in zip(r["m_fit"], r["k_fit"], r["g"], r["g_err"]):
                fh.write(f"{mm},{kk:.6g},{gg:.6g},{ee:.3g},{r['th'].growth(kk):.6g}\n")
    plot_gamma_k(results, a.out or Path(a.runs[0]) / "plots")


if __name__ == "__main__":
    main()
