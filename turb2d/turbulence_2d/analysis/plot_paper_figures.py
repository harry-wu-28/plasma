"""
plot_paper_figures.py
=====================
Reproduce the 4-panel reference figure:
  (a) Magnetic energy power spectrum E_mag(k_perp) vs k_perp*d
  (b) EdN/dE vs E/mc^2 (species 1 solid, species 2 dashed)
  (c) rho_max / l_esc vs tc/l_esc
  (d) beta (power-law spectral index) vs tc/l_esc

Physical parameters from turb_2d_GPU.toml:
  domain   = [-64, 64] x [-64, 64]  ->  L = 128
  skindepth0 = 1.0  ->  d = 1
  l_esc    = L / 2 = 64  (half domain; adjust if needed)
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import pandas as pd

from read_bp import (
    get_bp_files, read_fields, read_spectra, read_particles,
    DATA_DIR, STATS_FILE,
)
from spectrum_utils import isotropic_mag_spectrum, kolmogorov_ref, L, D_SKIN

PLOT_DIR = os.path.join(os.path.dirname(__file__), "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

L_ESC = 64.0   # escape length (half domain)


def t_norm(t):
    return t / L_ESC


# ── Panel (b): EdN/dE ─────────────────────────────────────────────────────────

def compute_EdNdE(d):
    """Return (E_mids, EdNdE_1, EdNdE_2) from a spectra dict."""
    ebn = d["sEbn"].astype(np.float64)
    n1  = d["sN_1"].astype(np.float64)
    n2  = d["sN_2"].astype(np.float64)
    dE      = np.diff(ebn)
    E_mids  = 0.5 * (ebn[:-1] + ebn[1:])
    EdNdE_1 = np.where(dE > 0, E_mids * n1 / dE, 0.0)
    EdNdE_2 = np.where(dE > 0, E_mids * n2 / dE, 0.0)
    return E_mids, EdNdE_1, EdNdE_2


# ── Panel (c): rho_max / l_esc ────────────────────────────────────────────────

def compute_rho_max(part, t_stats, B_rms):
    """Max Larmor radius: p_max / B_rms(t)."""
    u1 = part["u1_1"]; u2 = part["u2_1"]; u3 = part["u3_1"]
    p_max = np.percentile(np.sqrt(u1**2 + u2**2 + u3**2), 99.9)
    idx   = np.argmin(np.abs(t_stats - part["time"]))
    B     = B_rms[idx]
    return p_max / B if B > 0 else np.nan


# ── Panel (d): beta ───────────────────────────────────────────────────────────

def fit_beta(E_mids, EdNdE, E_min=5.0, E_max=200.0):
    """Fit EdNdE ~ E^(1-beta) -> return beta."""
    mask = (E_mids >= E_min) & (E_mids <= E_max) & (EdNdE > 0)
    if mask.sum() < 4:
        return np.nan
    slope, _ = np.polyfit(np.log10(E_mids[mask]), np.log10(EdNdE[mask]), 1)
    return 1.0 - slope


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # ── Stats ────────────────────────────────────────────────────────────────
    stats   = pd.read_csv(STATS_FILE, skipinitialspace=True)
    t_stats = stats["time"].values
    B_rms   = np.sqrt(
        stats["B1^2"].values + stats["B2^2"].values + stats["B3^2"].values
    )

    # ── Spectra ──────────────────────────────────────────────────────────────
    print("Loading spectra...")
    spec_files   = get_bp_files("spectra")
    spectra_data = sorted([read_spectra(f) for f in spec_files],
                          key=lambda x: x["time"])
    t_spec = np.array([d["time"] for d in spectra_data])
    print(f"  {len(spectra_data)} spectra snapshots")

    B_sq         = stats["B1^2"].values + stats["B2^2"].values + stats["B3^2"].values
    beta_plasma  = (stats["T00"].values - stats["Rho"].values) / (0.5 * B_sq)

    # ── rho_max(t) ───────────────────────────────────────────────────────────
    print("Loading particles for rho_max...")
    part_files = get_bp_files("particles")
    t_part     = []
    rho_max_t  = []
    for f in part_files:
        p = read_particles(f)
        t_part.append(p["time"])
        rho_max_t.append(compute_rho_max(p, t_stats, B_rms))
    t_part    = np.array(t_part)
    rho_max_t = np.array(rho_max_t)

    # ── Magnetic power spectra ───────────────────────────────────────────────
    print("Computing magnetic power spectra from fields...")
    field_files = get_bp_files("fields")[2:]   # skip first two timesteps (pre-cascade)
    field_times = []
    kd_all      = []
    Ek_all      = []

    for i, f in enumerate(field_files):
        print(f"  [{i+1}/{len(field_files)}]", end="\r", flush=True)
        fdata = read_fields(f, field_names=["fB1", "fB2", "fB3"])
        field_times.append(fdata["time"])
        kd, E_k, _, _ = isotropic_mag_spectrum(fdata, L=L, D_SKIN=D_SKIN)
        kd_all.append(kd)
        Ek_all.append(E_k)
    field_times = np.array(field_times)
    print()

    # ── Color normalisation ──────────────────────────────────────────────────
    t_all_max = max(field_times.max(), t_spec.max(), t_part.max())
    cmap      = cm.plasma
    norm_c    = plt.Normalize(0, t_norm(t_all_max))

    # ── Figure layout ────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(7, 12))
    gs  = fig.add_gridspec(4, 1, hspace=0.5,
                           height_ratios=[1.4, 1.4, 1.0, 1.0])
    ax_a = fig.add_subplot(gs[0])
    ax_b = fig.add_subplot(gs[1])
    ax_c = fig.add_subplot(gs[2])
    ax_d = fig.add_subplot(gs[3])

    # ── (a) magnetic power spectrum ───────────────────────────────────────────
    for t, kd, E_k in zip(field_times, kd_all, Ek_all):
        color = cmap(norm_c(t_norm(t)))
        mask  = (kd > 0) & (E_k > 0) & np.isfinite(E_k)
        if mask.sum() > 3:
            ax_a.loglog(kd[mask], E_k[mask], color=color, lw=0.8, alpha=0.85)

    k_ref, E_ref = kolmogorov_ref(kd_all[-1], Ek_all[-1])
    if k_ref is not None:
        ax_a.loglog(k_ref, E_ref, "k--", lw=1.5,
                    label=r"$\propto k_\perp^{-5/3}$")

    populated = [kd[(kd > 0) & (E_k > 0)] for kd, E_k in zip(kd_all, Ek_all)]
    populated = np.concatenate([p for p in populated if p.size > 0])
    ax_a.set_xlim(populated.min(), populated.max())
    ax_a.set_xlabel(r"$k_\perp d$", fontsize=11)
    ax_a.set_ylabel(r"$E_\mathrm{mag}(k_\perp)$", fontsize=11)
    ax_a.legend(fontsize=10, loc="lower left")
    ax_a.text(0.02, 0.96, "(a)", transform=ax_a.transAxes,
              fontsize=12, va="top", fontweight="bold")

    # ── (b) EdN/dE ───────────────────────────────────────────────────────────
    n_curves = 10
    idxs = np.linspace(0, len(spectra_data) - 1, n_curves, dtype=int)
    for i in idxs:
        d     = spectra_data[i]
        color = cmap(norm_c(t_norm(d["time"])))
        E, EdN1, EdN2 = compute_EdNdE(d)
        for EdN, ls in [(EdN1, "-"), (EdN2, "--")]:
            mask = EdN > 0
            if mask.sum() > 3:
                ax_b.loglog(E[mask], EdN[mask], color=color,
                            lw=1.0, ls=ls, alpha=0.85)

    from matplotlib.lines import Line2D
    ax_b.legend(
        handles=[Line2D([0], [0], color="gray", ls="-",  label=r"$e^-$ (sp. 1)"),
                 Line2D([0], [0], color="gray", ls="--", label=r"$e^+$ (sp. 2)")],
        fontsize=9, loc="lower left",
    )
    ax_b.set_xlabel(r"$E/(mc^2)$", fontsize=11)
    ax_b.set_ylabel(r"$EdN/dE$", fontsize=11)
    ax_b.text(0.02, 0.96, "(b)", transform=ax_b.transAxes,
              fontsize=12, va="top", fontweight="bold")

    # ── (c) rho_max / l_esc ──────────────────────────────────────────────────
    sort_idx = np.argsort(t_part)
    t_p_norm = t_norm(t_part[sort_idx])
    rho_norm = rho_max_t[sort_idx] / L_ESC
    valid    = np.isfinite(rho_norm)
    ax_c.semilogy(t_p_norm[valid], rho_norm[valid],
                  color="steelblue", lw=1.5)
    ax_c.set_xlabel(r"$tc/l_\mathrm{esc}$", fontsize=11)
    ax_c.set_ylabel(r"$\rho_\mathrm{max}/l_\mathrm{esc}$", fontsize=11)
    ax_c.text(0.02, 0.96, "(c)", transform=ax_c.transAxes,
              fontsize=12, va="top", fontweight="bold")

    # ── (d) plasma beta ──────────────────────────────────────────────────────
    ax_d.plot(t_norm(t_stats), beta_plasma, color="steelblue", lw=1.5)
    ax_d.set_xlabel(r"$tc/l_\mathrm{esc}$", fontsize=11)
    ax_d.set_ylabel(r"$\beta_\mathrm{plasma}$", fontsize=11)
    ax_d.text(0.02, 0.96, "(d)", transform=ax_d.transAxes,
              fontsize=12, va="top", fontweight="bold")

    # ── Shared colorbar for (a) and (b) ──────────────────────────────────────
    sm = cm.ScalarMappable(cmap=cmap, norm=norm_c)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=[ax_a, ax_b], shrink=0.95, pad=0.02)
    cbar.set_label(r"$tc/l_\mathrm{esc}$", fontsize=11)

    out = os.path.join(PLOT_DIR, "paper_figures.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
