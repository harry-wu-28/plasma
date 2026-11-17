# Two-stream instability (PIC numerics study)

Electron–electron two-stream instability in 1D with Entity's **v1.3.3** `streaming`
problem generator, used as a test case for PIC numerics: measured growth rate γ(k)
vs. cold symmetric-beam theory, and how particles per cell, grid resolution,
current filtering and shape order change the noise floor and numerical heating.

## Layout

```
pgens/streaming/pgen.hpp          verbatim copy of entity-toolkit/entity v1.3.3
                                  (tag v1.3.3 = 5bf97fd, sha256 28f7cc95...). Physics code: do not edit.
pgens/streaming_quiet/pgen.hpp    copy with evenly spaced initial positions (quiet start; user-approved)
twostream/
  scripts/build_twostream.sh      configure + build entity_s<N>.xc (N = shape order)
  scripts/bind_gpu.sh             rank -> GPU binding (copy of radiative/pp/scripts/)
  theory/chen_ee_derivation.md    Chen 6.6 algebra for two electron streams
  analysis/                       run analysis (reads simulation output)
    twostream_analysis.py         gamma(k) fit, mode histories, energy, x-t, phase space
    chen_ee.py, chen_figures.py   Chen-style theory + comparison figures
    buneman_analysis.py           electron-ion (Buneman) run
    quiet_compare.py              quiet vs random start noise comparison
  runs/baseline/                  random-start e-e run (CPU 11088180)
    inputs/twostream_baseline.toml   upstream twostream.toml, physics unchanged, I/O adjusted
    scripts/gpu_twostream.sh         1 L40S, 1 rank (cpu_twostream.sh: CPU)
  runs/quiet/                     quiet-start runs (smoke 11092712, visual 11093069)
  runs/buneman/                   electron beam through ions
  runs/scan/
    make_scan.py                     writes inputs/<tag>.toml + inputs/manifest.txt
    inputs/                          10 one-knob variants of the baseline
    scripts/gpu_twostream_scan.sh    SLURM array over manifest.txt
  results/                        deliverables
    talk/                         final-project deck (twostream_talk.pptx), content.md,
                                  build_deck.js, assets/, figures/ (random_start/ = old versions)
      scripts/                    slide/movie figure generators (write to ../figures)
    report/                       LaTeX reports (e-e, e-i) + PDFs, refs.bib, latexmkrc
```

Output goes to `/dartfs-hpc/scratch/f007hd2/twostream/<simulation.name>/`.

## Steps on Discovery

```bash
cd ~/plasma
bash twostream/scripts/build_twostream.sh                 # -> twostream/entity_s1.xc
cd twostream/runs/baseline/scripts && mkdir -p ../logs && sbatch gpu_twostream.sh
# after it finishes:
conda run -n analysis python ~/plasma/twostream/analysis/twostream_analysis.py \
    /dartfs-hpc/scratch/f007hd2/twostream/twostream_baseline \
    --out ~/plasma/twostream/runs/baseline/plots
```

Then the scan (shape-order variant needs its own binary):

```bash
SHAPE_ORDER=3 bash twostream/scripts/build_twostream.sh   # -> entity_s3.xc
cd twostream/runs/scan/scripts && mkdir -p ../logs && sbatch gpu_twostream_scan.sh
conda run -n analysis python ~/plasma/twostream/analysis/twostream_analysis.py \
    /dartfs-hpc/scratch/f007hd2/twostream/twostream_{baseline,ppc4,ppc64,ppc256} \
    --out ~/plasma/twostream/runs/scan/plots
```

### CPU (OpenMP) alternative — 2026-11-16

`gpuq` queue waits can be many hours; the baseline runs in **52 min on 16 OpenMP threads**
(job 11088180, `preemptable`, ~13 ms/step). The shared Kokkos install is CUDA-only, so the
CPU build lets Entity fetch Kokkos 4.7.1 with OpenMP (`unset Kokkos_ROOT` first — the login
shell exports it):

```bash
cd ~/plasma/radiative/entity && unset Kokkos_ROOT
export OMPI_CXX=/opt/rh/gcc-toolset-13/root/usr/bin/g++ OMPI_CC=/opt/rh/gcc-toolset-13/root/usr/bin/gcc
cmake -B build_twostream_cpu -DCMAKE_CXX_COMPILER=$OMPI_CXX -DCMAKE_C_COMPILER=$OMPI_CC \
  -Dpgen=$HOME/plasma/pgens/streaming -Dshape_order=1 -Dmpi=ON -Doutput=ON -Dprecision=single \
  -Dgpu_aware_mpi=OFF -DKokkos_ENABLE_OPENMP=ON \
  -DMPI_C_COMPILER=/optnfs/el8/openmpi/5.0/bin/mpicc -DMPI_CXX_COMPILER=/optnfs/el8/openmpi/5.0/bin/mpicxx \
  -Dadios2_ROOT=/dartfs-hpc/rc/home/5/f007gj5/ADIOS2/build \
  -DHDF5_ROOT=/dartfs-hpc/rc/home/5/f007gj5/hdf5src/build/hdf5_install
cmake --build build_twostream_cpu -j8
ln -sfn $PWD/build_twostream_cpu/src/entity.xc ~/plasma/twostream/entity_cpu.xc
cd ~/plasma/twostream/runs/baseline/scripts && mkdir -p ../logs && sbatch cpu_twostream.sh
```

`cpu_twostream.sh` writes to `/dartfs-hpc/scratch/f007hd2/twostream/cpu/` and resumes from the
latest checkpoint if preempted. Entity's verbose `.log` reaches ~1.6 GB for the baseline.

The build uses the existing `radiative/entity` checkout (v1.3.3rc). The pgen compiled
cleanly against a clean v1.3.3 checkout (CPU/OpenMP build, 2026-11-16); if it does
not compile against the rc, clone `--branch v1.3.3` and pass `ENTITY_DIR=...`.

## Physics of the baseline (all in Entity code units, c = 1)

| quantity | value |
|---|---|
| beam density (each) | n_b = 0.25 n0 (`densities[i]` is the *pair* total) |
| ω_b = √n_b / skindepth0 | 0.050 (0.0496 with the γ0³ longitudinal mass) |
| u0 = γv, v0, γ0 | 0.1, 0.0995 c, 1.005 |
| γ_max = ω_b/2 | 0.0248, at k v0 = (√3/2) ω_b → k = 0.432, λ = 14.5 |
| unstable band | k v0 < √2 ω_b → k < 0.705 (box modes m ≤ 11, L = 100) |
| λ_D (T = 1e-4) | 0.14 = 17 cells at 12288 cells |
| macroparticles | 4 per cell per species at ppc0 = 16 (49k per beam) |

## Caveat found in testing: the linear phase is short

The pgen starts beams from random (shot-noise) positions, with no seeded mode. In CPU
tests the field jumps to a thermal-fluctuation level within t ≈ 5 and the band then has
only a couple of e-folds before trapping saturates it, so γ(k) fits at upstream ppc
are noise-limited. This is itself a result for the numerics study (noise floor ∝ 1/√N
sets how much linear phase you get), but for a clean γ(k) comparison use the high-ppc
runs, and always look at `*_modes.png` before trusting the fit window
(override with `--fit-window T1 T2`). See the PR description for the test numbers.

**Baseline result (CPU run 11088180, 2026-11-16):** field energy grows exponentially over
t ≈ 40–150 and saturates at t = 188. The auto window picked t = [142, 162] (too late, mode
coupling near saturation); use `--fit-window 60 140`, which gives γ/γ_th ≈ 0.8–1.2 for the
band core m = 4–9 (edges m = 1–3, 10–11 are noise-dominated). Total-energy drift stays below
1e-5. Poisson check from the output: ∂ₓE = C ρ with C ≈ 1.04–1.06 vs expected
larmor0/skindepth0² = 1. Together with γ matching theory this is consistent with a particle
force of (q/m)E/larmor0; the separatrix drawn with it encloses the simulated vortices.

## Chen §6.6 for two electron streams (theory vs simulation)

[theory/chen_ee_derivation.md](theory/chen_ee_derivation.md) redoes Chen's Eqs. 6.19–6.35
for his Problem 6.6 (two cold electron streams, ±v₀, n₀/2 each), including the exact roots
(Re ω = 0, γ_max = ω_p/2√2 at kv₀ = √(3/8) ω_p, cutoff kv₀ = ω_p) and the eigenvector, and
compares each prediction with the baseline run. `analysis/chen_ee.py RUN --out DIR
[--window 60 140]` makes the figures (Chen Figs. 6.8/6.9, 7.11/7.12, 7.13, 7.19 for this
case, plus roots, no-fit mode growth, eigenvector) and `chen_ee_comparison.csv`.

## Illustrative figures

`analysis/chen_figures.py RUN --out DIR [--fit-window T1 T2]` (energy timeline, linear
bunching + Poisson check, phase-space snapshots, plateau; *not* reproductions of Chen's
figures despite the file name) redraws the textbook
two-stream story (Chen, *Introduction to Plasma Physics*): graphical dispersion F(ω) = 1 for
Chen's beam-through-ions case and for these symmetric beams, Re/Im ω(k) roots with the
measured γ(k), field-energy timeline, linear bunching + Poisson check, phase-space trapping
with the separatrix computed from the measured potential, and the f(uₓ, t) plateau.

## Scan (one knob changed per variant)

| tag | change | probes |
|---|---|---|
| ppc4 / ppc64 / ppc256 | ppc0 | noise floor, length of linear phase |
| filt0 / filt1 / filt16 | current_filters | short-k noise, damping of the band edge |
| res3072 / res768 / res192 | cells (total particles fixed) | λ_D/dx = 4.3, 1.1, 0.27: finite-grid heating |
| shape3 | shape order 3 (compile-time) | aliasing / heating vs order 1 |

Numerical heating shows as drift in total energy, `T00 + (σ0/2)(E² + B²)` from the
stats file (`*_energy.png`). Note `T00` is printed with 6 significant figures, so
relative drifts below ~1e-5 are not resolved.

## Buneman run: exact cold-fluid numbers (2026-11-16)

Solving Chen Eq. 6.30, `1 = ω_pi²/ω² + ω_pe²/(ω − k v0)²`, numerically for M/m = 1836:
γ_max = **0.0544 ω_pe** at k v0 = 1.006 ω_pe, Re ω = 0.036 ω_pe; cutoff k v0 =
(1 + (m/M)^{1/3})^{3/2} ω_pe = 1.125 ω_pe. The comment in `runs/buneman/inputs/buneman.toml`
quotes the small-ω approximation (√3/2)(m/2M)^{1/3} ω_pe = 0.0561 ω_pe, which is 3% high.
With ω_pe = 0.1 and L = 100: box mode m = 16 sits on the peak, m ≤ 17 are unstable, the
e-folding time is ≈184, and the run (t = 4000) covers ≈22 e-folds. The report is
`results/report/twostream_electron_ion.tex`.

**Setup (`runs/buneman/`).** The input uses the unmodified streaming pgen: species 1 = e⁻
(u0 = 0.1), 2 = mobile ions (M/m = 1836), 3 = rigid return current (m = 1e8, +q, u0 = 0.1),
and 4 = its immobile −q background (pusher None). Species 3/4 are there because Chen's
theory is electrostatic (no k = 0 field), but Entity advances E with Ampère's law, and in
1D the uniform beam current would build a uniform Ex (dEx/dt = −Jx). That would make the
whole beam oscillate at ω_pe with amplitude v0. With species 3, mean Ex stays at ~1e-3 in
the linear phase and ~1e-2 at saturation, against J0/ω_pe ≈ 1 uncompensated. Cost on 32
OpenMP threads is 22 ms/step, ~85% of it particle deposit and push, since three species
move: ~5× the particles of the e-e baseline.

**Result (CPU job 11091422, 2026-11-16, cancelled by the user at t ≈ 936 after
saturation).** Output is in `/dartfs-hpc/scratch/f007hd2/twostream/cpu/buneman` and the plots
are in `runs/buneman/plots/` (`analysis/buneman_analysis.py RUN --out DIR --window 400 700`).
- *What matches Chen:* from t ≈ 300 to saturation the field spectrum is dominated by
  m = 13–17 (k v0/ω_pe = 0.82–1.07), 10× the median mode, i.e. the instability picks Chen's
  wavelength. m = 16 (the theoretical peak) grows from 0.069 to 0.395 over t = 400–700 and
  saturates at t ≈ 750.
- *What does not give a clean γ(k):* noise grows roughly linearly in time (band rms
  0.013 → 0.09 over t = 12–190). It comes from the beam resonantly sweeping past frozen ion
  positions at k v0 ≈ ω_pe, so only ~1.6 e-folds of exponential growth separate the noise
  from saturation (window t = 400–700 = 1.63 e-folds at γ_max). With the e-e rule (≥ 1.5
  theoretical e-folds in the window) only m = 16 counts: γ = 0.0061 ± 0.0001 vs Chen
  0.0054 (1.12×). Over the same window the median mode, and the stable modes m = 18–24
  (γ_th = 0), also grow at ~0.0045–0.011, so the band growth rate cannot be separated from
  broadband growth of the spectrum. Not presentable as a γ(k) comparison.
- *To improve:* fixing this needs a quieter start or many more particles per cell (noise
  ∝ 1/√N), or a lighter ion (M/m = 100 grows 2.6× faster). Running longer does not help:
  everything after t ≈ 750 is saturation.

## Numerics actually used: Boris + zigzag + first-order shape (verified 2026-11-16)

From the baseline run's own report (`twostream_baseline.info`: `Deposit: zigzag`,
`Pusher: boris` for the beams) and the Entity source: the beams use the default Boris pusher
(`defaults::em_pusher`), current is deposited with the charge-conserving zigzag scheme
(Umeda et al. 2003), and fields are interpolated with first-order (linear, cloud-in-cell)
weights (`getInterpFlds<0>`).

**`-Dshape_order` is ignored for the zigzag deposit.** `cmake/config.cmake` only passes
`-DSHAPE_ORDER` when `deposit=esirkepov`; with zigzag (the default) `SHAPE_ORDER` stays 0.
So `SHAPE_ORDER=3 bash twostream/scripts/build_twostream.sh` builds the *same* first-order
code, and the `shape3` scan variant is not a shape-order test. A real higher-order build
needs `-Ddeposit=esirkepov -Dshape_order=3`.

## Growth-rate precision and why it is limited (2026-11-16)

**Honest per-wave uncertainty.** A single straight-line fit of ln|E_m| over t = 60–140 gives
error bars of ~0.01 ω_p, which hide the real uncertainty. Fitting the same mode over 40-unit
windows sliding across t = 40–160 (before saturation at t ≈ 180) moves the rate by ±0.06–0.19
ω_p (25–50% of theory). `results/talk/scripts/slide_figures.py` plots the median over those windows with
the window spread as the error bar. For the resolved waves m = 4–9 the median/theory ratios
are 0.85, 0.96, 0.93, 1.01, 1.23, 0.98, so the **mean ratio is 0.99 ± 0.16** (± from
propagating each wave's window spread; the six ratios alone give SE 0.05, but the windows
overlap and the waves share one noise realization, so quote the conservative value). Fastest
wave m = 7: 0.36 ± 0.12 ω_p vs theory 0.354. The earlier "0.352 vs 0.354" was window luck.
m = 1–3 are uninformative (spread ±0.27–0.37); m = 11 sits high because it is driven by the
strong modes (m = 12, with zero theoretical growth, grows as fast).

**Why: only ~3.8 e-folds exist.** The m = 7 density ripple starts at the shot-noise floor
δn/n_b ≈ 0.011 (median over t = 10–50) and saturates at ≈ 0.5, so ln(0.5/0.011) ≈ 3.8 e-folds
from noise to saturation, and noise-driven wobble dominates any short single-mode fit. More
particles help only logarithmically (noise ∝ 1/√N: 4× ppc ≈ +0.7 e-fold, 16× ≈ +1.4).

**The streaming pgen cannot seed a wave from the TOML.** `pgens/streaming/pgen.hpp` reads only
`setup.drifts_in_{x,y,z}`, `densities`, `temperatures`, `Bmag/Btheta/Bphi` and injects with
`arch::InjectUniformMaxwellians` (uniform density, no spatial structure); the only field
initializer is a uniform B. A seeded (ideally eigenvector-loaded) run needs a new or edited
pgen, which is physics code (user's permission). Seeding would not add e-folds; it would make
the seeded wave dominate its Fourier amplitude from t = 0 (estimated ~5–10% single-wave
precision at baseline ppc, runtime ~300 is enough).

**Entity's random seed is hard-coded.** `src/global/utils/numeric.h` defines
`constant::RandomSeed`, used by `src/framework/domain/domain.h` for the random pool; there is
no TOML option. Reruns at the same ppc reproduce the same noise, so ensemble averaging over
noise realizations also needs a code change.

## Quiet start: evenly spaced initial positions (2026-11-17)

`pgens/streaming_quiet/pgen.hpp` (user-approved physics change; diff vs `pgens/streaming` in
`quiet_start_draft/pgen.diff`) replaces the random positions of `InjectUniformMaxwellians`
with x = i + (j + ½)/npc inside every cell (npc = ppc0·density/2 must be an integer); both
species of a pair share positions, so ρ = 0 exactly per cell at t = 0. Velocities are the
same random Maxwellians. 1D only. Built in `radiative/entity/build_twostream_quiet_cpu`
(symlink `entity_quiet_cpu.xc`).

Smoke test (job 11092712: baseline grid and ppc0 = 16, to 21/ω_p, 13 min on 32 threads,
9.6 ms/step; `analysis/quiet_compare.py`, plot `runs/quiet/plots/quiet_vs_random_noise.png`):
the seed the instability amplifies is 15–64× lower per mode for m = 4–9 (geometric mean 28×
= **+3.3 clean e-folds**; the band energy reaches a common level 9.4/ω_p later, giving the same
+3.3). The random thermal velocities do decorrelate the ordering (|δn_m|/n_b quiet/random is 70×
lower at t ≤ 1/ω_p and 29× at 4–6/ω_p), but most of the gain survives. Saturation moves from
12.6 to ~22–25/ω_p. Visual run: `runs/quiet/inputs/quiet_visual.toml` (ppc0 = 64, log_level
WARNING), `runs/quiet/scripts/cpu_quiet_visual.sh` (1 node × 1 rank × 32 threads, preemptable;
the account's 32-CPU cap rules out multi-node), job 11093069, output in
`/dartfs-hpc/scratch/f007hd2/twostream/quiet/quiet_visual/`.

**Full quiet run (job 11093069, ppc0 = 64; linear phase from completed snapshots to 34/ω_p,
2026-11-17).** Fit window t = 140–320 (9.8–22.5/ω_p), saturation (first field-energy peak) at
26.8/ω_p. m = 7: 0.339 ± 0.014 ω_p vs 0.354; m = 4–9 mean ratio 0.96 ± 0.04 (the ~4% shortfall
is plausibly the beam temperature, v_th = 0.1 v0, not separately computed); median spread 9%;
4.2 clean e-folds (×70); |Re ω| ≤ 0.024 ω_p; slow growers m = 1–3, 11. Seed vs random start:
48× (+3.9 e-folds) = quiet start 28× (smoke vs random, both ppc0 = 16) × 4× particles 1.8×
(full vs smoke, both quiet; ≈ √4, as expected if the residual seed is thermal-velocity noise).
Completed in 1 h 30 min 48 s (1 node, 1 rank × 32 threads, 22.2 ms/step average, 245,760 steps,
1.3 GB output in `/dartfs-hpc/scratch/f007hd2/twostream/quiet/quiet_visual/`).
