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
