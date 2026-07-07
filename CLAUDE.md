# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Project**: Entity PIC simulations of QED pair cascades (inverse Compton + Breit-Wheeler) on Dartmouth's Discovery HPC cluster (SLURM). Entity is a C++17 relativistic PIC code (Kokkos/MPI/ADIOS2); binary is `entity.xc`.

## Layout

- `pgens/` — **user's problem generators** (pp, pp_IC, turbulence); builds point here via `-Dpgen`
- `radiative/entity/` — Entity checkout (upstream v1.3.3rc) with build dirs `build_pp/`, `build_pp_IC/`
- `analysis/` — **shared analysis home**: `scripts/` (bp_reader, viz_style, overview — general, run-agnostic), `reports/` (evidence reports)
- `radiative/pp/` — per-run layout: `runs/<run>/` (`inputs/`, `scripts/`, `logs/`, `plots/`, optional run-specific `analysis/`; one dir per scratch run, currently `testPP`, `bw_aharonian`), plus `scripts/bind_gpu.sh`, `entity.xc` symlink
- `radiative/pp_IC/` — run dir (old flat layout): `inputs/`, `scripts/` (SLURM), `logs/`, `analysis/`, `entity.xc` symlink
- `turb2d/` — empty scaffold
- `docs/` — detailed guides (see index below)

## Essential commands

```bash
# Rebuild after a pgen edit (from radiative/entity/; build dir matches pgen):
cmake --build build_pp_IC -j8

# Run locally / resume:
./entity.xc -input <input.toml> [-restart]

# Submit (user's call only): sbatch radiative/pp_IC/scripts/gpu_pp_IC.sh
# Analysis: conda run -n analysis python <script>   (only env with adios2)
# Full run digest: conda run -n analysis python analysis/scripts/overview.py <run_dir>
```

## Critical rules

1. **The file structure changes between sessions without notice.** Re-survey (`ls`, `find`) before structural work. Never recreate, overwrite, or "fix" a path to match a cached/remembered layout without explicit permission — a missing path is a deliberate change until the user says otherwise. This applies to these docs too: if reality contradicts them, believe reality and update the doc.
2. **Never `module load openmpi`** — PMIx symbol conflict. The binary uses system OpenMPI; run scripts set paths and `--mca` flags. Only `cuda/12` is loaded.
3. **Simulation output goes to `/dartfs-hpc/scratch/f007hd2/`, never home** (~50 GB quota). Scratch is unbacked-up and purgeable — copy keeper results back promptly.
4. **Never `sbatch`/`scancel` unprompted** — queue time and GPU hours are the user's.
5. **Species indexing: C++ is 0-based, TOML/output is 1-based** (species 1–5 = primary e-, e+, photons, secondary e-, e+). The most likely off-by-one in this repo.
6. **NEVER edit physics code** — the pgen physics (`pgens/*/pgen.hpp`) and Entity's kernels/engines are off-limits without explicit, per-change permission from the user. When you find a suspected error or have an improvement, do not fix it: build an **evidence report** for a physicist to act on (exact location, the equation/limit violated, observed evidence, proposed change as an unapplied diff) — format in [docs/physics.md](docs/physics.md). Even "harmless" cleanups are edits: changing float evaluation order is a physics change.
7. **Commit at meaningful checkpoints** (compiling pgen change, working script, finalized input) — one logical change per commit, plain detailed messages (what + why), no push/history rewrites unasked.
8. **Adopt an operating profile when a task touches its domain** (Physicist, Build Engineer, Kernel Engineer, Analyst) — see [docs/agent-profiles.md](docs/agent-profiles.md).
9. **Write conclusions back into the relevant doc before finishing.** When a session establishes something durable — a diagnosis confirmed, a fact verified, a step completed, an approach ruled out — add it (date-stamped) to the matching `docs/*.md` so the next session doesn't waste time re-deriving it. Durable findings only: session chatter, transient state, and unverified hunches don't belong in docs.

## Docs index — read the relevant doc before working in its area

| Doc | Read when |
|---|---|
| [docs/building-and-running.md](docs/building-and-running.md) | Building (CMake flags, dependency paths), running, SLURM scripts, MPI details, TOML inputs |
| [docs/hpc-discovery.md](docs/hpc-discovery.md) | Filesystems/quotas, scratch layout, SLURM discipline, official Discovery doc links |
| [docs/physics.md](docs/physics.md) | pgen architecture, IC/BW modules, setup params, unit system, known physics issues, analysis conventions |
| [docs/agent-profiles.md](docs/agent-profiles.md) | Operating personas, per-domain checklists, discourse norms |

When uncertain about cluster policy (partitions, quotas, purge), consult https://rc.dartmouth.edu/ or query the cluster (`sinfo`, `sacct`) — never assert policy from memory.
