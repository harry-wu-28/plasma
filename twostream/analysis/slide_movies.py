#!/usr/bin/env python3
"""Talk animation and space-time figures for the e-e two-stream run (same style as
slide_figures.py).

  phase_space.mp4 / .gif       x-v phase space, beam 1 blue / beam 2 red, time counter
  spacetime_Ex.png             E_x(x, t), linear color
  spacetime_Ex_normalized.png  same, each time row divided by its own rms

Usage:
    conda run -n analysis python twostream/analysis/slide_movies.py \
        /dartfs-hpc/scratch/f007hd2/twostream/cpu/twostream_baseline --out talk/figures
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slide_figures as sf  # noqa: E402  (sets the shared rcParams)
import chen_ee as ce  # noqa: E402
import twostream_analysis as ta  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import animation  # noqa: E402
from adios2 import FileReader  # noqa: E402


def frame_list(ptimes, wp, t_full, stride_late):
    order = np.argsort(ptimes)
    early = [i for i in order if ptimes[i] * wp <= t_full]
    late = [i for i in order if ptimes[i] * wp > t_full][::stride_late]
    return early + late


def movie(pfiles, ptimes, wp, frames, out, fps=24, dpi=120, gif_every=2, gif_fps=12, gif_dpi=60):
    fig, ax = plt.subplots(figsize=sf.SIZE)
    lines = {s: ax.plot([], [], ".", color=c, ms=1.6, alpha=0.6)[0] for s, c in ((1, sf.BEAM1), (3, sf.BEAM2))}
    ax.set_xlim(0, 100 * wp)
    ax.set_ylim(-0.25, 0.25)
    ax.set_xlabel("position (c/ω$_p$)")
    ax.set_ylabel("velocity (c)")
    h = [plt.Line2D([], [], marker="o", ls="", color=c, ms=9) for c in (sf.BEAM1, sf.BEAM2)]
    ax.legend(h, ["beam 1 (→)", "beam 2 (←)"], loc="lower left", fontsize=14, framealpha=0.9)
    clock = ax.text(0.98, 0.96, "", transform=ax.transAxes, ha="right", va="top", fontsize=24,
                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.85))
    fig.tight_layout()

    def draw(i):
        with FileReader(str(pfiles[i])) as f:
            t = float(f.read("Time"))
            for s in (1, 3):
                lines[s].set_data(np.asarray(f.read(f"pX1_{s}")) * wp,
                                  sf.speed(np.asarray(f.read(f"pU1_{s}"))))
        clock.set_text(f"t = {t*wp:4.1f} / ω$_p$")
        return list(lines.values()) + [clock]

    mp4 = out / "phase_space.mp4"
    w = animation.FFMpegWriter(fps=fps, codec="libx264", bitrate=-1,
                               extra_args=["-pix_fmt", "yuv420p", "-crf", "23", "-preset", "medium",
                                           "-movflags", "+faststart"])
    with w.saving(fig, str(mp4), dpi=dpi):
        for i in frames:
            draw(i)
            w.grab_frame()
    gif = out / "phase_space.gif"
    gw = animation.PillowWriter(fps=gif_fps)
    with gw.saving(fig, str(gif), dpi=gif_dpi):
        for i in frames[::gif_every]:
            draw(i)
            gw.grab_frame()
    plt.close(fig)
    for p, n, r in ((mp4, len(frames), fps), (gif, len(frames[::gif_every]), gif_fps)):
        print(f"wrote {p}  {p.stat().st_size/1e6:.1f} MB  {n} frames @ {r} fps = {n/r:.1f} s")


def spacetime(ffiles, wp, t_max, t_sat, out, block=12):
    t, E, x = ta.read_field_series(ffiles, "fE1")
    keep = t * wp <= t_max
    t, E = t[keep], E[keep]
    nx = E.shape[1] // block * block
    E = E[:, :nx].reshape(len(t), -1, block).mean(axis=2)  # display resampling only
    xb = x[:nx].reshape(-1, block).mean(axis=1)
    ext = (xb[0] * wp, xb[-1] * wp, t[0] * wp, t[-1] * wp)
    for name, data, lim, label in (
        ("spacetime_Ex.png", E, np.percentile(np.abs(E), 99.5), "electric field $E_x$ (code units)"),
        ("spacetime_Ex_normalized.png", E / np.sqrt((E**2).mean(axis=1, keepdims=True)), 2.5,
         "$E_x$ ÷ its rms at that time"),
    ):
        fig, ax = plt.subplots(figsize=sf.SIZE)
        im = ax.imshow(data, origin="lower", aspect="auto", extent=ext, cmap="RdBu_r",
                       vmin=-lim, vmax=lim, interpolation="nearest")
        ax.axhline(t_sat * wp, color="k", ls="--", lw=1.2)
        ax.text(ext[1] - 0.05, t_sat * wp + 0.25, "growth stops (saturation)", ha="right", va="bottom",
                fontsize=16, bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=2))
        ax.set_xlabel("position (c/ω$_p$)")
        ax.set_ylabel("time (1/ω$_p$)")
        cb = fig.colorbar(im, ax=ax, pad=0.02)
        cb.set_label(label, fontsize=16)
        fig.tight_layout()
        sf.save(fig, out, name)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--t-full", type=float, default=20.0, help="every snapshot up to this time [1/wp]")
    ap.add_argument("--stride-late", type=int, default=3)
    ap.add_argument("--no-movie", action="store_true", help="only redraw the space-time figures")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    run = Path(a.run)

    ffiles = ta.field_files(run)
    cfg = ta.read_config(ffiles[0])
    th = ta.Theory(cfg)
    wp = ce.ChenEE(th, cfg).wp
    pfiles = sorted((run / "particles").glob("particles.*.bp"))
    ptimes = ce.file_times(pfiles)
    dts = np.diff(np.sort(ptimes))
    print(f"particle snapshots: {len(pfiles)}, spacing {np.median(dts):.2f} code = {np.median(dts)*wp:.3f}/wp; "
          f"{1/th.gamma_max/np.median(dts):.0f} frames per e-folding of the fastest mode")

    t, Ek, _, _ = ce.modes(ffiles, "fE1")
    k = 2 * np.pi * np.arange(Ek.shape[1]) / (float(cfg["grid.extent"][1]) - float(cfg["grid.extent"][0]))
    band = np.where((k > 0) & (k < th.k_cut))[0]
    W = (np.abs(Ek[:, band]) ** 2).sum(axis=1)
    t_sat = float(t[int(np.argmax(np.where(t * wp <= a.t_full, W, -1)))])
    print(f"saturation t = {t_sat:.0f} code = {t_sat*wp:.1f}/wp")

    if not a.no_movie:
        movie(pfiles, ptimes, wp, frame_list(ptimes, wp, a.t_full, a.stride_late), a.out)
    spacetime(ffiles, wp, a.t_full, t_sat, a.out)


if __name__ == "__main__":
    main()
