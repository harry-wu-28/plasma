#!/usr/bin/env python
"""Complete overview of one Entity run directory (pp / pp_IC setups).

Usage:
  conda run -n analysis python overview.py /dartfs-hpc/scratch/f007hd2/radiative/pp/testPP

Produces, under radiative/pp/runs/<run_name>/plots/ when that run dir
exists, else <this analysis dir>/plots/<run_name>/ (or --out):
  run_summary.txt       run configuration digest + data-health checks
  census.png            particle count per species vs time
  energetics.png        total energy and mean gamma per species vs time
  particle_spectra.png  dN/dln(eps) per species at several epochs
                        (built from raw momenta — pp weights are zero)
  builtin_spectra.png   Entity's [output.spectra] histograms (skipped if all zero)
  density_maps.png      2D particle density maps per species at the last step
  fields.png            nonzero field/moment maps at the last step (skipped if all zero)

Safe to run while the job is still writing: unreadable (mid-write) steps are
skipped and listed in the summary. Counts/energies are multiplied by
output.particles.stride and unweighted (pp particle weights are identically
zero — see zero-weight-photon-injection-report.md).

All quantities are in Entity code units: energies/gamma in m_e c^2,
lengths in c/omega_p, time in 1/omega_p (larmor0 = skindepth0 = 1).
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, TwoSlopeNorm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bp_reader import MASSLESS, RunReader, lorentz_gamma
import viz_style as vs


def log(msg):
    print(msg, flush=True)


def valid_particle_steps(run):
    """Steps whose particle file opens cleanly (job may be mid-write)."""
    good, bad = [], []
    for step in sorted(run.steps["particles"]):
        try:
            run.particle_counts(step)
            good.append(step)
        except Exception:
            bad.append(step)
    return good, bad


def collect_timeseries(run, steps, every, with_energy=True):
    """time, counts[s], energy[s], mean_gamma[s] arrays over output steps."""
    steps = steps[::every] if every > 1 else steps
    species = range(1, run.nspec + 1)
    t = []
    counts = {s: [] for s in species}
    energy = {s: [] for s in species}
    mean_g = {s: [] for s in species}
    for k, step in enumerate(steps):
        time, n = run.particle_counts(step)
        t.append(time)
        for s in species:
            counts[s].append(n[s])
            if not with_energy:
                continue
            if n[s] == 0:
                energy[s].append(0.0)
                mean_g[s].append(np.nan)
            else:
                g = run.particle_gammas(step, s)
                energy[s].append(float(g.sum()))
                mean_g[s].append(float(g.mean()))
        log(f"  step {step:>8d}  t={time:8.1f}  " +
            " ".join(f"N{s}={counts[s][-1]}" for s in species))
    to_np = lambda d: {s: np.asarray(v, dtype=float) for s, v in d.items()}
    return np.asarray(t), to_np(counts), to_np(energy), to_np(mean_g)


def plot_census(run, t, counts, out):
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    present, labels = [], []
    for s, n in counts.items():
        if n.max() == 0:
            continue
        est = n * run.stride
        ax.plot(t, est, color=vs.SPECIES_COLOR[s], label=run.species_label(s))
        labels.append((t[-1], est[-1], run.species_label(s), vs.SPECIES_COLOR[s]))
        present.append(s)
    ax.set_yscale("log")
    vs.direct_labels(ax, labels)
    ax.set_xlabel(r"$t\ [\omega_p^{-1}]$")
    ax.set_ylabel(f"particle count (stride-{run.stride} corrected)")
    ax.set_title(f"{run.run_dir.name}: species census")
    ax.legend(loc="lower right")
    ax.grid(axis="y")
    fig.savefig(out / "census.png")
    plt.close(fig)
    return present


def plot_energetics(run, t, energy, mean_g, out):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    total = np.zeros_like(t)
    labels1 = []
    for s, e in energy.items():
        est = e * run.stride
        total += est
        if e.max() == 0:
            continue
        ax1.plot(t, est, color=vs.SPECIES_COLOR[s], label=run.species_label(s))
        labels1.append((t[-1], est[-1], run.species_label(s), vs.SPECIES_COLOR[s]))
    ax1.plot(t, total, color=vs.INK, ls="--", lw=1.4, label="all species")
    ax1.set_yscale("log")
    vs.direct_labels(ax1, labels1)
    ax1.set_xlabel(r"$t\ [\omega_p^{-1}]$")
    ax1.set_ylabel(r"total energy $\Sigma\gamma\ [m_e c^2]$ (stride-corrected)")
    ax1.set_title("energy per species")
    ax1.legend(loc="lower right")

    labels2 = []
    for s, g in mean_g.items():
        if np.all(np.isnan(g)):
            continue
        ax2.plot(t, g, color=vs.SPECIES_COLOR[s], label=run.species_label(s))
        last = np.where(~np.isnan(g))[0][-1]
        labels2.append((t[last], g[last], run.species_label(s), vs.SPECIES_COLOR[s]))
    ax2.set_yscale("log")
    vs.direct_labels(ax2, labels2)
    ax2.set_xlabel(r"$t\ [\omega_p^{-1}]$")
    ax2.set_ylabel(r"$\langle\gamma\rangle$  ($\gamma=|u|$ for photons)")
    ax2.set_title("mean Lorentz factor / photon energy")
    ax2.legend(loc="lower left")
    fig.suptitle(f"{run.run_dir.name}: energetics", fontsize=11)
    fig.savefig(out / "energetics.png")
    plt.close(fig)


def spectra_bins(run):
    e_min = float(run.attrs.get("output.spectra.e_min", 1e-3))
    e_max = float(run.attrs.get("output.spectra.e_max", 1e3))
    n_bins = int(run.attrs.get("output.spectra.n_bins", 200))
    return np.geomspace(e_min, e_max, n_bins + 1)


def plot_particle_spectra(run, steps, present, epochs, out):
    picks = sorted(set(np.linspace(0, len(steps) - 1, epochs).round().astype(int)))
    edges = spectra_bins(run)
    centers = np.sqrt(edges[:-1] * edges[1:])
    dln = np.log(edges[1:] / edges[:-1])
    colors = vs.epoch_colors(len(picks))

    fig, axes = plt.subplots(1, len(present), figsize=(4.0 * len(present), 3.6),
                             layout="constrained", squeeze=False)
    for ax, s in zip(axes[0], present):
        occupied = np.zeros(len(centers), dtype=bool)
        for c, i in zip(colors, picks):
            step = steps[i]
            g = run.particle_gammas(step, s)
            if g.size == 0:
                continue
            time, _ = run.particle_counts(step)
            h, _ = np.histogram(g, bins=edges)
            occupied |= h > 0
            # steps, not point-lines: a near-monoenergetic population fills
            # a single bin, which a plain plot() renders as nothing
            ax.stairs(h * run.stride / dln, edges, color=c, lw=1.8,
                      baseline=None, label=f"t={time:.0f}")
        ax.set_xscale("log")
        ax.set_yscale("log")
        if occupied.any():
            lo, hi = np.where(occupied)[0][[0, -1]]
            ax.set_xlim(edges[lo] / 2, edges[hi + 1] * 2)
        if s in MASSLESS:
            ax.set_xlabel(r"$\epsilon\ [m_e c^2]$")
            ax.set_ylabel(r"$dN/d\ln\epsilon$ (stride-corrected)")
        else:
            ax.set_xlabel(r"$\gamma$")
            ax.set_ylabel(r"$dN/d\ln\gamma$ (stride-corrected)")
        ax.set_title(run.species_label(s), color=vs.SPECIES_COLOR[s], fontweight="bold")
        ax.grid(which="both", axis="both", alpha=0.5)
    axes[0][-1].legend(title=r"$t\ [\omega_p^{-1}]$", loc="best")
    fig.suptitle(f"{run.run_dir.name}: particle spectra (unweighted, from raw momenta)",
                 fontsize=11)
    fig.savefig(out / "particle_spectra.png")
    plt.close(fig)


def plot_builtin_spectra(run, out):
    """Entity [output.spectra] histograms; returns False if all-zero."""
    steps = sorted(run.steps["spectra"])
    if not steps:
        return None
    picks = sorted(set(np.linspace(0, len(steps) - 1, 4).round().astype(int)))
    data = []
    for i in picks:
        try:
            data.append(run.spectrum(steps[i]))
        except Exception:
            continue
    if not data or all(c is None or not np.any(c)
                       for _, _, cnt in data for c in cnt.values()):
        return False
    fig, ax = plt.subplots(figsize=(6, 4), layout="constrained")
    colors = vs.epoch_colors(len(data))
    for c, (time, edges, cnt) in zip(colors, data):
        centers = np.sqrt(edges[:-1] * edges[1:])
        for s, y in cnt.items():
            if y is None or not np.any(y):
                continue
            m = y > 0
            ax.plot(centers[m], y[m], color=vs.SPECIES_COLOR[s], alpha=0.9,
                    label=f"{run.species_label(s)} t={time:.0f}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"$\epsilon\ [m_e c^2]$")
    ax.set_ylabel("weighted count per bin")
    ax.set_title(f"{run.run_dir.name}: built-in spectra")
    ax.legend()
    fig.savefig(out / "builtin_spectra.png")
    plt.close(fig)
    return True


def plot_density_maps(run, step, present, map_bins, out):
    ext = run.attrs.get("grid.extent", [-1, 1, -1, 1])
    x1r, x2r = (ext[0], ext[1]), (ext[2], ext[3])
    time, _ = run.particle_counts(step)
    fig, axes = plt.subplots(1, len(present), figsize=(4.2 * len(present), 4.0),
                             layout="constrained", squeeze=False)
    for ax, s in zip(axes[0], present):
        p = run.particles(step, s, quantities=("X1", "X2"))
        h, xe, ye = np.histogram2d(p["X1"], p["X2"], bins=map_bins,
                                   range=[x1r, x2r])
        vmax = max(h.max(), 1.0)
        pc = ax.pcolormesh(xe, ye, h.T, cmap=vs.SEQ_CMAP,
                           norm=LogNorm(vmin=1.0, vmax=vmax), rasterized=True)
        ax.set_aspect("equal")
        ax.set_xlabel(r"$x_1\ [c/\omega_p]$")
        ax.set_ylabel(r"$x_2\ [c/\omega_p]$")
        ax.set_title(f"{run.species_label(s)}  (N={p['X1'].size * run.stride:.3g})",
                     color=vs.SPECIES_COLOR[s], fontweight="bold")
        ax.grid(False)
        fig.colorbar(pc, ax=ax, shrink=0.8,
                     label=f"count per cell (stride-{run.stride} sample)")
    fig.suptitle(f"{run.run_dir.name}: particle density at t={time:.0f}"
                 r"$\ \omega_p^{-1}$", fontsize=11)
    fig.savefig(out / "density_maps.png")
    plt.close(fig)


def plot_fields(run, out, max_panels=12):
    """Maps of nonzero field variables at the last readable fields step.
    Returns (plotted_names, all_zero_names) or None if unreadable."""
    steps = sorted(run.steps["fields"])
    for step in reversed(steps):
        try:
            names = run.field_names(step)
            data = run.fields(step, names)
            break
        except Exception:
            continue
    else:
        return None
    nonzero = [n for n in names if np.any(data[n])]
    zero = [n for n in names if n not in nonzero]
    if nonzero:
        sel = nonzero[:max_panels]
        ncol = min(4, len(sel))
        nrow = int(np.ceil(len(sel) / ncol))
        fig, axes = plt.subplots(nrow, ncol, figsize=(3.8 * ncol, 3.6 * nrow),
                                 layout="constrained", squeeze=False)
        for ax, n in zip(axes.flat, sel):
            arr = data[n]  # stored [x2, x1]
            if n.startswith("fN"):  # non-negative density -> sequential
                pc = ax.pcolormesh(data["X1e"], data["X2e"], arr,
                                   cmap=vs.SEQ_CMAP, rasterized=True)
            else:  # signed -> diverging, symmetric about 0
                a = float(np.abs(arr).max())
                pc = ax.pcolormesh(data["X1e"], data["X2e"], arr, cmap=vs.DIV_CMAP,
                                   norm=TwoSlopeNorm(0, -a, a), rasterized=True)
            ax.set_aspect("equal")
            ax.set_title(f"{n} [code units]")
            ax.grid(False)
            fig.colorbar(pc, ax=ax, shrink=0.8)
        for ax in axes.flat[len(sel):]:
            ax.set_visible(False)
        fig.suptitle(f"{run.run_dir.name}: fields at t={data['Time']:.0f}"
                     r"$\ \omega_p^{-1}$", fontsize=11)
        fig.savefig(out / "fields.png")
        plt.close(fig)
    return nonzero, zero


def write_summary(run, out, info):
    a = run.attrs
    lines = [
        f"Run overview: {run.run_dir}",
        f"generated by {Path(__file__).name}",
        "",
        "--- configuration (from BP attributes) ---",
        f"simulation.name      = {a.get('simulation.name')}",
        f"engine / metric      = {a.get('simulation.engine')} / {a.get('grid.metric.metric')}",
        f"resolution           = {a.get('grid.resolution')}",
        f"extent [c/wp]        = {a.get('grid.extent')}",
        f"dt [1/wp]            = {a.get('algorithms.timestep.dt')}",
        f"runtime [1/wp]       = {a.get('simulation.runtime')}",
        f"ppc0 / n0            = {a.get('particles.ppc0')} / {a.get('scales.n0')}",
        f"output interval_time = {a.get('output.interval_time')}, particle stride = {run.stride}",
        f"spectra bins         = {a.get('output.spectra.n_bins')} log bins, "
        f"[{a.get('output.spectra.e_min')}, {a.get('output.spectra.e_max')}] m_e c^2",
        "",
        "--- [setup] physics ---",
    ]
    lines += [f"{k:22s} = {v}" for k, v in sorted(a.items()) if k.startswith("setup.")]
    lines += ["", "--- data present ---"]
    for kind in ("fields", "particles", "spectra"):
        st = sorted(run.steps[kind])
        lines.append(f"{kind:9s}: {len(st)} steps"
                     + (f", {st[0]}..{st[-1]}" if st else ""))
    lines += ["", "--- census (stride-corrected) ---"]
    t, counts = info["t"], info["counts"]
    lines.append(f"first output t={t[0]:.1f}, last readable t={t[-1]:.1f}")
    for s in sorted(counts):
        n = counts[s]
        lines.append(f"  {run.species_label(s):7s} (sp {s}): "
                     f"N(first)={int(n[0]) * run.stride:>12d}  "
                     f"N(last)={int(n[-1]) * run.stride:>12d}")
    lines += ["", "--- data-health checks ---"]
    lines += info["health"]
    (out / "run_summary.txt").write_text("\n".join(lines) + "\n")
    log("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", help="Entity run dir on scratch (contains fields/ particles/ spectra/)")
    ap.add_argument("--out", default=None,
                    help="output dir (default: runs/<run_name>/plots if that "
                         "run dir exists, else <analysis>/plots/<run_name>)")
    ap.add_argument("--epochs", type=int, default=4, help="number of times for spectra (default 4)")
    ap.add_argument("--every", type=int, default=1, help="use every Nth step for time series")
    ap.add_argument("--map-bins", type=int, default=256, help="density-map resolution")
    ap.add_argument("--skip-energetics", action="store_true",
                    help="census only (skips reading momenta for every step)")
    args = ap.parse_args()

    run = RunReader(args.run_dir)
    # default output: the run's own plots/ dir under radiative/pp/runs/ if
    # that run dir exists; otherwise <analysis>/plots/<run_name> (e.g. pp_IC)
    per_run = (Path(__file__).resolve().parents[2] / "radiative" / "pp" /
               "runs" / run.run_dir.name)
    out = Path(args.out) if args.out else (
        per_run / "plots" if per_run.is_dir()
        else Path(__file__).resolve().parents[1] / "plots" / run.run_dir.name)
    out.mkdir(parents=True, exist_ok=True)
    vs.apply_style()
    log(f"run: {run.run_dir}  ->  {out}")

    steps, bad_steps = valid_particle_steps(run)
    if not steps:
        sys.exit("no readable particle steps")
    log(f"readable particle steps: {len(steps)}"
        + (f" (skipped mid-write/corrupt: {bad_steps})" if bad_steps else ""))

    log("time series" + (" (census only)" if args.skip_energetics else " + energetics"))
    t, counts, energy, mean_g = collect_timeseries(
        run, steps, args.every, with_energy=not args.skip_energetics)

    present = plot_census(run, t, counts, out)
    log(f"wrote census.png (species present: {present})")
    if not args.skip_energetics:
        plot_energetics(run, t, energy, mean_g, out)
        log("wrote energetics.png")

    plot_particle_spectra(run, steps[::args.every], present, args.epochs, out)
    log("wrote particle_spectra.png")

    builtin = plot_builtin_spectra(run, out)
    log("wrote builtin_spectra.png" if builtin
        else "built-in spectra all zero or absent — skipped (pp zero-weight issue)")

    plot_density_maps(run, steps[-1], present, args.map_bins, out)
    log("wrote density_maps.png")

    fres = plot_fields(run, out)
    if fres is None:
        log("no readable fields step")
        f_note = "fields: no readable step"
    else:
        nonzero, zero = fres
        f_note = (f"fields: {len(nonzero)} nonzero vars plotted"
                  if nonzero else f"fields: ALL {len(zero)} variables identically zero")
        log(f_note)

    # health checks
    wmax = 0.0
    for s in sorted(present, key=lambda s: counts[s][-1], reverse=True)[:1]:
        w = run.particles(steps[-1], s, quantities=("W",))["W"]
        wmax = float(w.max()) if w.size else 0.0
    health = [
        f"particle weights: {'ALL ZERO (known pp pgen issue; all plots here are unweighted)' if wmax == 0 else f'nonzero (max {wmax:g})'}",
        f"built-in spectra: {'nonzero' if builtin else 'ALL ZERO or absent (weight bug for pp runs)'}",
        f_note,
        f"stats output    : {'enabled' if run.attrs.get('output.stats.enable') else 'disabled ([output.stats] enable=false; *_stats.csv has headers only)'}",
        f"unreadable steps: {bad_steps if bad_steps else 'none'}"
        + ("  (job may still be writing)" if bad_steps else ""),
    ]
    write_summary(run, out, {"t": t, "counts": counts, "health": health})
    log(f"\ndone -> {out}")


if __name__ == "__main__":
    main()
