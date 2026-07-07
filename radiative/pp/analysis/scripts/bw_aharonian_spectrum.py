"""Breit-Wheeler validation: simulated pair spectrum vs Aharonian+ 1983.

Recreates the Entity docs two-photon test figure for this repo's pp pgen:
a hard isotropic monoenergetic photon population (setup.epsilon1, the
figure's eps_2) pair-producing on an implicit isotropic monoenergetic
bath (setup.photonEnergy, the figure's eps_1). The secondary e-/e+
spectra (species 4/5) are histogrammed from raw particle momenta (the
built-in spectra are zeroed by the pp zero-weight bug) and compared with
the analytic spectrum of Aharonian, Atoyan & Nagapetyan 1983
(Astrofizika 19, 323) for a monochromatic gamma-ray in an isotropic
monochromatic field, everything in units of m_e c^2:

  dN/dE ∝ 4 eg^2/(E(eg-E)) * ln(4 e E (eg-E)/eg) - 8 e eg
          + 2(2 e eg - 1) eg^2/(E(eg-E))
          - (1 - 1/(e eg)) eg^4/(E^2 (eg-E)^2)

(e = soft energy, eg = hard energy; asymptotic form, accurate for
e*eg >> 1 — here e*eg = 10). The curve is normalized to the simulated
per-species pair count, so the comparison tests the *shape*.

Since IC is off and secondaries never cool, the accumulated spectrum at
any output step has the same shape as the instantaneous production rate.

Usage:
  conda run -n analysis python bw_aharonian_spectrum.py <run_dir> [--step N]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bp_reader import RunReader
import viz_style as vs


def aan83_spectrum(gam, eps_soft, eps_hard):
    """AAN83 pair spectrum shape (arbitrary norm) on grid gam; 0 outside
    the physical support (bracket must be positive and 0 < gam < eps_hard)."""
    g = np.asarray(gam, dtype=float)
    out = np.zeros_like(g)
    d = g * (eps_hard - g)
    ok = (g > 0) & (g < eps_hard)
    ok &= np.where(ok, 4 * eps_soft * d / eps_hard > 1e-300, False)
    dd = d[ok]
    br = (4 * eps_hard**2 / dd * np.log(4 * eps_soft * dd / eps_hard)
          - 8 * eps_soft * eps_hard
          + 2 * (2 * eps_soft * eps_hard - 1) * eps_hard**2 / dd
          - (1 - 1 / (eps_soft * eps_hard)) * eps_hard**4 / dd**2)
    out[ok] = np.clip(br, 0.0, None)
    return out


def kinematic_bounds(eps_soft, eps_hard):
    """Exact pair-gamma limits over all collision angles and CM emission
    angles: gamma_pm = [E_tot -/+ P(s_max) * beta'(s_max)] / 2."""
    e_tot = eps_soft + eps_hard
    s_max = 4 * eps_soft * eps_hard
    p_tot = np.sqrt(e_tot**2 - s_max)
    beta_pair = np.sqrt(1 - 4 / s_max)
    return (e_tot - p_tot * beta_pair) / 2, (e_tot + p_tot * beta_pair) / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--step", type=int, default=None,
                    help="particle output step (default: last)")
    args = ap.parse_args()

    run = RunReader(args.run_dir)
    step = args.step if args.step is not None else max(run.steps["particles"])
    time, counts = run.particle_counts(step)

    eps_soft = float(run.attrs["setup.photonEnergy"])   # figure's eps_1
    eps_hard = float(run.attrs["setup.epsilon1"])       # figure's eps_2
    g_lo, g_hi = kinematic_bounds(eps_soft, eps_hard)

    print(f"run={run.run_dir.name}  step={step}  t={time:g}  stride={run.stride}")
    print(f"eps_soft(bath)={eps_soft}  eps_hard(injected)={eps_hard}  "
          f"kinematic gamma range [{g_lo:.3f}, {g_hi:.3f}]")

    edges = np.geomspace(1.2, 1.3 * g_hi, 71)
    widths = np.diff(edges)
    centers = np.sqrt(edges[:-1] * edges[1:])

    # analytic shape, normalized per species below
    dense = np.geomspace(edges[0], edges[-1], 4000)
    shape = aan83_spectrum(dense, eps_soft, eps_hard)
    shape_int = np.trapezoid(shape, dense)

    vs.apply_style()
    fig, ax = plt.subplots(figsize=(6.4, 4.6))

    stats = {}
    for s in (4, 5):
        gam = run.particle_gammas(step, s)
        n = gam.size * run.stride
        hist, _ = np.histogram(gam, bins=edges)
        f_sim = hist * run.stride / widths          # dN/dgamma
        ax.stairs(f_sim, edges, color=vs.SPECIES_COLOR[s], linewidth=1.6,
                  label=f"simulation {run.species_label(s)}", baseline=None)

        # per-bin relative deviation where the analytic prediction is
        # well-populated (>=100 expected counts)
        f_ana_bins = np.interp(centers, dense, shape) * n / shape_int
        well = f_ana_bins * widths >= 100
        rel = np.abs(f_sim[well] - f_ana_bins[well]) / f_ana_bins[well]
        stats[s] = (n, gam.min(), gam.max(), np.median(rel), well.sum())

    n_ref = stats[4][0]
    ax.plot(dense, shape * n_ref / shape_int, color=vs.INK, linewidth=1.4,
            label="Aharonian+ 1983 analytics", zorder=1)
    for x, lab in ((g_lo, r"$\gamma_{\min}$"), (g_hi, r"$\gamma_{\max}$")):
        ax.axvline(x, color=vs.MUTED, linestyle="--", linewidth=1.0)
    ax.plot([], [], color=vs.MUTED, linestyle="--", linewidth=1.0,
            label=rf"$\gamma_{{\min}},\gamma_{{\max}}$ = {g_lo:.2f}, {g_hi:.1f}")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(edges[0], edges[-1])
    ax.set_xlabel(r"pair Lorentz factor $\gamma$ (dimensionless)")
    ax.set_ylabel(r"$f(\gamma) = dN/d\gamma$ (pairs per unit $\gamma$)")
    ax.set_title(
        "BW pair spectrum vs Aharonian+ 1983 analytics\n"
        rf"$\varepsilon_1={eps_soft}$, $\varepsilon_2={eps_hard:g}\ m_ec^2$ — "
        rf"run {run.run_dir.name}, $t={time:.0f}$")
    ax.legend(loc="lower center")

    out_dir = Path(__file__).resolve().parents[1] / "plots" / run.run_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"pair_spectrum_vs_aan83_step{step:08d}.png"
    fig.tight_layout()
    fig.savefig(out)
    print(f"wrote {out}")

    for s in (4, 5):
        n, gmin, gmax, med, nbins = stats[s]
        print(f"species {s} ({run.species_label(s)}): N={n:.4g}  "
              f"gamma range [{gmin:.3f}, {gmax:.3f}]  "
              f"median |sim-ana|/ana = {med:.3f} over {nbins} bins")


if __name__ == "__main__":
    main()
