# Evidence Report: Secondary pairs are never IC-cooled (exemplar)

*This is the exemplar evidence report referenced by [physics.md](physics.md) — a real, known
issue written up in the required format. New reports should follow this shape.*

**Status**: Known issue (listed under Known Physics Issues). **Author**: agent session
2026-07-07. **Severity**: physics-correctness — affects any run with `IsBW = true` evolved
long enough for secondaries to matter.

## 1. Location

`pgens/pp/pgen.hpp` (same structure in `pgens/pp_IC/pgen.hpp`):

- Line 161–163 — the IC module loops over species indices 0 and 1 only:
  ```c++
  if (IsIC)
    {
      for (int s = 0; s < 2; s++)
  ```
- Lines 324–340 — the BW module injects created pairs into species indices 3 and 4:
  ```c++
  elec_spec = 3;
  auto &electrons = domain.species[elec_spec];
  ...
  pos_spec = 4;
  auto &positrons = domain.species[pos_spec];
  ```

## 2. Claim

Every electron/positron in the soft-photon bath should experience IC drag/scattering; the
cross-section does not distinguish primaries from secondaries. Because the IC loop covers only
`s ∈ {0, 1}`, particles created by BW into `s ∈ {3, 4}` evolve ballistically: they never cool,
never produce IC photons, and therefore never feed the next cascade generation.

## 3. Evidence

**Demonstrated (from code reading)**: `domain.species[3]`/`[4]` appear only as BW injection
targets; no other statement in `CustomPostStep` touches their momenta. The IC loop bound `s < 2`
is a hard constant.

**Suspected (needs a run to confirm)**: in `<name>_stats.csv` and the spectra output, the
secondary-species energy should grow monotonically with no cooling tail, and the photon spectrum
should be missing the secondary-generation IC component. Not yet demonstrated — the last pp_IC
run died during init (see hpc-discovery.md), so no data exists.

## 4. Proposed change (NOT applied)

Extend the IC loop to the secondary species, e.g.:

```diff
-	  for (int s = 0; s < 2; s++)
+	  for (int s : {0, 1, 3, 4})
```

Side effects to weigh: (a) per-step cost grows with the secondary population; (b) secondaries
then emit IC photons into species 2, closing the cascade loop — this changes the photon budget
and hence the BW rate, so results are *expected* to differ from all previous runs; (c) if the
physics intent is a one-generation cascade, the current behavior may be deliberate.

## 5. Verification plan

Short run with `IsIC = IsBW = true`: (i) plot per-species mean γ vs time — species 4/5 (1-based)
should show a cooling turnover instead of monotonic growth; (ii) check total (particles +
radiated) energy accounting; (iii) compare photon spectra with/without the change — a secondary
IC bump should appear.

## 6. Confidence & alternatives

High confidence in the code-reading claim (the loop bound is unambiguous). The open question is
intent, not mechanism: the physicist may want secondaries uncooled for a controlled
one-generation experiment. Touches Known Physics Issue #1 directly; interacts with issue #2
(more IC photons → larger BW workload → rejection-loop cost).
