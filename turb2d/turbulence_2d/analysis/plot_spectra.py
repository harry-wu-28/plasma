
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.cm as cm

from read_bp import get_bp_files, read_fields, read_spectra
from spectrum_utils import isotropic_mag_spectrum, kolmogorov_ref, L, D_SKIN

PLOT_DIR = os.path.join(os.path.dirname(__file__), "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

L_ESC  = 64.0   # escape length for time normalisation
N_REP  = 20     # number of snapshots for magnetic spectrum plot


# ── Particle spectra ──────────────────────────────────────────────────────────

def _load_all_spectra():
    return sorted([read_spectra(f) for f in get_bp_files("spectra")],
                  key=lambda x: x["time"])


def plot_spectra_evolution(data, n_curves=10):
    idxs   = np.linspace(0, len(data) - 1, n_curves, dtype=int)
    colors = cm.plasma(np.linspace(0.1, 0.95, n_curves))

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=False)
    for ax, sp_key, sp_label in [
        (axes[0], "sN_1", r"$e^-$ (species 1)"),
        (axes[1], "sN_2", r"$e^+$ (species 2)"),
    ]:
        for i, color in zip(idxs, colors):
            d      = data[i]
            gamma  = d["energy_bins"]
            counts = d[sp_key]
            mask   = counts > 0
            if mask.sum() < 2:
                continue
            ax.loglog(gamma[mask], counts[mask], color=color, lw=1.5, alpha=0.85)
        ax.set_xlabel(r"$\gamma - 1$  (kinetic energy / $mc^2$)", fontsize=12)
        ax.set_ylabel(r"$dN/d\gamma$", fontsize=12)
        ax.set_title(sp_label, fontsize=13)
        ax.grid(alpha=0.3, which="both")

    sm = cm.ScalarMappable(cmap="plasma",
                           norm=plt.Normalize(data[0]["time"], data[-1]["time"]))
    sm.set_array([])
    fig.colorbar(sm, ax=axes.ravel().tolist(), shrink=0.8, pad=0.02).set_label(
        r"Time $[c/\omega_0]$", fontsize=11)
    fig.suptitle("Particle Energy Spectra Evolution", fontsize=14)
    fig.tight_layout()
    out = os.path.join(PLOT_DIR, "spectra_evolution.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out}")


def plot_final_spectra(data):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, sp_key, sp_label in [
        (axes[0], "sN_1", r"$e^-$ (species 1)"),
        (axes[1], "sN_2", r"$e^+$ (species 2)"),
    ]:
        for d, ls, color, lw in [
            (data[0],  "--", "steelblue", 1.5),
            (data[-1], "-",  "tomato",    2.0),
        ]:
            gamma  = d["energy_bins"]
            counts = d[sp_key]
            mask   = counts > 0
            ax.loglog(gamma[mask], counts[mask], ls=ls, color=color, lw=lw,
                      label=f"t={d['time']:.0f}")

        # Power-law fit on final spectrum
        gamma  = data[-1]["energy_bins"]
        counts = data[-1][sp_key]
        fmask  = (gamma >= 2.0) & (gamma <= 50.0) & (counts > 0)
        if fmask.sum() >= 3:
            slope, intercept = np.polyfit(np.log10(gamma[fmask]),
                                          np.log10(counts[fmask]), 1)
            gfit = np.logspace(np.log10(2), np.log10(100), 50)
            ax.loglog(gfit, 10**intercept * gfit**slope, "k--", lw=1.5,
                      label=rf"fit: $\gamma^{{{slope:.2f}}}$")
            ax.text(0.05, 0.15, rf"$p = {-slope:.2f}$", transform=ax.transAxes,
                    fontsize=12, bbox=dict(facecolor="white", alpha=0.7))

        ax.set_xlabel(r"$\gamma - 1$", fontsize=12)
        ax.set_ylabel(r"$dN/d\gamma$", fontsize=12)
        ax.set_title(sp_label, fontsize=13)
        ax.legend(fontsize=10)
        ax.grid(alpha=0.3, which="both")

    fig.suptitle("Energy Spectra: Initial vs Final", fontsize=14)
    fig.tight_layout()
    out = os.path.join(PLOT_DIR, "spectra_final.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out}")


def plot_spectra_2d(data):
    times = np.array([d["time"] for d in data])
    gamma = data[0]["energy_bins"]
    for sp_key, sp_label, fname in [
        ("sN_1", r"$e^-$", "spectra_2d_e.png"),
        ("sN_2", r"$e^+$", "spectra_2d_p.png"),
    ]:
        arr = np.array([d[sp_key] for d in data], dtype=float)
        arr[arr <= 0] = np.nan
        fig, ax = plt.subplots(figsize=(10, 6))
        im = ax.pcolormesh(gamma, times, np.log10(arr), cmap="inferno", shading="auto")
        ax.set_xscale("log")
        ax.set_xlabel(r"$\gamma - 1$", fontsize=12)
        ax.set_ylabel(r"Time $[c/\omega_0]$", fontsize=12)
        ax.set_title(f"log$_{{10}}$(N) vs time — {sp_label}", fontsize=13)
        fig.colorbar(im, ax=ax).set_label(r"$\log_{10}(dN/d\gamma)$", fontsize=11)
        fig.tight_layout()
        out = os.path.join(PLOT_DIR, fname)
        fig.savefig(out, dpi=150)
        plt.close(fig)
        print(f"  Saved: {out}")


# ── Magnetic power spectrum ───────────────────────────────────────────────────

def plot_mag_spectrum():
    field_files = get_bp_files("fields")[2:]
    if not field_files:
        print("  No field BP files found — skipping magnetic spectrum.")
        return

    idxs  = np.linspace(0, len(field_files) - 1, N_REP, dtype=int)
    files = [field_files[i] for i in idxs]

    print(f"  Computing B spectrum for {len(files)} snapshots...")
    times  = []
    kd_all = []
    Ek_all = []
    for i, f in enumerate(files):
        print(f"    [{i+1}/{len(files)}]", end="\r", flush=True)
        fdata = read_fields(f, field_names=["fB1", "fB2", "fB3"])
        times.append(fdata["time"])
        kd, E_k, _, _ = isotropic_mag_spectrum(fdata, L=L, D_SKIN=D_SKIN)
        kd_all.append(kd)
        Ek_all.append(E_k)
    print()

    times = np.array(times)
    tau   = times / L_ESC

    fig, ax = plt.subplots(figsize=(7, 5))
    fig.subplots_adjust(right=0.84)
    norm_c = mpl.colors.Normalize(vmin=tau.min(), vmax=tau.max())
    cmap   = mpl.colormaps.get_cmap("plasma")

    for i, (t, kd, E_k) in enumerate(zip(tau, kd_all, Ek_all)):
        mask = (kd > 0) & (E_k > 0) & np.isfinite(E_k)
        if mask.sum() < 2:
            continue
        ax.loglog(kd[mask], E_k[mask], color=cmap(norm_c(t)), lw=0.9, alpha=0.85)
        if i == len(tau) - 1:
            k_ref, E_ref = kolmogorov_ref(kd, E_k)
            if k_ref is not None:
                ax.loglog(k_ref, E_ref, "k--", lw=1.5, label=r"$\propto k_\perp^{-5/3}$")

    ax.set_xlabel(r"$k_\perp\,d_e$", fontsize=12)
    ax.set_ylabel(r"$E_B(k_\perp)$", fontsize=12)
    ax.legend(fontsize=10, loc="lower left")
    ax.grid(True, which="both", ls="--", lw=0.4, alpha=0.5)

    cax = fig.add_axes([0.86, 0.14, 0.025, 0.72])
    sm  = mpl.cm.ScalarMappable(norm=norm_c, cmap=cmap)
    sm.set_array([])
    fig.colorbar(sm, cax=cax).set_label(r"$tc/l_\mathrm{esc}$", fontsize=11)

    out = os.path.join(PLOT_DIR, "Bspectrum_evolution.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Energy spectra diagnostics.")
    parser.add_argument("--no-particle", action="store_true",
                        help="Skip particle energy spectra")
    parser.add_argument("--no-magnetic", action="store_true",
                        help="Skip magnetic power spectrum")
    args = parser.parse_args()

    if not args.no_particle:
        print("Loading particle spectra...")
        data = _load_all_spectra()
        if data:
            print(f"  {len(data)} snapshots, t={data[0]['time']:.1f} to {data[-1]['time']:.1f}")
            print("  Plotting evolution...")
            plot_spectra_evolution(data)
            print("  Plotting initial vs final...")
            plot_final_spectra(data)
            print("  Plotting 2D spectrogram...")
            plot_spectra_2d(data)
        else:
            print("  No spectra files found.")

    if not args.no_magnetic:
        print("Plotting magnetic power spectrum...")
        plot_mag_spectrum()

    print("Done.")


if __name__ == "__main__":
    main()
