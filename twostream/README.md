# Two-stream instability (PIC numerics study)

Electron–electron two-stream instability in 1D with Entity's **v1.3.3** `streaming`
problem generator, used as a test case for PIC numerics: measured growth rate γ(k)
vs. cold symmetric-beam theory, and how particles per cell, grid resolution,
current filtering and shape order change the noise floor and numerical heating.

## Layout

```
pgens/streaming/pgen.hpp          verbatim copy of entity-toolkit/entity v1.3.3
                                  (tag v1.3.3 = 5bf97fd, sha256 28f7cc95...). Physics code: do not edit.
twostream/
  scripts/build_twostream.sh      configure + build entity_s<N>.xc (N = shape order)
  scripts/bind_gpu.sh             rank -> GPU binding (copy of radiative/pp/scripts/)
  analysis/twostream_analysis.py  gamma(k) fit, mode histories, energy, x-t, phase space
  runs/baseline/
    inputs/twostream_baseline.toml   upstream twostream.toml, physics unchanged, I/O adjusted
    scripts/gpu_twostream.sh         1 L40S, 1 rank
  runs/scan/
    make_scan.py                     writes inputs/<tag>.toml + inputs/manifest.txt
    inputs/                          10 one-knob variants of the baseline
    scripts/gpu_twostream_scan.sh    SLURM array over manifest.txt
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
`paper/twostream_electron_ion.tex`.

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
