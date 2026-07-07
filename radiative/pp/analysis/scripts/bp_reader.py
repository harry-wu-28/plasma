"""ADIOS2 BP5 reader for Entity v1.3.3 run output (pp / pp_IC setups).

Layout facts, verified 2026-07-07 against runs pp/pp and pp/testPP:

- A run dir holds fields/, particles/, spectra/, each with one BP5 dir per
  output step: e.g. fields/fields.00000514.bp. Every file carries scalar
  Step and Time plus the full input config as attributes.
- fields:    X1, X2 (cell centers), X1e, X2e (edges), 2D arrays fB1..fB3,
  fE1..fE3, fN_<s>, fRho_<s>, fT11_<s>.., fV1_<s>.. — arrays are stored
  [x2, x1] (MPI decomposition along X2 splits the first axis).
- particles: pX1_<s>, pX2_<s>, pU1_<s>, pU2_<s>, pU3_<s>, pW_<s> with
  1-based species index <s>. Output is subsampled by
  output.particles.stride. Zero-size variables (empty species) crash
  adios2's plain read() — guard on the global shape.
- spectra:   sEbn (bin edges, n_bins+1), sN_<s> (counts) are ADIOS2 *local*
  arrays: no global shape, one block per writer rank, and ranks other than
  0 may write zero-count blocks. Read block-wise, skip Count==0, sum.
- The pp pgen leaves particle weights at 0 (see
  radiative/pp/analysis/zero-weight-photon-injection-report.md), so all
  sN_<s> are identically zero for pp runs; build spectra from raw
  particle momenta instead.

Species convention (this repo's 5-species radiative setups; TOML/output
1-based): 1 e-_p, 2 e+_p, 3 phot (massless), 4 e-_sec, 5 e+_sec.
"""

from pathlib import Path

import numpy as np
from adios2 import FileReader

SPECIES_LABELS = {1: "e-_p", 2: "e+_p", 3: "phot", 4: "e-_sec", 5: "e+_sec"}
MASSLESS = {3}


def lorentz_gamma(u1, u2, u3, massless):
    """gamma = |u| for photons, sqrt(1 + u^2) for massive particles."""
    usq = u1 * u1 + u2 * u2 + u3 * u3
    return np.sqrt(usq) if massless else np.sqrt(1.0 + usq)


def _parse_attr(raw):
    """Entity attribute values arrive as strings: '\"pp\"', '0.176777',
    '{ 1, 2, 3 }'. Convert to python types."""
    s = raw.strip()
    if s.startswith("{"):
        inner = s.strip("{} ").strip()
        return [] if not inner else [_parse_attr(t) for t in inner.split(",")]
    if s.startswith('"'):
        return s.strip('"')
    try:
        f = float(s)
        return int(f) if f.is_integer() and ("." not in s and "e" not in s.lower()) else f
    except ValueError:
        return s


class RunReader:
    """Discovers and reads one Entity run directory on scratch."""

    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        if not self.run_dir.is_dir():
            raise FileNotFoundError(f"run dir not found: {run_dir}")
        self.steps = {}  # kind -> {step:int -> Path}
        for kind in ("fields", "particles", "spectra"):
            d = self.run_dir / kind
            found = {}
            if d.is_dir():
                for p in sorted(d.glob(f"{kind}.*.bp")):
                    try:
                        found[int(p.name.split(".")[1])] = p
                    except (IndexError, ValueError):
                        continue
            self.steps[kind] = found
        if not any(self.steps.values()):
            raise FileNotFoundError(f"no fields/particles/spectra BP output under {run_dir}")
        self.attrs = self._read_attrs()
        self.nspec = int(self.attrs.get("particles.nspec", 5))
        self.stride = int(self.attrs.get("output.particles.stride", 1))

    def _any_file(self):
        for kind in ("fields", "particles", "spectra"):
            if self.steps[kind]:
                return next(iter(self.steps[kind].values()))
        raise FileNotFoundError("no BP files")

    def _read_attrs(self):
        with FileReader(str(self._any_file())) as f:
            return {k: _parse_attr(v.get("Value", "")) for k, v in f.available_attributes().items()}

    def species_label(self, s):
        return SPECIES_LABELS.get(s, f"sp{s}")

    # ---------------- particles ----------------

    def particle_counts(self, step):
        """Per-species particle count in the file (shape inquiry only — no
        data read). Multiply by self.stride for the population estimate."""
        out = {}
        with FileReader(str(self.steps["particles"][step])) as f:
            time = float(f.read("Time"))
            for s in range(1, self.nspec + 1):
                v = f.inquire_variable(f"pU1_{s}")
                out[s] = int(v.shape()[0]) if v is not None else 0
        return time, out

    def particles(self, step, species, quantities=("X1", "X2", "U1", "U2", "U3", "W")):
        """Read one species' particle arrays. Returns dict quantity -> array
        (empty arrays for an empty species)."""
        out = {}
        with FileReader(str(self.steps["particles"][step])) as f:
            for q in quantities:
                name = f"p{q}_{species}"
                v = f.inquire_variable(name)
                if v is None or int(v.shape()[0]) == 0:
                    out[q] = np.empty(0, dtype=np.float32)
                else:
                    out[q] = f.read(name)
        return out

    def particle_gammas(self, step, species):
        u = self.particles(step, species, quantities=("U1", "U2", "U3"))
        return lorentz_gamma(u["U1"], u["U2"], u["U3"], species in MASSLESS)

    # ---------------- spectra ----------------

    def spectrum(self, step):
        """Built-in spectra: (time, bin_edges, {species: counts}), counts
        summed over writer blocks (zero-count blocks skipped)."""
        counts = {}
        with FileReader(str(self.steps["spectra"][step])) as f:
            time = float(f.read("Time"))
            edges = self._read_local_blocks(f, "sEbn", combine="first")
            for s in range(1, self.nspec + 1):
                counts[s] = self._read_local_blocks(f, f"sN_{s}", combine="sum")
        return time, edges, counts

    @staticmethod
    def _read_local_blocks(f, name, combine):
        total = None
        for b in f.all_blocks_info(name)[0]:
            if int(b.get("Count") or 0) == 0:
                continue  # empty rank block; plain read() would NaN-crash
            v = f.inquire_variable(name)
            v.set_block_selection(int(b["BlockID"]))
            arr = f.read(v)
            if combine == "first":
                return arr
            total = arr if total is None else total + arr
        return total

    # ---------------- fields ----------------

    def field_names(self, step=None):
        step = step if step is not None else next(iter(self.steps["fields"]))
        with FileReader(str(self.steps["fields"][step])) as f:
            return sorted(n for n in f.available_variables() if n.startswith("f"))

    def fields(self, step, names):
        """Read 2D field arrays plus axes. Arrays come back [x2, x1]."""
        out = {}
        with FileReader(str(self.steps["fields"][step])) as f:
            out["Time"] = float(f.read("Time"))
            for ax in ("X1", "X2", "X1e", "X2e"):
                out[ax] = f.read(ax)
            for n in names:
                out[n] = f.read(n)
        return out
