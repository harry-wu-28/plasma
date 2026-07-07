# Building and Running Entity

## Building

Entity uses CMake. Dependency paths:

```
Kokkos_ROOT=/dartfs-hpc/rc/home/2/f007hd2/dependencies/kokkos/install   # user's build, CUDA arch 89 (L40S)
adios2_ROOT=/dartfs-hpc/rc/home/5/f007gj5/ADIOS2/build                  # shared, owned by f007gj5
HDF5_ROOT=/dartfs-hpc/rc/home/5/f007gj5/hdf5src/build/hdf5_install      # shared, owned by f007gj5
```

Configure + build (example: the pp_IC variant):

```bash
cd radiative/entity
module load cuda/12                                   # nvcc must be on PATH for configure & build
export NVCC_WRAPPER_DEFAULT_COMPILER=/usr/bin/g++    # see "host compiler landmine" below
cmake -B build_pp_IC \
  -Dpgen=/dartfs-hpc/rc/home/2/f007hd2/plasma/pgens/pp_IC \
  -Dmpi=ON -Doutput=ON -Dprecision=single \
  -Dgpu_aware_mpi=OFF \
  -DKokkos_ROOT=/dartfs-hpc/rc/home/2/f007hd2/dependencies/kokkos/install \
  -Dadios2_ROOT=/dartfs-hpc/rc/home/5/f007gj5/ADIOS2/build \
  -DHDF5_ROOT=/dartfs-hpc/rc/home/5/f007gj5/hdf5src/build/hdf5_install
cmake --build build_pp_IC -j8
```

**`-Dgpu_aware_mpi=OFF` is required** (verified 2026-07-07). Entity's default is ON, which
passes raw GPU device pointers to `MPI_Sendrecv`; the OpenMPI available at runtime reports
`opal_built_with_cuda_support: false` and has no CUDA-capable BTL, so the TCP transport fails
with `mca_btl_tcp_frag_send: writev error ... Bad address` and the run hangs at the first
`CommunicateFields` until the SLURM time limit (this is what killed the 2026-06-04 pp_IC job
8754355). With the flag OFF, Entity stages comm buffers through host mirrors
(`src/framework/domain/comm_mpi.hpp`) and multi-GPU runs work — validated by pp job 8915373.
`build_pp` was rebuilt with OFF on 2026-07-07; **`build_pp_IC` still has it ON and must be
reconfigured before the next pp_IC run.**

**Host compiler landmine** (hit 2026-07-07): the login shell exports
`NVCC_WRAPPER_DEFAULT_COMPILER=/opt/rh/gcc-toolset-13/root/usr/bin/g++` (GCC 13), and CUDA
12.0's `host_config.h` rejects GCC > 12 (`#error -- unsupported GNU version!`). Override to
`/usr/bin/g++` (GCC 8.5, the toolchain of the original working builds) for any Entity rebuild.

For the pp variant use `-B build_pp` and `-Dpgen=.../pgens/pp`. Binaries land at
`build_*/src/entity.xc`; the run directories' `entity.xc` symlinks already point there, so a
rebuild is all that's needed after a pgen edit. Verify the symlink still resolves afterwards
(`ls -la radiative/*/entity.xc`). Other useful flags: `-DDEBUG=ON`, `-Dprecision=double`.

On a build issue, read `build_*/CMakeCache.txt` first — it is the ground truth for which pgen
and dependencies each build dir uses.

## Running

```bash
./entity.xc -input <path/to/input.toml>
# Resume from checkpoint:
./entity.xc -input <path/to/input.toml> -restart
```

On the cluster, submit via SLURM (from the run's own `scripts/` dir, so the `../logs/`
SBATCH output path resolves; pp uses a per-run layout since 2026-07-07):

- `radiative/pp/runs/testPP/scripts/gpu_pp.sh` — pp production run (2 L40S, 2 ranks)
- `radiative/pp/runs/bw_aharonian/scripts/gpu_pp_bw.sh` — BW validation run (1 L40S, 1 rank)
- `radiative/pp_IC/scripts/gpu_pp_IC.sh` — pp_IC run (2 L40S, 2 ranks)

All request `--partition=gpuq` and wrap the binary in the shared
`radiative/pp/scripts/bind_gpu.sh` (pp_IC has its own copy), which maps each MPI local rank
to its own GPU via `CUDA_VISIBLE_DEVICES`.

### The OpenMPI/PMIx landmine

The MPI story is messier than "links against system OpenMPI" (corrected 2026-07-07):
`entity.xc` is *compiled* against the module OpenMPI 5.0 headers
(`MPI_CXX_COMPILER=/optnfs/el8/openmpi/5.0/bin/mpicxx` in `CMakeCache.txt`, RUNPATH to
`/optnfs/common/openmpi/5.0/lib`), but at *runtime* the scripts' `LD_LIBRARY_PATH`
(which beats RUNPATH under `--enable-new-dtags`) steers `libmpi.so.40` to the **system
OpenMPI 4.1** in `/usr/lib64/openmpi`, launched by the system `mpirun`. This mixed
configuration is what actually works (validated end-to-end by pp job 8915373). Loading the
`openmpi` module instead mixes PMIx libraries and fails with
`undefined symbol: pmix_output_check_verbosity`. The run scripts set:

```bash
export PATH=/usr/lib64/openmpi/bin:$PATH
export LD_LIBRARY_PATH=/usr/lib64/openmpi/lib:${LD_LIBRARY_PATH:-}
```

and pass `--mca pml ob1 --mca btl self,tcp --mca mtl ^ofi --mca osc ^ucx` to `mpirun` to avoid
OFI/RDMA failures on these nodes. Only `module load cuda/12` is needed.

Output and checkpoints land in `/dartfs-hpc/scratch/f007hd2/radiative/pp` and `.../pp_IC`
(the scripts `cd` there before running). See [hpc-discovery.md](hpc-discovery.md) for the
scratch layout and SLURM discipline.

## Input files (TOML)

See `radiative/entity/input.example.toml` for the full annotated schema. Active inputs:

- `radiative/pp/runs/testPP/inputs/toml_pp.toml` — testPP production input (2560×2560, `runtime = 1000`,
  `epsilon1 = 200`, `simulation.name = "testPP"`). Ran to completion in 447 s on 2 L40S
  (job 8915652, 2026-07-07): 5644 steps, 81 GB in scratch, 100 output steps each of
  fields/particles/spectra; final census 4.6e7 photons, 6.3e6 + 6.3e6 BW secondary pairs,
  species 1/2 empty as expected. Its 512×512 `runtime = 100` predecessor (job 8915373) ran
  in 14 s — the small run was latency-bound, so cost scales far sublinearly with problem
  size. Two caveats for analysis/future runs: the `[output.fields]` quantities list only
  covers species 1/2, which stay empty in the pp regime, so most of the 81 GB is zero-valued
  field data (trim the list or add `N_3`/`N_4`/`N_5` variants); and photon weights are zero
  (known pp pgen issue, see [physics.md](physics.md)), so all `[output.spectra]` output is
  identically zero.
- `radiative/pp/runs/bw_aharonian/inputs/toml_pp_bw_aharonian.toml` — BW validation vs
  Aharonian+ 1983 (512×512, `runtime = 250`, `epsilon1 = 100`, `photonEnergy = 0.1`,
  IC off, full particle dumps). Job 8916768 completed in 20 s on 1 L40S; see the run log
  in [physics.md](physics.md).
- `radiative/pp_IC/inputs/toml_pp_IC.toml` — filled-in pp_IC run (512×512, 5 species,
  `runtime = 1000`, BPFile output)

Key sections: `[simulation]` (engine `"srpic"`), `[grid]`, `[scales]`
(`larmor0 = skindepth0 = 1.0` → σ₀ = B₀ = 1), `[algorithms.fieldsolver] enable = false`
(EM evolution off for the radiative study), `[particles]` (5 species: `e-_p`, `e+_p`, `phot`,
`e-_sec`, `e+_sec`), `[setup]` (pgen parameters — see [physics.md](physics.md)),
`[output]` (`format = "BPFile"`), `[checkpoint]`.
