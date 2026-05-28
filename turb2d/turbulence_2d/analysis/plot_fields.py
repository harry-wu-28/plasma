"""
plot_fields.py
==============
All field-space diagnostics. Three modes:

  panels  (default)  6-panel overviews at selected timesteps.
  --check            Compare first vs last snapshot field-by-field.
  --video            Render all snapshots into an MP4 via ffmpeg.

Panel mode flags:
  --all              Process every snapshot
  --steps N ...      Specific step numbers
  --index I          Single snapshot by index (0 = first, -1 = last)

Video mode flags (require --video):
  --fps N            Frames per second (default: 10)
  --dpi N            Frame DPI (default: 100)
  --field FIELD      Animate one field instead of all 9 panels
  --keep-frames      Keep intermediate PNGs after encoding

Outputs:
  plots/fields/panel_<step>.png          (panels)
  plots/fields/boundary_check.png        (--check)
  plots/field_evolution[_<field>].mp4    (--video)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import argparse
import subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import CenteredNorm, LogNorm
import pandas as pd

from read_bp import get_bp_files, read_fields, STATS_FILE

PLOT_DIR   = os.path.join(os.path.dirname(__file__), "plots")
FIELDS_DIR = os.path.join(PLOT_DIR, "fields")
FRAME_DIR  = os.path.join(PLOT_DIR, "video_frames")
os.makedirs(FIELDS_DIR, exist_ok=True)

PANEL_NAMES = ["Bz", "Jz", "Jx", "Jy", "Ez", "N", "rho", "Eip", "Bip",
               "Ex", "Ey", "Bx", "By"]
PANEL_TITLES = {
    "Bz": r"$B_z$",        "Jz": r"$J_z$",        "Jx": r"$J_x$",
    "Jy": r"$J_y$",        "Ez": r"$E_z$",         "N":  r"$N_-+N_+$",
    "rho": r"$\rho_-+\rho_+$", "Eip": r"$|E_{x,y}|$", "Bip": r"$|B_{x,y}|$",
    "Ex": r"$E_x$",        "Ey": r"$E_y$",
    "Bx": r"$B_x$",        "By": r"$B_y$",
}


# ── Shared helpers ────────────────────────────────────────────────────────────

def _get(fields, key, x1, x2, default=0.0):
    v = fields.get(key)
    return v if v is not None else np.full((len(x1), len(x2)), default)


def _extract_panels(fields):
    x1, x2 = fields["x1"], fields["x2"]
    def g(k): return _get(fields, k, x1, x2)
    ex, ey, bx, by = g("fE1"), g("fE2"), g("fB1"), g("fB2")
    return {
        "Bz": g("fB3"),   "Jz": g("fJ3"),   "Jx": g("fJ1"),   "Jy": g("fJ2"),
        "Ez": g("fE3"),   "N":  g("fN_1") + g("fN_2"),
        "rho": g("fRho_1") + g("fRho_2"),
        "Eip": np.sqrt(ex**2 + ey**2),   "Bip": np.sqrt(bx**2 + by**2),
        "Ex": ex, "Ey": ey, "Bx": bx, "By": by,
    }


def _fields_all_zero(fields, tol=1e-30):
    return not any(
        isinstance(v, np.ndarray) and v.ndim == 2 and np.any(np.abs(v) > tol)
        for v in fields.values()
    )


def _imshow(ax, x1, x2, data, title="", cmap="RdBu_r",
            symmetric=True, log=False, cbar_label=""):
    extent = [x1[0], x1[-1], x2[0], x2[-1]]
    kw = dict(origin="lower", extent=extent, aspect="equal", cmap=cmap)
    if log and np.any(data > 0):
        vmin = data[data > 0].min()
        im = ax.imshow(data.T, norm=LogNorm(vmin=vmin, vmax=data.max()), **kw)
    elif symmetric:
        im = ax.imshow(data.T, norm=CenteredNorm(), **kw)
    else:
        im = ax.imshow(data.T, **kw)
    cb = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    if cbar_label:
        cb.set_label(cbar_label, fontsize=9)
    cb.ax.tick_params(labelsize=8)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel(r"$x_1\;[d_e]$", fontsize=9)
    ax.set_ylabel(r"$x_2\;[d_e]$", fontsize=9)
    ax.tick_params(labelsize=8)
    return im


# ── Panel rendering ───────────────────────────────────────────────────────────

def make_panel(fields, out_path):
    x1, x2 = fields["x1"], fields["x2"]
    t, s   = fields["time"], fields["step"]

    def g(k): return _get(fields, k, x1, x2)
    b3 = g("fB3"); j3 = g("fJ3")
    e1 = g("fE1"); e2 = g("fE2")
    b1 = g("fB1"); b2 = g("fB2")

    fig, axes = plt.subplots(2, 3, figsize=(18, 11))
    fig.suptitle(f"Field Overview   step={s}   t={t:.2f}", fontsize=13)

    _imshow(axes[0,0], x1, x2, b3,                      r"$B_z$",          "RdBu_r",  symmetric=True,  cbar_label=r"$B_z$")
    _imshow(axes[0,1], x1, x2, j3,                      r"$J_z$",          "RdBu_r",  symmetric=True,  cbar_label=r"$J_z$")
    _imshow(axes[0,2], x1, x2, g("fN_1")+g("fN_2"),     r"$N_-+N_+$",      "inferno", symmetric=False, cbar_label=r"$N$")
    _imshow(axes[1,0], x1, x2, g("fRho_1")+g("fRho_2"), r"$\rho_-+\rho_+$","RdBu_r",  symmetric=True,  cbar_label=r"$\rho$")
    _imshow(axes[1,1], x1, x2, np.sqrt(e1**2+e2**2),    r"$|E_{x,y}|$",    "magma",   symmetric=False, cbar_label=r"$|E_\perp|$")
    _imshow(axes[1,2], x1, x2, np.sqrt(b1**2+b2**2),    r"$|B_{x,y}|$",    "magma",   symmetric=False, cbar_label=r"$|B_\perp|$")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


# ── Panels mode ───────────────────────────────────────────────────────────────

def run_panels(args):
    bp_files = get_bp_files("fields")
    if not bp_files:
        print("No field BP files found.")
        return

    if args.all:
        selected = bp_files
    elif args.steps:
        selected = []
        for s in args.steps:
            match = [f for f in bp_files if f"{s:08d}" in f]
            selected.extend(match) if match else print(f"  Warning: step {s} not found")
    elif args.index is not None:
        selected = [bp_files[args.index]]
    else:
        n = len(bp_files)
        selected = [bp_files[i] for i in sorted(set([0, n//4, n//2, 3*n//4, n-1]))]

    print(f"Processing {len(selected)} snapshot(s)...")
    zero_count = 0
    for bp in selected:
        step_str = os.path.basename(bp).split(".")[1]
        print(f"  Step {step_str}...")
        fdata = read_fields(bp)
        if _fields_all_zero(fdata):
            print(f"    WARNING: all fields zero (GPU output not flushed). Skipping.")
            zero_count += 1
            continue
        make_panel(fdata, os.path.join(FIELDS_DIR, f"panel_{step_str}.png"))

    if zero_count == len(selected):
        print("\nAll snapshots have zero field data — falling back to stats CSV.")
        _fallback_energy_plot()


def _fallback_energy_plot():
    try:
        df = pd.read_csv(STATS_FILE, skipinitialspace=True)
        df.columns = [c.strip() for c in df.columns]
    except FileNotFoundError:
        print(f"  Stats file not found: {STATS_FILE}")
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df["time"], df["B1^2"] + df["B2^2"] + df["B3^2"],
            label=r"$\langle B^2 \rangle$", lw=2, color="steelblue")
    ax.set_xlabel(r"Time $[c/\omega_0]$", fontsize=12)
    ax.set_ylabel("Magnetic energy density", fontsize=12)
    ax.set_title("Field energy from stats CSV (BP field arrays are zero)", fontsize=12)
    ax.grid(alpha=0.3); ax.legend(fontsize=11)
    fig.tight_layout()
    out = os.path.join(FIELDS_DIR, "field_energy_from_stats.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out}")


# ── Check mode ────────────────────────────────────────────────────────────────

def run_check():
    bp_files = get_bp_files("fields")
    if not bp_files:
        print("No field BP files found.")
        return

    def _report(label, bp_path):
        print(f"\n{'='*55}\n  {label}: {os.path.basename(bp_path)}\n{'='*55}")
        fdata = read_fields(bp_path)
        print(f"  step={fdata['step']}   time={fdata['time']:.4f}")
        keys = sorted(k for k, v in fdata.items()
                      if isinstance(v, np.ndarray) and v.ndim == 2)
        allzero = True
        for k in keys:
            absmax = float(np.abs(fdata[k]).max())
            if absmax > 1e-30:
                allzero = False
            print(f"    {k:12s}  {'ALL ZERO' if absmax <= 1e-30 else f'max|v|={absmax:.3e}'}")
        print(f"  --> {'ALL FIELDS ZERO' if allzero else 'has non-zero fields'}")
        return fdata, keys

    first_fields, field_keys = _report("FIRST", bp_files[0])
    last_fields,  _          = _report("LAST",  bp_files[-1])

    n = len(field_keys)
    if n == 0:
        return

    x1, x2 = first_fields["x1"], first_fields["x2"]
    extent  = [x1[0], x1[-1], x2[0], x2[-1]]
    fig, axes = plt.subplots(n, 2, figsize=(14, 4 * n))
    if n == 1:
        axes = axes[None, :]
    fig.suptitle(
        f"step {first_fields['step']} (t={first_fields['time']:.2f})"
        f"  vs  step {last_fields['step']} (t={last_fields['time']:.2f})",
        fontsize=13,
    )
    for row, key in enumerate(field_keys):
        d0, d1 = first_fields[key], last_fields[key]
        vmax = max(np.abs(d0).max(), np.abs(d1).max()) or 1.0
        for col, (data, snap_label) in enumerate([(d0, "First"), (d1, "Last")]):
            ax = axes[row, col]
            im = ax.imshow(data.T, origin="lower", extent=extent, aspect="equal",
                           cmap="RdBu_r", vmin=-vmax, vmax=vmax)
            ax.set_title(f"{key}  [{snap_label}]", fontsize=10)
            ax.set_xlabel(r"$x_1\;[d_e]$", fontsize=8)
            ax.set_ylabel(r"$x_2\;[d_e]$", fontsize=8)
            ax.tick_params(labelsize=7)
            plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    out = os.path.join(FIELDS_DIR, "boundary_check.png")
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"\nSaved: {out}")


# ── Video mode ────────────────────────────────────────────────────────────────

def run_video(args):
    import glob
    bp_files = get_bp_files("fields")
    if not bp_files:
        print("No field BP files found.")
        return

    os.makedirs(FRAME_DIR, exist_ok=True)
    n = len(bp_files)

    # Pass 1: global color limits
    print(f"Pass 1/2 — computing color limits over {n} snapshots...")
    gmin = {k:  np.inf for k in PANEL_NAMES}
    gmax = {k: -np.inf for k in PANEL_NAMES}
    for i, bp in enumerate(bp_files):
        print(f"  [{i+1:3d}/{n}]", end="\r", flush=True)
        for k, arr in _extract_panels(read_fields(bp)).items():
            gmin[k] = min(gmin[k], arr.min())
            gmax[k] = max(gmax[k], arr.max())
    print()
    limits = {k: (gmin[k], gmax[k]) if gmin[k] != gmax[k] else (0.0, 1.0)
              for k in PANEL_NAMES}

    # Pass 2: render frames
    print(f"Pass 2/2 — rendering {n} frames...")
    for i, bp in enumerate(bp_files):
        print(f"  [{i+1:3d}/{n}]", end="\r", flush=True)
        fdata   = read_fields(bp)
        x1, x2  = fdata["x1"], fdata["x2"]
        t, s    = fdata["time"], fdata["step"]
        extent  = [x1[0], x1[-1], x2[0], x2[-1]]
        panels  = _extract_panels(fdata)
        out     = os.path.join(FRAME_DIR, f"frame_{i:04d}.png")
        kw      = dict(origin="lower", extent=extent, aspect="equal", cmap="plasma")

        if args.field:
            fig, ax = plt.subplots(figsize=(8, 7))
            fig.suptitle(f"{PANEL_TITLES[args.field]}  |  step={s}  |  t={t:.3f}", fontsize=13)
            vmin, vmax = limits[args.field]
            im = ax.imshow(panels[args.field].T, vmin=vmin, vmax=vmax, **kw)
            plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04).set_label(PANEL_TITLES[args.field], fontsize=10)
            ax.set_xlabel(r"$x_1\;[d_e]$", fontsize=10)
            ax.set_ylabel(r"$x_2\;[d_e]$", fontsize=10)
        else:
            fig, axes = plt.subplots(3, 3, figsize=(18, 16))
            fig.suptitle(f"Field Evolution  |  step={s}  |  t={t:.3f}", fontsize=14)
            for ax, name in zip(axes.flat, PANEL_NAMES):
                vmin, vmax = limits[name]
                im = ax.imshow(panels[name].T, vmin=vmin, vmax=vmax, **kw)
                plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04).ax.tick_params(labelsize=8)
                ax.set_title(PANEL_TITLES[name], fontsize=12)
                ax.set_xlabel(r"$x_1\;[d_e]$", fontsize=9)
                ax.set_ylabel(r"$x_2\;[d_e]$", fontsize=9)
                ax.tick_params(labelsize=8)

        fig.tight_layout()
        fig.savefig(out, dpi=args.dpi, bbox_inches="tight")
        plt.close(fig)
    print()

    # Stitch
    field_tag = f"_{args.field}" if args.field else ""
    out_video = os.path.join(PLOT_DIR, f"field_evolution{field_tag}.mp4")
    cmd = ["ffmpeg", "-y", "-framerate", str(args.fps),
           "-i", os.path.join(FRAME_DIR, "frame_%04d.png"),
           "-c:v", "mpeg4", "-q:v", "3", "-pix_fmt", "yuv420p", out_video]
    print(f"Stitching: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ffmpeg error:\n" + result.stderr)
        return
    print(f"Video saved: {out_video}")

    if not args.keep_frames:
        for f in glob.glob(os.path.join(FRAME_DIR, "frame_*.png")):
            os.remove(f)
        try:
            os.rmdir(FRAME_DIR)
        except OSError:
            pass
        print("Cleaned up intermediate frames (--keep-frames to retain).")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Field-space diagnostics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--check", action="store_true",
                        help="Compare first vs last snapshot (boundary check)")
    parser.add_argument("--video", action="store_true",
                        help="Render all snapshots into an MP4")
    parser.add_argument("--all",   action="store_true",  help="Panel: all snapshots")
    parser.add_argument("--steps", nargs="+", type=int,  help="Panel: specific step numbers")
    parser.add_argument("--index", type=int, default=None,
                        help="Panel: single snapshot by index (0=first, -1=last)")
    parser.add_argument("--fps",  type=int, default=10,  help="Video: frames/sec (default 10)")
    parser.add_argument("--dpi",  type=int, default=100, help="Video: frame DPI (default 100)")
    parser.add_argument("--field", type=str, default=None, choices=PANEL_NAMES,
                        help="Video: animate a single field")
    parser.add_argument("--keep-frames", action="store_true",
                        help="Video: keep intermediate PNGs after encoding")
    args = parser.parse_args()

    if args.check:
        run_check()
    elif args.video:
        run_video(args)
    else:
        run_panels(args)


if __name__ == "__main__":
    main()
