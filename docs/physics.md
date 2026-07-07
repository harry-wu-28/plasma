# Physics: pgens, Units, and Known Issues

## Physics change policy: report, don't edit

Agents **do not edit physics code** — `pgens/*/pgen.hpp` and Entity's `src/kernels/`,
`src/engines/` — without explicit, per-change permission from the user. Permission for one
change does not carry over to the next. Non-physics surfaces (run scripts, TOML inputs when
asked, analysis code, build config, docs) remain editable under the normal rules.

When you find a suspected error or want to propose an improvement, produce an **evidence
report** the user can hand to a physicist. A report contains:

1. **Location** — file:line of every implicated statement, with the surrounding code quoted.
2. **Claim** — the specific equation, limit, or invariant violated (e.g. "Thomson drag term
   lacks the γ² factor from Blumenthal & Gould Eq. X"), never "this looks wrong."
3. **Evidence** — what you actually observed: log excerpts, `_stats.csv` trends, a plot from
   existing data, a dimensional-analysis derivation in the code's units, or a limit check
   (Thomson limit `γ ≪ gammaKN`, BW threshold `s ≥ 4`, energy conservation across an event).
   Distinguish *demonstrated* from *suspected*.
4. **Proposed change** — as an unapplied diff or precise prose ("replace line N with ..."),
   including any numerical-stability or performance side effects you can foresee.
5. **Verification plan** — the test, plot, or limit check that would confirm the fix worked.
6. **Confidence & alternatives** — how sure you are, what else could explain the observation,
   and which Known Physics Issues (below) it touches, if any.

Write reports as standalone markdown (in the relevant `analysis/` dir or the scratchpad, per
the user's preference) so they survive the session and can be emailed or discussed as-is.
**Follow the exemplar**: [example-evidence-report.md](example-evidence-report.md) writes up the
secondary-pair cooling issue in exactly this format — imitate its structure and level of detail.

Enforcement: `.claude/settings.json` denies Edit/Write on `pgens/**/*.hpp|cpp` and
`radiative/entity/src/**`, and `pgens/CLAUDE.md` restates the rule in-directory. If the user
grants a specific edit, they will approve it through the permission prompt.

## The two radiative setups

Both pgens (`pgens/pp/pgen.hpp`, `pgens/pp_IC/pgen.hpp`) contain the **same IC + BW physics
modules** in `CustomPostStep`, toggled by TOML `setup.IsIC` / `setup.IsBW`. They differ in
initial conditions:

- **pp** — injects an isotropic photon population at t=0 (species 3, energy `setup.epsilon1`,
  `ppc0` per cell); pairs then appear via BW and cool via IC.
- **pp_IC** — injects Maxwellian e-/e+ pairs (species 1/2) kicked to a beam with
  `ux1 = setup.gamma0`; photons appear via IC upscattering.

## Pgen `[setup]` parameters

`temperature` (+optional `temperature2`), `OpticalDepth` (Thomson depth across Lx),
`photonEnergy` (soft bath energy, sets `gammaKN = 1/(4*photonEnergy)`), `switchToKN`
(default 0.1; IC switches Thomson→KN at `gammaSwitch = switchToKN * gammaKN`), `gamma0`
(beam Lorentz factor), `epsilon1` (pp only: injected photon energy), `IsIC`, `IsBW`.

## Unit system

All quantities are dimensionless, normalized to fiducial values from `[scales]`. With
`larmor0 = skindepth0 = 1.0`: `B₀ = 1`, `σ₀ = 1`, `c = 1`. Particle momenta/energies are in
units of `m_e c²`. Lorentz factor: `γ = sqrt(1 + u²)` for massive particles; `γ = |u|` for
photons.

## Source code architecture

```
radiative/entity/src/
  engines/         # SRPICEngine, GRPICEngine — top-level simulation loop
  kernels/         # Kokkos kernels: particle pusher, field solver (Faraday/Ampere), current deposit
  archetypes/      # Base classes: ProblemGenerator, SpatialDistribution, EnergyDistribution, ParticleInjector
  framework/       # SimulationParams, Metadomain/Domain, containers
  metrics/         # Metric implementations (Minkowski, Spherical, Kerr-Schild, etc.)
  output/          # ADIOS2 output routines
  global/          # Global typedefs, enums, constants
```

Problem generators implement `user::PGen<S, M>` inheriting from `arch::ProblemGenerator`.
`InitPrtls` sets initial conditions; `CustomPostStep` runs every timestep after the standard
PIC loop — this is where the user physics lives:

1. **Inverse Compton (IC)**: continuous Thomson drag below `gammaSwitch`, discrete
   Klein-Nishina Monte Carlo above it. Acts on species indices 0/1 (primary e-/e+), emits
   photons into species index 2.
2. **Breit-Wheeler (BW) pair production**: photon + soft bath → e-/e+ pair. Acts on species
   index 2, injects into species indices 3/4.

**Species indexing: C++ indices are 0-based, TOML/output indices are 1-based.** Species 1–5 =
primary e-, primary e+, photons, secondary e-, secondary e+.

## Known physics issues (pp / pp_IC pgens)

These are open research questions, not bugs to silently "fix" — flag any change touching them.

- Secondary pairs (species indices 3/4) are not fed back into the IC module — the IC loop only
  covers species 0/1, so secondaries accumulate energy without cooling.
- BW angular rejection loop runs up to 10,000 iterations per photon — can become a bottleneck
  as the photon population grows.
- Whether a `(1 − cosθ)` lab-frame factor belongs in the BW cross-section is unresolved
  (currently omitted).
- Scattered photon direction is approximated along the parent particle's β̂ (not deflected by
  scattering angle).
- **pp only** (found 2026-07-07, job 8915373): the pp `InitPrtls` photon loop never sets
  `weight` (zero-initialized), and IC/BW propagate the parent weight — so all particles carry
  weight 0 and all `[output.spectra]` output is identically zero (the spectra kernel bins
  `+= weight(p)` unconditionally). Dynamics and unweighted moments are unaffected; pp_IC is
  unaffected (its arch injector writes weight = 1). Evidence report with one-line proposed
  fix: `radiative/pp/analysis/zero-weight-photon-injection-report.md`. Re-confirmed
  2026-07-07 on the testPP production run (job 8915652): `pW_3` sampled via `bpls` is
  identically zero at the final output step.

## Analysis conventions

Data is ADIOS2 BP5 (`format = "BPFile"`). Python analysis runs via
`conda run -n analysis python <script>` — the `analysis` conda env has adios2 2.11 +
numpy + matplotlib (verified 2026-07-07; `anaconda3` has **no** adios2, and no `bpls` was
found on PATH or under dependencies — probe files from Python). Confirm variable names
against the actual BP file before writing reader code. Every plot states its units in the
axis label. Write outputs to `analysis/plots/<run_name>/`, derived from the data path.

**Overview tooling** (added 2026-07-07): `radiative/pp/analysis/scripts/` has
`bp_reader.py` (RunReader library), `viz_style.py` (shared palette/style), and
`overview.py` — run `conda run -n analysis python overview.py <run_dir>` against any
run dir on scratch (pp or pp_IC) for a full digest: summary + health checks, census,
energetics, spectra, density maps, field maps. Safe to run mid-job (skips mid-write steps).

### BP file layout facts (verified 2026-07-07 on runs pp/pp and pp/testPP)

- One BP5 dir per output step: `fields/fields.00000514.bp` etc. Every file carries
  scalar `Step`/`Time` and the **full input config as attributes** (`setup.*`,
  `grid.*`, `output.*` — no need to parse the TOML).
- Fields: `X1`,`X2` centers, `X1e`,`X2e` edges; 2D arrays `fB1..3`, `fE1..3`,
  `fN_<s>`, `fRho_<s>`, `fT11_<s>`.., `fV1_<s>`.. stored **[x2, x1]** (MPI
  decomposition along X2 splits the first axis).
- Particles: `pX1_<s>`, `pX2_<s>`, `pU1..3_<s>`, `pW_<s>`, subsampled by
  `output.particles.stride` (10 in current runs) — multiply counts/sums by stride.
- Spectra: `sEbn` (n_bins+1 edges), `sN_<s>` are ADIOS2 **local** arrays — one block
  per writer rank, and non-root ranks may write zero-count blocks. Read block-wise,
  skip `Count==0` (a plain `read()` on them NaN-crashes adios2 2.11 Python), sum blocks.
- Zero-size variables (empty species) also crash plain `read()` — guard on global shape.
- **pp runs only**: species 1/2 are empty by design (pp injects only photons), so the
  `[output.fields]` quantities `N_1, N_2, Rho_1, Rho_2, V_1/2, Tij_1/2` are identically
  zero, and with the fieldsolver disabled E/B are zero too — **all 28 field variables
  carry no information**; the overview must be built from particle data. (Suggest
  switching the quantities to species 3/4/5 for future pp inputs.) Built-in spectra are
  also all zero for pp (zero-weight issue above).

### Run log

- 2026-07-07, job 8915652 (`testPP`, 2560², runtime 1000, completed in 7:27): overview
  in `radiative/pp/analysis/plots/testPP/`. Photons stay monoenergetic at ε₁=200 and
  deplete ~12% via BW (5.24e7 → 4.61e7 stride-corrected); secondaries grow to 6.3e6
  each with spectrum spanning γ ≈ 25–170 peaked near 130; ⟨γ⟩ of secondaries stays flat
  at ≈100 for the whole run — direct evidence of the "secondaries not fed back into IC"
  known issue. Total energy conserved to the eye.
