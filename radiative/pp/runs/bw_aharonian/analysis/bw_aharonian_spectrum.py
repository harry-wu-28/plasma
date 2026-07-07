"""Breit-Wheeler validation: simulated pair spectrum vs Aharonian+ 1983.

Recreates the Entity docs two-photon test figure for this repo's pp pgen:
a hard isotropic monoenergetic photon population (setup.epsilon1, the
figure's eps_2) pair-producing on an implicit isotropic monoenergetic
bath (setup.photonEnergy, the figure's eps_1). The secondary e-/e+
spectra (species 4/5) are histogrammed from raw particle momenta (the
built-in spectra are zeroed by the pp zero-weight bug) and compared with
the pair spectrum of Agaronyan (Aharonian), Atoyan & Nagapetyan 1983,
Astrophysics 19, 187 (transl. of Astrofizika 19, 323),
doi:10.1007/BF01005624 — "AAN83". Our eps_1 = 0.1, eps_2 = 100 case is
exactly the paper's Fig. 1b curve 2. Everything in units m_e c^2 = 1.

Two analytic curves, both from the paper:

* EXACT, Eqs. (19)-(21): with E = w1 + w2, D = w2 - w1, x = eps - E/2,

    I(eps) ∝ (1/w1^2 w2) ∫_a^b dk (k^2 + E D)/k^3 [Phi(k,x) + Phi(k,-x)]
    Phi(k,x) = [1 + 4/(E^2-k^2) - 8/(E^2-k^2)^2] 2k/R(k,x)
               - 16 k (k^2 + 2 x D)/((E^2-k^2)^2 R^3(k,x)) - 1
    R(k,x)   = sqrt(4 (k^2 - D^2)/(E^2 - k^2) + (2x + D)^2)

  k = |k1+k2| is the photon-pair total momentum (s = E^2 - k^2). The
  k-limits printed as Eq. (21) are typographically ambiguous in the scan,
  so they are re-derived here from the paper's own constraint
  |x| <= (k/2) sqrt(1 - 4/(E^2-k^2))  ==>
    k^2 <=> (1/2)[E^2-4+4x^2 ± sqrt((E^2-4+4x^2)^2 - 16 E^2 x^2)],
  with additionally k >= D; this reproduces the paper's stated narrow
  interval w2-w1 <= k <= w2+w1 for w1 << 1, and the eps-support Eq. (22):
    |x| <= (D/2) sqrt(1 - 1/(w1 w2)).
  The spectrum is exactly symmetric about E/2 (electron <-> positron).

* ASYMPTOTIC, Eq. (25) (valid w1 << 1, E ~= w2):

    I(eps) ∝ 4E^2/((E-eps)eps) ln(4 w1 (E-eps) eps / E) - 8 w1 E
             + 2(2 w1 E - 1) E^2/((E-eps)eps)
             - (1 - 1/(w1 E)) E^4/((E-eps)^2 eps^2)

Both curves are normalized to the simulated per-species pair count, so
the comparison tests the *shape*; deviation stats are quoted against the
exact spectrum.

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

# shared analysis library lives at <pp>/analysis/scripts (this file is at
# <pp>/runs/<run>/analysis/)
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "analysis" / "scripts"))
from bp_reader import RunReader
import viz_style as vs


def aan83_exact(gam, w1, w2, n_nodes=256):
    """AAN83 exact pair spectrum, Eqs. (19)-(21) (arbitrary norm): 1D
    Gauss-Legendre integral over the photon-pair total momentum k for
    each pair energy gam. Zero outside the Eq. (22) support."""
    g = np.asarray(gam, dtype=float)
    E, D = w1 + w2, w2 - w1
    x = g - E / 2
    half_width = (D / 2) * np.sqrt(1 - 1 / (w1 * w2))
    ok = np.abs(x) < half_width

    A = E * E - 4 + 4 * x * x
    disc = np.sqrt(np.clip(A * A - 16 * E * E * x * x, 0.0, None))
    b2 = 0.5 * (A + disc)
    a2 = np.maximum(D * D, 0.5 * (A - disc))
    a = np.sqrt(np.clip(a2, 0.0, None))
    b = np.sqrt(np.clip(b2, 0.0, None))
    ok &= b > a

    # per-gamma k nodes, [n_nodes, len(g)]
    nodes, wts = np.polynomial.legendre.leggauss(n_nodes)
    k = 0.5 * (b + a) + 0.5 * (b - a) * nodes[:, None]
    jac = 0.5 * (b - a)

    m2 = E * E - k * k  # invariant s of the photon pair

    def phi(xx):
        R = np.sqrt(4 * (k * k - D * D) / m2 + (2 * xx + D) ** 2)
        return ((1 + 4 / m2 - 8 / m2**2) * 2 * k / R
                - 16 * k * (k * k + 2 * xx * D) / (m2**2 * R**3) - 1)

    with np.errstate(divide="ignore", invalid="ignore"):
        integrand = (k * k + E * D) / k**3 * (phi(x) + phi(-x))
        val = jac * np.einsum("i,ij->j", wts, np.nan_to_num(integrand))
    out = np.where(ok, val / (16 * w1**2 * w2), 0.0)
    return np.clip(out, 0.0, None)


def aan83_eq25(gam, w1, w2):
    """AAN83 asymptotic pair spectrum, Eq. (25) (arbitrary norm; valid
    w1 << 1, E ~= w2). Zero where the bracket goes negative."""
    g = np.asarray(gam, dtype=float)
    E = w2  # the paper sets E ~= w2 in this limit
    out = np.zeros_like(g)
    d = g * (E - g)
    ok = (g > 0) & (g < E)
    ok &= np.where(ok, 4 * w1 * d / E > 1e-300, False)
    dd = d[ok]
    br = (4 * E**2 / dd * np.log(4 * w1 * dd / E)
          - 8 * w1 * E
          + 2 * (2 * w1 * E - 1) * E**2 / dd
          - (1 - 1 / (w1 * E)) * E**4 / dd**2)
    out[ok] = np.clip(br, 0.0, None)
    return out


def kinematic_bounds(eps_soft, eps_hard):
    """Pair-energy support, AAN83 Eq. (22):
    (E -/+ D sqrt(1 - 1/(w1 w2))) / 2 — identical to the kinematic limits
    over all collision angles and CM emission angles."""
    e_tot = eps_soft + eps_hard
    delta = eps_hard - eps_soft
    hw = (delta / 2) * np.sqrt(1 - 1 / (eps_soft * eps_hard))
    return e_tot / 2 - hw, e_tot / 2 + hw


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

    # analytic shapes, normalized per species below; exact is the reference
    dense = np.geomspace(edges[0], edges[-1], 4000)
    shape = aan83_exact(dense, eps_soft, eps_hard)
    shape_int = np.trapezoid(shape, dense)
    shape25 = aan83_eq25(dense, eps_soft, eps_hard)
    shape25_int = np.trapezoid(shape25, dense)

    # quadrature self-check: doubling the nodes must not move the curve
    conv = aan83_exact(dense, eps_soft, eps_hard, n_nodes=512)
    live = shape > 0
    conv_err = np.max(np.abs(conv[live] - shape[live]) / shape[live])
    print(f"exact-spectrum quadrature check (256 vs 512 nodes): "
          f"max rel diff = {conv_err:.2e}")

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
            label="AAN83 exact, eqs. (19)-(21)", zorder=1)
    ax.plot(dense, shape25 * n_ref / shape25_int, color=vs.MUTED,
            linewidth=1.2, linestyle=":",
            label=r"AAN83 asymptotic, eq. (25) ($\omega_1\ll 1$)", zorder=1)
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

    out_dir = Path(__file__).resolve().parents[2] / run.run_dir.name / "plots"
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
