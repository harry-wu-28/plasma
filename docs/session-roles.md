# Session Roles: Cloud (code) vs. Cluster (execution)

Two kinds of Claude Code session work in this repo, and their jobs do not overlap. **Work out
which one you are before doing anything else**, then stay inside your column.

## Which session are you?

| Check | Cloud session | Cluster session |
|---|---|---|
| Where it runs | claude.ai cloud container (started from the web/app or a claude.ai project) | Dartmouth Discovery, over SSH, in `~/plasma` |
| Tell-tale | `CLAUDE_CODE_REMOTE=true`; no `/dartfs-hpc` | `/dartfs-hpc` exists; `sinfo`/`sbatch` on `PATH` |
| Has | a fresh git clone, GitHub push access | Entity checkouts, Kokkos/ADIOS2, GPUs via SLURM, the `analysis` conda env, all simulation output on scratch |
| Does not have | Entity's build deps, GPUs, scratch, any simulation output (all gitignored) | (only push access if the user has set it up) |

If neither tell-tale applies, stop and ask the user which role you have. Do not guess.

## Who does what

| Activity | Cloud session | Cluster session |
|---|---|---|
| Write/edit TOML inputs, SLURM scripts, build scripts, run-dir scaffolding | **Yes** | No |
| Write/edit analysis and plotting scripts (`analysis/`, `*/analysis/`) | **Yes** | No |
| Write/edit the LaTeX paper (`paper/main.tex`, `refs.bib`) and compile it | **Yes** | No |
| Write/edit how-to docs, READMEs, this file | **Yes** | No (except verified facts, below) |
| Physics code (`pgens/*/pgen.hpp`, Entity `src/kernels/`, `src/engines/`) | Evidence reports only. Edits only with explicit per-change permission from the user | Evidence reports only. Never edits |
| Configure / compile Entity (`cmake`, `build_twostream.sh`, …) | **Never** | **Yes** |
| Run `entity.xc`, any size, any machine | **Never**, not even a tiny CPU test | **Yes**, on GPU nodes via SLURM |
| `sbatch` / `scancel` | **Never** | Only when the user asks (critical rule 4) |
| Run analysis scripts on simulation output | **Never** (there is no output in the container) | **Yes** |
| Produce plots and paper figures from data | No | **Yes** (`paper/figures/*.pdf`) |
| Read logs (`logs/*.err`), `seff`/`sacct`, diagnose failed builds/runs | No (works from what the cluster session reports) | **Yes** |
| Record verified run/build facts in docs (critical rule 9) | No: it can't verify them | **Yes**, date-stamped |
| Interpret reported results, decide the next change | **Yes** | Reports observations; leaves code fixes to the cloud session |
| Merge PRs into `main` | No (user only) | No (user only) |

### What "never run" means for the cloud session

The cloud session's compute budget is for writing code. It must not build Entity, run
`entity.xc`, or run analysis on fake or synthetic data as a stand-in for a real run. The
only things it may execute are cheap static checks that don't simulate anything:

- `python -m py_compile <script>` or `python -c "import ast; ..."` (syntax only)
- `bash -n <script>` (syntax only)
- parsing a TOML file to check it is well formed
- `latexmk` on `paper/` to compile the report
- `git` and `gh`

Anything that needs a real build or real data goes to the cluster session as a step in the
PR's handoff section. "It probably works" is not verification, so the PR must say
**untested on the cluster** until the cluster session reports back.

### What the cluster session does not do

It does not edit source: inputs, scripts, analysis code, the paper, or how-to docs. When a
build fails, a job crashes, or a script has a bug, it does **not** patch it, even if the
fix is one line. It writes up what happened (below) and the cloud session makes the fix
on a branch. That keeps every source change in a reviewable PR and keeps the two sessions
from editing the same file.

The cluster session's own commits are limited to:

- result records: `analysis/reports/*.md`, or `RESULTS.md` in the run dir
- generated paper figures: `paper/figures/*.pdf` (other `plots/` dirs stay gitignored)
- dated, verified facts in `docs/*.md` and run-dir READMEs (e.g. "built OK against
  v1.3.3rc, 2026-11-20"; "job 1234 hit OOM at 40 GB")

## Handoff via git

`main` is the shared state. Neither session merges; the user merges.

**Cloud → cluster (new code to build or run)**

1. The cloud session works on a branch named `<area>/<topic>` (e.g. `twostream/seeded-mode`,
   `paper/results-section`), commits, pushes, and opens a PR against `main`.
2. The PR description has a **Cluster steps** section: the exact commands to build, submit,
   and analyze, in order, with expected output paths (scratch dir, `plots/` dir) and what to
   check (e.g. "`*_modes.png` should show a clean exponential for t ≈ 20–60"). Mark which
   steps need `sbatch`, so the user can approve them.
3. The cluster session runs those steps from the branch (`git fetch origin <branch> &&
   git checkout <branch>`) or from `main` after the user merges, only after the user tells it to.

**Cluster → cloud (results or failures)**

1. The cluster session writes a short record: what it ran (commit hash, command, job ID),
   what came out (key numbers, fit results, figure paths), and for a failure the exact error
   with the relevant log excerpt. It goes in `analysis/reports/<YYYY-MM-DD>-<topic>.md` or
   the run dir's `RESULTS.md`.
2. It commits that record (plus any `paper/figures/*.pdf`) on a branch named
   `results/<topic>` and pushes it **when the user asks** (critical rule 7), or the user
   pastes the record into the cloud session.
3. The cloud session reads the record from git (or the paste), never assumes numbers it
   hasn't seen, and opens a new PR with any fixes or the paper text that uses the results.

Raw simulation output (`*.bp`, `*.h5`, checkpoints) and `logs/` never go into git; they stay
on scratch. Only the short record and the paper figures cross over.

## Rules that apply to both sessions

Everything in [CLAUDE.md](../CLAUDE.md) "Critical rules" still applies, in particular the
physics no-edit rule (6) and the evidence-report format in [physics.md](physics.md). Note that
`.claude/settings.json` (which enforces rule 6 with deny rules) is gitignored, so it exists
only on the cluster. In the cloud session rule 6 is enforced by these docs alone.
