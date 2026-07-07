# Evidence Report: pp photon injection leaves all particle weights at zero → all spectra output is empty

**Status**: New finding (first valid pp run, 2026-07-07, SLURM job 8915373). **Author**: agent
session 2026-07-07. **Severity**: diagnostics-correctness — particle dynamics are unaffected,
but every weight-derived output (`[output.spectra]`, weighted moments, weighted stats) is
identically zero for **all** species in the pp regime. The pp_IC regime is *not* affected.

## 1. Location

- `pgens/pp/pgen.hpp:97–119` — the hand-rolled photon injection loop in `InitPrtls`. It
  assigns `i1, dx1, i2, dx2, ux1, ux2, ux3, tag` — but never `weight`:

  ```c++
  Kokkos::parallel_for(
    "PhotonInjection",
    domain.mesh.rangeActiveCells(),
    Lambda(index_t i1, index_t i2){
      ...
      ux3_phot(phot_p + offset_phot) = epsilon1_ * U;
      tag_phot(phot_p + offset_phot) = ParticleTag::alive;   // <- weight never set
    }
  ```

  (`weight_phot` is aliased at line 94 but only ever read elsewhere, never written here.)

- `pgens/pp/pgen.hpp:294, 438, 452` — the IC and BW modules *propagate* the parent's weight
  to created particles (`weight_phot(...) = weight(p)`, `weight_elec(...) = weight(p)`,
  `weight_pos(...) = weight(p)`), so the zero weight is inherited by every particle ever
  created in the cascade.

- `radiative/entity/src/framework/domain/output.cpp:784` — the spectra kernel bins by weight
  **unconditionally** (no `use_weights` guard):

  ```c++
  dn_acc(e_ind) += weight(p);
  ```

- Contrast: Entity's standard injection kernel,
  `radiative/entity/src/kernels/injectors.hpp:46,69`, always writes
  `weight_arr(p) = weight` with default `weight = ONE`. The pp_IC pgen injects its primaries
  through the arch injector path, so pp_IC particles carry weight 1 and its spectra are fine.

## 2. Claim

Kokkos views are zero-initialized, so photons injected by the pp `InitPrtls` loop carry
`weight = 0`, and via the propagation lines above so do all IC-emitted photons and BW
secondaries. Since `ComputeSpectra` accumulates `+= weight(p)`, every spectrum (`sN_1`…`sN_5`)
is identically zero, for the entire run, regardless of how many particles exist. Field-moment
outputs (`N_i`, `Rho_i`, …) honor `particles.use_weights` (default `false` on Cartesian grids,
each particle then counts as 1 — see `src/kernels/particle_moments.hpp:309`), so *those* would
be correct if requested; only weight-derived diagnostics are broken. Particle dynamics (pusher,
IC/BW Monte-Carlo) never read `weight`, so trajectories, counts, and momenta remain valid.

## 3. Evidence

**Demonstrated** (run pp, job 8915373, output at
`/dartfs-hpc/scratch/f007hd2/radiative/pp/pp/`):

- `bpls -l particles/particles.00000514.bp` → `pW_3 {197802} = 0 / 0`,
  `pW_4 {11911} = 0 / 0`, `pW_5 {11911} = 0 / 0` — 197,802 alive photons and 2×11,911
  secondaries, every weight exactly zero.
- `bpls -d spectra/spectra.00000514.bp sN_3` → all bins 0, while the same file's momenta are
  physical (`pU1_3 = ±200` matching `epsilon1 = 200`; `pU1_4 = ±165` below the parent photon
  energy, as required by BW kinematics).
- The run itself is healthy: exit 0 in 14 s, 1.98×10⁶ photons → 1.31×10⁵ secondary pairs of
  each sign (final stdout summary), i.e. the BW module fired ~13% pair conversion.

**Demonstrated (code reading)**: the three locations quoted in §1; zero-initialization of
Kokkos views supplies the 0.

## 4. Proposed change (unapplied — requires physicist sign-off)

Single line in `pgens/pp/pgen.hpp`, inside the injection loop after line 115
(`ux3_phot(...) = epsilon1_ * U;`):

```diff
     ux3_phot(phot_p + offset_phot) = epsilon1_ * U;
+    weight_phot(phot_p + offset_phot) = ONE;
     tag_phot(phot_p + offset_phot) = ParticleTag::alive;
```

`weight_phot` is already captured at line 94, so no other change is needed. Weight = 1 matches
what the arch injector gives pp_IC primaries. No performance or numerical-stability impact
(one extra coalesced store per injected photon at t=0 only). IC/BW propagation lines then
carry 1 to all descendants automatically.

## 5. Verification plan

Rerun the identical `toml_pp.toml` (runtime 100 suffices) and check
`bpls -l particles/particles.00000001.bp pW_3` → expect `1 / 1`, and
`bpls -d spectra/spectra.00000001.bp sN_3` → a single populated bin at ε ≈ 200 containing
~2×10⁶ (× 1/stride sampling does not apply to spectra; the full population is binned). At
later steps `sN_4`/`sN_5` should populate as pairs appear, and Σ_bins sN_3 should equal the
alive-photon count printed in stdout.

## 6. Confidence & alternatives

High. The zero weights and zero spectra are directly observed; the assignment gap and the
unconditional `+= weight(p)` are directly read from the code. Alternative explanations
considered and rejected: (a) spectra bins out of range — no, `sEbn` spans 10⁻³…10³ and ε=200
is in range; even out-of-range particles clamp into the edge bins (output.cpp:775–781);
(b) `use_weights` misconfiguration — irrelevant, the spectra kernel has no `use_weights`
branch. Related Known Physics Issues: none overlap (this is a diagnostics gap, not cascade
physics), but note that any future analysis of this run's spectra or weighted stats would
silently read zeros — analysis should use particle momenta (`pU*`) until fixed.
