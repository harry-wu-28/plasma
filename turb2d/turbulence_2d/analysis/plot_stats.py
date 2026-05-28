"""
plot_stats.py
=============
Plot time-evolution diagnostics from turbulence_stats.csv.

Produces:
  plots/stats_energy.png      - Magnetic and electric energy components
  plots/stats_total_energy.png - Total field energy + T00 (plasma energy)
  plots/stats_exb.png          - Poynting flux (ExB) components
  plots/stats_current_rho.png  - Charge density evolution

Run with:
    conda run -n analysis python plot_stats.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from read_bp import STATS_FILE

PLOT_DIR = os.path.join(os.path.dirname(__file__), "plots")
os.makedirs(PLOT_DIR, exist_ok=True)


def load_stats():
    df = pd.read_csv(STATS_FILE, skipinitialspace=True)
    df.columns = [c.strip() for c in df.columns]
    return df


def plot_field_energies(df):
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # Magnetic energy
    ax = axes[0]
    ax.plot(df["time"], df["B1^2"], label=r"$\langle B_x^2 \rangle$")
    ax.plot(df["time"], df["B2^2"], label=r"$\langle B_y^2 \rangle$")
    ax.plot(df["time"], df["B3^2"], label=r"$\langle B_z^2 \rangle$")
    ax.set_ylabel(r"Magnetic energy density", fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)

    # Electric energy
    ax = axes[1]
    ax.plot(df["time"], df["E1^2"], label=r"$\langle E_x^2 \rangle$")
    ax.plot(df["time"], df["E2^2"], label=r"$\langle E_y^2 \rangle$")
    ax.plot(df["time"], df["E3^2"], label=r"$\langle E_z^2 \rangle$")
    ax.set_xlabel(r"Time $[c/\omega_0]$", fontsize=12)
    ax.set_ylabel(r"Electric energy density", fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)

    fig.suptitle("Field Energy Components", fontsize=14)
    fig.tight_layout()
    out = os.path.join(PLOT_DIR, "stats_energy.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out}")


def plot_total_energy(df):
    B_tot = df["B1^2"] + df["B2^2"] + df["B3^2"]
    E_tot = df["E1^2"] + df["E2^2"] + df["E3^2"]
    field_tot = B_tot + E_tot

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    ax = axes[0]
    ax.plot(df["time"], B_tot, label=r"$\langle B^2 \rangle$", color="steelblue")
    ax.plot(df["time"], E_tot, label=r"$\langle E^2 \rangle$", color="tomato")
    ax.plot(df["time"], field_tot, label=r"$\langle B^2+E^2 \rangle$", color="k", lw=2)
    ax.set_ylabel("Field energy density", fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)

    ax = axes[1]
    ax.plot(df["time"], df["T00"], label=r"$T^{00}$ (plasma energy)", color="darkorange", lw=2)
    ax.set_xlabel(r"Time $[c/\omega_0]$", fontsize=12)
    ax.set_ylabel(r"$T^{00}$", fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)

    fig.suptitle("Total Energy Evolution", fontsize=14)
    fig.tight_layout()
    out = os.path.join(PLOT_DIR, "stats_total_energy.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out}")


def plot_exb(df):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df["time"], df["ExB1"], label=r"$(E \times B)_x$")
    ax.plot(df["time"], df["ExB2"], label=r"$(E \times B)_y$")
    ax.plot(df["time"], df["ExB3"], label=r"$(E \times B)_z$")
    ax.axhline(0, color="k", lw=0.8, ls="--")
    ax.set_xlabel(r"Time $[c/\omega_0]$", fontsize=12)
    ax.set_ylabel(r"$\langle E \times B \rangle$", fontsize=12)
    ax.set_title("Poynting Flux (ExB) Components", fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out = os.path.join(PLOT_DIR, "stats_exb.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out}")


def plot_reconnection_proxy(df):
    """
    Reconnection proxy: plot dB^2/dt (rate of magnetic energy dissipation)
    and the ratio of in-plane to out-of-plane magnetic energy.
    """
    B_ip = df["B1^2"] + df["B2^2"]   # in-plane (x, y)
    B_op = df["B3^2"]                  # out-of-plane (z = guide field)
    ratio = B_ip / B_op

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    ax = axes[0]
    ax.plot(df["time"], B_ip, label=r"$\langle B_x^2 + B_y^2 \rangle$ (in-plane)", color="steelblue")
    ax.plot(df["time"], B_op, label=r"$\langle B_z^2 \rangle$ (guide field)", color="tomato")
    ax.set_ylabel("Magnetic energy density", fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)

    ax = axes[1]
    ax.plot(df["time"], ratio, color="purple", lw=2)
    ax.set_xlabel(r"Time $[c/\omega_0]$", fontsize=12)
    ax.set_ylabel(r"$(B_x^2+B_y^2) / B_z^2$", fontsize=12)
    ax.set_title("In-plane vs Guide Field Ratio", fontsize=12)
    ax.grid(alpha=0.3)

    fig.suptitle("Magnetic Field Component Analysis", fontsize=14)
    fig.tight_layout()
    out = os.path.join(PLOT_DIR, "stats_bfield_ratio.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out}")


def main():
    print("Loading stats...")
    df = load_stats()
    print(f"  {len(df)} timesteps, t = {df['time'].iloc[0]:.1f} to {df['time'].iloc[-1]:.1f}")

    print("Plotting field energies...")
    plot_field_energies(df)

    print("Plotting total energy...")
    plot_total_energy(df)

    print("Plotting ExB (Poynting flux)...")
    plot_exb(df)

    print("Plotting B-field ratio...")
    plot_reconnection_proxy(df)

    print("Done.")


if __name__ == "__main__":
    main()
