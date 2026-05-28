"""
plot_particles.py
=================
Phase-space and spatial diagnostics from particle snapshot files.

Variables per species s (1 = e-, 2 = e+):
  pX1_s, pX2_s  : positions
  pU1_s, pU2_s, pU3_s : four-velocity components (gamma * v/c)
  pW_s          : particle weights

Produces (in plots/particles/):
  xy_scatter_<step>.png     - Particle position scatter plot
  phase_x_u1_<step>.png     - Phase space x1 vs u1 for each species
  gamma_hist_<step>.png     - Lorentz factor distribution
  momentum_scatter_<step>.png - u1 vs u2 scatter

Run with:
    conda run -n analysis python plot_particles.py [--all] [--steps N ...]
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

from read_bp import get_bp_files, read_particles, gamma_from_u

PLOT_DIR = os.path.join(os.path.dirname(__file__), "plots", "particles")
os.makedirs(PLOT_DIR, exist_ok=True)

SPECIES = {1: (r"$e^-$", "steelblue"), 2: (r"$e^+$", "tomato")}


def plot_xy_scatter(pdata, out_path, max_pts=20000):
    """Particle x1-x2 position scatter."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
    fig.suptitle(f"Particle Positions   step={pdata['step']}   t={pdata['time']:.2f}",
                 fontsize=13)

    for ax, (s, (label, color)) in zip(axes, SPECIES.items()):
        x1 = pdata[f"x1_{s}"]
        x2 = pdata[f"x2_{s}"]
        n = len(x1)
        if n > max_pts:
            idx = np.random.choice(n, max_pts, replace=False)
            x1, x2 = x1[idx], x2[idx]
        ax.scatter(x1, x2, s=0.5, alpha=0.3, color=color, rasterized=True)
        ax.set_xlim(-64, 64)
        ax.set_ylim(-64, 64)
        ax.set_aspect("equal")
        ax.set_xlabel(r"$x_1 / d_e$", fontsize=11)
        ax.set_ylabel(r"$x_2 / d_e$", fontsize=11)
        ax.set_title(f"{label}  (N={n:,})", fontsize=12)
        ax.grid(alpha=0.2)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_path}")


def plot_phase_space(pdata, out_path, max_pts=30000):
    """x1 vs u1 phase space for each species."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"Phase Space   step={pdata['step']}   t={pdata['time']:.2f}",
                 fontsize=13)

    for row, (s, (label, color)) in enumerate(SPECIES.items()):
        x1 = pdata[f"x1_{s}"]
        u1 = pdata[f"u1_{s}"]
        u2 = pdata[f"u2_{s}"]
        n = len(x1)
        if n > max_pts:
            idx = np.random.choice(n, max_pts, replace=False)
            x1, u1, u2 = x1[idx], u1[idx], u2[idx]

        # x1 vs u1
        ax = axes[row, 0]
        h, xe, ye, im = ax.hist2d(x1, u1, bins=100, norm=LogNorm(), cmap="inferno")
        ax.set_xlabel(r"$x_1 / d_e$", fontsize=10)
        ax.set_ylabel(r"$u_1 = \gamma v_1/c$", fontsize=10)
        ax.set_title(f"{label}: $x_1$–$u_1$ phase space", fontsize=11)
        plt.colorbar(im, ax=ax, label="counts")

        # x1 vs u2
        ax = axes[row, 1]
        h, xe, ye, im = ax.hist2d(x1, u2, bins=100, norm=LogNorm(), cmap="inferno")
        ax.set_xlabel(r"$x_1 / d_e$", fontsize=10)
        ax.set_ylabel(r"$u_2 = \gamma v_2/c$", fontsize=10)
        ax.set_title(f"{label}: $x_1$–$u_2$ phase space", fontsize=11)
        plt.colorbar(im, ax=ax, label="counts")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_path}")


def plot_gamma_hist(pdata, out_path, n_bins=80):
    """Lorentz factor distribution for each species."""
    fig, ax = plt.subplots(figsize=(9, 6))

    for s, (label, color) in SPECIES.items():
        u1 = pdata[f"u1_{s}"]
        u2 = pdata[f"u2_{s}"]
        u3 = pdata[f"u3_{s}"]
        w = pdata[f"w_{s}"]
        gamma = gamma_from_u(u1, u2, u3)
        kin = gamma - 1.0  # kinetic energy in mc^2

        bins = np.logspace(np.log10(max(kin.min(), 1e-3)), np.log10(kin.max() + 1), n_bins)
        counts, edges = np.histogram(kin, bins=bins, weights=w)
        mids = 0.5 * (edges[:-1] + edges[1:])
        mask = counts > 0
        ax.loglog(mids[mask], counts[mask], color=color, lw=2, label=label)

    ax.set_xlabel(r"$\gamma - 1$  (kinetic energy / $mc^2$)", fontsize=12)
    ax.set_ylabel(r"$dN/d(\gamma-1)$", fontsize=12)
    ax.set_title(f"Lorentz Factor Distribution   step={pdata['step']}   t={pdata['time']:.2f}",
                 fontsize=13)
    ax.legend(fontsize=11)
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_path}")


def plot_momentum_scatter(pdata, out_path, max_pts=20000):
    """u1 vs u2 momentum scatter."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(f"Momentum Space   step={pdata['step']}   t={pdata['time']:.2f}",
                 fontsize=13)

    for ax, (s, (label, color)) in zip(axes, SPECIES.items()):
        u1 = pdata[f"u1_{s}"]
        u2 = pdata[f"u2_{s}"]
        n = len(u1)
        if n > max_pts:
            idx = np.random.choice(n, max_pts, replace=False)
            u1, u2 = u1[idx], u2[idx]

        h, xe, ye, im = ax.hist2d(u1, u2, bins=80, norm=LogNorm(), cmap="plasma")
        ax.set_xlabel(r"$u_1 = \gamma v_1/c$", fontsize=11)
        ax.set_ylabel(r"$u_2 = \gamma v_2/c$", fontsize=11)
        ax.set_title(label, fontsize=12)
        plt.colorbar(im, ax=ax, label="counts")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_path}")


def process_snapshot(bp_path):
    step_str = os.path.basename(bp_path).split(".")[1]
    pdata = read_particles(bp_path)

    plot_xy_scatter(pdata, os.path.join(PLOT_DIR, f"xy_scatter_{step_str}.png"))
    plot_phase_space(pdata, os.path.join(PLOT_DIR, f"phase_x_u_{step_str}.png"))
    plot_gamma_hist(pdata, os.path.join(PLOT_DIR, f"gamma_hist_{step_str}.png"))
    plot_momentum_scatter(pdata, os.path.join(PLOT_DIR, f"momentum_{step_str}.png"))


def main():
    parser = argparse.ArgumentParser(description="Plot particle phase space diagnostics.")
    parser.add_argument("--all", action="store_true", help="Process all snapshots")
    parser.add_argument("--steps", nargs="+", type=int,
                        help="Specific step numbers to plot")
    args = parser.parse_args()

    bp_files = get_bp_files("particles")
    if not bp_files:
        print("No particle BP files found.")
        return

    if args.all:
        selected = bp_files
    elif args.steps:
        selected = []
        for s in args.steps:
            step_str = f"{s:08d}"
            match = [f for f in bp_files if step_str in f]
            if match:
                selected.extend(match)
            else:
                print(f"  Warning: step {s} not found")
    else:
        n = len(bp_files)
        idxs = sorted(set([0, n//4, n//2, 3*n//4, n - 1]))
        selected = [bp_files[i] for i in idxs]

    print(f"Processing {len(selected)} particle snapshot(s)...")
    for bp in selected:
        step_str = os.path.basename(bp).split(".")[1]
        print(f"  Step {step_str}...")
        process_snapshot(bp)

    print("Done.")


if __name__ == "__main__":
    main()
