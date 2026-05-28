# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This workspace contains two Entity PIC simulation projects, each with their own copy of the Entity codebase (`entity/`) and a simulation run directory:

- `radiative/` — QED pair-cascade study (IC + Breit-Wheeler pair production on a 2D Minkowski grid, field solver off). Active pgen: `pgens/pp/pgen.hpp`.
- `turb2d/` — 2D plasma turbulence study (SRPIC on 2D Minkowski grid, field solver on). Active pgen: `pgens/turbulence/`.

**Entity** is a C++17 relativistic PIC code using Kokkos (GPU/CPU portability), MPI (multi-node), and ADIOS2 (HDF5/BP5 output). The compiled binary is named `entity.xc`.

## Building

Entity uses CMake. The build directory lives at `<project>/entity/build/`. Key configure options:

| CMake flag | Purpose | Common values |
|---|---|---|
| `-Dpgen=<path>` | Problem generator (name or absolute path to dir containing `pgen.hpp`) | `turbulence`, `/abs/path/to/pp` |
| `-Dmpi=ON` | Enable MPI | `ON` / `OFF` |
| `-Doutput=ON` | Enable ADIOS2 output | `ON` / `OFF` |
| `-Dprecision=single` | Float precision | `single` / `double` |
| `-DDEBUG=ON` | Debug build | `ON` / `OFF` |
| `-DKokkos_ROOT=` | Path to pre-built Kokkos | see below |
| `-Dadios2_ROOT=` | Path to pre-built ADIOS2 | see below |

Shared library paths on this cluster (owned by f007gj5):
```
Kokkos_ROOT=/dartfs-hpc/rc/home/5/f007gj5/kokkos/build
adios2_ROOT=/dartfs-hpc/rc/home/5/f007gj5/ADIOS2/build
HDF5_ROOT=/dartfs-hpc/rc/home/5/f007gj5/hdf5src/build/hdf5_install
```

Example configure + build (for the `pp` pgen with MPI and GPU):
```bash
cd radiative/entity
cmake -B build \
  -Dpgen=/dartfs-hpc/rc/home/2/f007hd2/plasma/radiative/entity/pgens/pp \
  -Dmpi=ON -Doutput=ON -Dprecision=single \
  -DKokkos_ROOT=/dartfs-hpc/rc/home/5/f007gj5/kokkos/build \
  -Dadios2_ROOT=/dartfs-hpc/rc/home/5/f007gj5/ADIOS2/build \
  -DHDF5_ROOT=/dartfs-hpc/rc/home/5/f007gj5/hdf5src/build/hdf5_install
cmake --build build -j$(nproc)
```

The compiled binary is at `build/src/entity.xc`. Each simulation directory has a symlinked `entity.xc`.

### Quick configure command (cake command)
```bash
cmake -B build -D pgen=/dartfs-hpc/rc/home/2/f007hd2/plasma/radiative/entity/pgens/pp -D Kokkos_ENABLE_CUDA=ON -D mpi=ON
```

## Running Simulations

```bash
./entity.xc -input <path/to/input.toml>
# Resume from checkpoint:
./entity.xc -input <path/to/input.toml> -restart
```

On the cluster both projects submit via SLURM using `mpirun`. See:
- `radiative/rad/scripts/gpu_pp.sh` — radiative (BW + IC) run script
- `radiative/rad/scripts/gpu_pp_IC.sh` — radiative (IC only) run script
- `turb2d/turbulence_2d/scripts/gpu.sh` — turbulence run script

**Critical MPI note**: The binary links against the system OpenMPI (`/usr/lib64/openmpi`). Loading an MPI module causes `pmix` symbol conflicts. The run scripts manually set:
```bash
export PATH=/usr/lib64/openmpi/bin:$PATH
export LD_LIBRARY_PATH=/usr/lib64/openmpi/lib:${LD_LIBRARY_PATH:-}
```
and pass `--mca pml ob1 --mca btl self,vader,tcp --mca mtl ^ofi --mca osc ^ucx` to `mpirun` to avoid OFI/RDMA failures.

Output and scratch data land in `/dartfs-hpc/scratch/f007hd2/<project>/`.

## Input Files (TOML)

See `entity/input.example.toml` for the full annotated schema. Key sections:

- `[simulation]` — engine (`"srpic"` or `"grpic"`), runtime
- `[grid]` — resolution, extent, metric, boundary conditions
- `[scales]` — `larmor0`, `skindepth0` (both = 1.0 means σ₀ = 1, B₀ = 1)
- `[algorithms.fieldsolver] enable = false` — disables EM evolution (used in radiative project)
- `[particles]` — `ppc0`, species list (mass/charge/maxnpart/pusher)
- `[setup]` — pgen-specific parameters
- `[output]` — format (`"hdf5"` or `"BPFile"`), `interval_time`, fields/particles/spectra/stats toggles
- `[checkpoint]` — interval, `keep`, `walltime`

Active input files:
- `radiative/rad/inputs/toml_pp.toml` — radiative cascade (512×512, 5 species, HDF5, field solver off)
- `radiative/rad/inputs/toml_pp_IC.toml` — IC-only variant (BW disabled)
- `turb2d/turbulence_2d/inputs/turb_2d_GPU.toml` — turbulence (GPU run, BPFile)
- `turb2d/turbulence_2d/inputs/turb_2d_CPU.toml` — turbulence (CPU test, BPFile)

## Unit System

All quantities are dimensionless, normalized to fiducial values from `[scales]`. With `larmor0 = skindepth0 = 1.0`: `B₀ = 1`, `σ₀ = 1`, `c = 1`. Particle momenta/energies are in units of `m_e c²`. Simulation time is in units of `c = 1`.

## Source Code Architecture

```
entity/src/
  engines/         # SRPICEngine, GRPICEngine — top-level simulation loop
  kernels/         # Kokkos kernels: particle pusher, field solver (Faraday/Ampere), current deposit
  archetypes/      # Base classes: ProblemGenerator, SpatialDistribution, EnergyDistribution, ParticleInjector
  framework/       # SimulationParams, Metadomain/Domain, containers
  metrics/         # Metric implementations (Minkowski, Spherical, Kerr-Schild, etc.)
  output/          # ADIOS2 output routines
  global/          # Global typedefs, enums, constants

entity/pgens/      # Problem generators — one directory per physics setup, each contains pgen.hpp
```

Problem generators live under `pgens/<name>/pgen.hpp` and implement `user::PGen<S, M>` inheriting from `arch::ProblemGenerator`. The `CustomPostStep` method (if defined) runs every timestep after the standard PIC loop — this is where user physics (IC, BW pair production, etc.) is implemented.

The active radiative pgen is `pgens/pp/pgen.hpp`. The `CustomPostStep` there implements:
1. **Inverse Compton (IC)**: continuous Thomson drag below a threshold γ, discrete Klein-Nishina Monte Carlo above it. The threshold is `gammaSwitch = KNswitch * gammaKN` where `gammaKN = 1/(4*enBath)` and `KNswitch` defaults to `0.1` (TOML `setup.switchToKN`). Acts on species 0 and 1 (primary e-/e+).
2. **Breit-Wheeler (BW) pair production**: photon + soft bath → e-/e+ pair. Acts on species 2 (photons). Injects into species 3/4.

## Analysis Scripts

### Radiative project (`radiative/rad/analysis/`)

All analysis scripts live under `radiative/rad/analysis/scripts/`. Uses ADIOS2 BP5 output (`format = "BPFile"`). The five species are indexed 1–5 (primary e-, primary e+, photons, created e-, created e+). Data subdirectories per run: `fields/`, `particles/`, `spectra/`.

**Active simulation runs** (each has its own scratch directory and output folder):

| Script | `WORK_DIR` | Physics |
|---|---|---|
| `gpu_pp.sh` | `/dartfs-hpc/scratch/f007hd2/radiative/pp` | IC + BW pair production |
| `gpu_pp_IC.sh` | `/dartfs-hpc/scratch/f007hd2/radiative/pp_IC` | IC only |

**Running scripts:** set `DATA`/`DATA_DIR` at the top of each script to the desired run's scratch path, then run from the `analysis/` directory:

```bash
# from radiative/rad/analysis/
conda run -n anaconda3 python scripts/plot_spectra_rad.py
conda run -n anaconda3 python scripts/plot_paper_figures_rad.py
conda run -n anaconda3 python scripts/plot_bw_distribution.py
conda run -n anaconda3 python scripts/plot_bw_partition_clean.py
conda run -n anaconda3 python scripts/plot_bw_momentum.py
conda run -n anaconda3 python scripts/make_movie_rad.py
conda run -n anaconda3 python scripts/make_movie_energy.py
conda run -n anaconda3 python scripts/make_movie_photons.py
```

**Output:** plots are written to `analysis/plots/<sim_name>/` where `<sim_name>` is the basename of `DATA`/`DATA_DIR` (e.g. `plots/pp/`, `plots/pp_IC/`, `plots/testPP/`). Each script derives this automatically — only the data path at the top of the script needs changing to target a different run.

### Turbulence project (`turb2d/turbulence_2d/analysis/`)

Uses ADIOS2 BP5 output (`format = "BPFile"`). Helper: `read_bp.py`. Default data directory: `/dartfs-hpc/scratch/f007hd2/turb2d/turbulence`.

```bash
# Field/spectra/particle plots — run from the analysis/ directory
python plot_fields.py
python plot_spectra.py
python plot_stats.py
```

Field variables in BP files are prefixed with `f` (e.g., `fB1`, `fE2`). Particle data uses `pX1_<s>`, `pU1_<s>`, `pW_<s>` where `<s>` is the 1-based species index. Lorentz factor: `γ = sqrt(1 + u1² + u2² + u3²)` for massive; `γ = |u|` for photons.

## Known Physics Issues (radiative/pp pgen)

- Secondary pairs (species 3/4) are not fed back into the IC module — they accumulate energy without further cooling.
- BW angular rejection loop runs up to 10,000 iterations per photon — can become a bottleneck as photon population grows.
- Whether a `(1 − cosθ)` lab-frame factor belongs in the BW cross-section is unresolved (currently omitted).
- Scattered photon direction is approximated along the parent particle's β̂ (not deflected by scattering angle).
