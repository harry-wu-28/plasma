# Dartmouth Discovery HPC Environment

This runs on Dartmouth's **Discovery** cluster (SLURM). When uncertain about partitions, quotas,
purge policy, or cluster services, **consult the official documentation** (via WebFetch) or query
the cluster directly (`sinfo`, `sacct`) — never assert policy numbers from memory:

- Research Computing & Data home: https://rc.dartmouth.edu/
- Discovery overview: https://rc.dartmouth.edu/hpc/discovery-overview/
- Scratch space policy: https://rc.dartmouth.edu/hpc/hpc-scratch-space/
- HPC knowledge base: https://services.dartmouth.edu/TDClient/1806/Portal/KB/?CategoryID=13110

## Filesystem discipline

- **DartFS home** (`/dartfs-hpc/rc/home/2/f007hd2`): ~50 GB quota, permanent. Code, inputs,
  scripts, plots — never simulation output. A single BP5 run can blow the quota.
- **Shared scratch** (`/dartfs-hpc/scratch`): large (tens of TB), **no backup, subject to purge**
  (per policy, roughly 45-day expectation, ~5 TB/user). All simulation output and checkpoints go
  here. Results worth keeping (final plots, reduced data) must be copied back to permanent
  storage promptly.
- Node-local `/scratch` on compute nodes is purged even more aggressively (~20 days); nothing
  durable belongs there.

## Scratch layout (surveyed 2026-07-07 — re-verify with `ls` before relying on it)

Entity runs with cwd = `WORK_DIR` and creates a directory tree named after `simulation.name`
from the TOML:

```
/dartfs-hpc/scratch/f007hd2/radiative/
  pp/                    # WORK_DIR for pp runs (first completed run 2026-07-07, job 8915373, 335 MB)
  pp_IC/                 # WORK_DIR for pp_IC runs
    pp_IC/               # named after simulation.name
      pp_IC.info         #   resolved build + full config dump (versions, flags, memory footprint)
      pp_IC.log          #   verbose logger checkpoints — shows how far a run got
      pp_IC.err          #   warnings/errors
      pp_IC.out          #   domain decomposition + memory report
      pp_IC_stats.csv    #   per-step field/energy stats
      fields/            #   fields.<step>.bp     (BP5; created on first output write)
      particles/         #   particles.<step>.bp
      spectra/           #   spectra.<step>.bp
    pp_IC.ckpt/          # checkpoints: step-<step>.bp
```

The BP5 subdirectory names and file patterns come from `src/output/writer.cpp`
(`<mode>/<mode>.%08lu.bp`) and `src/output/checkpoint.cpp` (`step-%08lu.bp`).

Diagnosing a failed run: `<name>.log` (last logger checkpoint reached) and `<name>.err` first,
then the SLURM logs in the repo run dir's `logs/`. State as surveyed 2026-07-07: pp has one
completed validation run (job 8915373, full BP5 tree, all 10 output steps readable via `bpls`).
The 2026-06-04 pp_IC failure is now diagnosed: it hung at the first `CommunicateFields`
because the build had `gpu_aware_mpi=ON` while the runtime OpenMPI is not CUDA-aware
(`btl_tcp writev ... Bad address` in `logs/gpu_8754355.err`), then hit the time limit — see
[building-and-running.md](building-and-running.md); rebuild `build_pp_IC` with
`-Dgpu_aware_mpi=OFF` before rerunning pp_IC.

## SLURM discipline

- **Login nodes are for editing, builds, and light analysis only** — never run `entity.xc` or
  heavy Python on a login node; the GPU code requires GPU nodes anyway. Keep build parallelism
  reasonable rather than blindly `-j$(nproc)` on a busy login node.
- This project uses `--partition=gpuq` (L40S nodes, 5-day time limit). Other GPU partitions
  exist (`a100`, `h200`, `*_preemptable` with shorter limits) — check `sinfo -s` for current
  availability before suggesting one.
- After a job completes, calibrate future requests with `seff <jobid>` or
  `sacct -j <jobid> --format=Elapsed,MaxRSS,State` — don't carry over oversized
  `--time`/`--mem` requests by habit.
- Monitor with `squeue -u f007hd2`; job stdout/stderr land in the run dir's `logs/`.
- For runs that may hit the partition time limit, set `[checkpoint] walltime` in the TOML so
  Entity checkpoints before SLURM kills the job, then resume with `-restart`.
- Submitting (`sbatch`) and cancelling (`scancel`) jobs is the user's call — never do either
  unprompted.
