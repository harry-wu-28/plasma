#!/bin/bash
# Configure + build entity.xc for the two-stream study (streaming pgen, 1D-capable).
# Run on a Discovery login/GPU node from anywhere:
#   bash twostream/scripts/build_twostream.sh            # shape order 1 (default)
#   SHAPE_ORDER=3 bash twostream/scripts/build_twostream.sh
# Each shape order gets its own build dir, since shape order is a compile-time flag
# (-Dshape_order, zigzag deposit). The pgen is pgens/streaming (verbatim Entity v1.3.3).
#
# ENTITY_DIR defaults to the existing checkout (upstream v1.3.3rc). If the pgen fails to
# compile there, point ENTITY_DIR at a clean `git clone --branch v1.3.3` checkout.
set -euo pipefail

SHAPE_ORDER=${SHAPE_ORDER:-1}
REPO=${REPO:-$HOME/plasma}
ENTITY_DIR=${ENTITY_DIR:-$REPO/radiative/entity}
BUILD_DIR=build_twostream_s${SHAPE_ORDER}

module load cuda/12
# CUDA 12.0 rejects GCC > 12; see docs/building-and-running.md "host compiler landmine".
export NVCC_WRAPPER_DEFAULT_COMPILER=/usr/bin/g++

cd "$ENTITY_DIR"
cmake -B "$BUILD_DIR" \
  -Dpgen="$REPO/pgens/streaming" \
  -Dshape_order="$SHAPE_ORDER" \
  -Dmpi=ON -Doutput=ON -Dprecision=single \
  -Dgpu_aware_mpi=OFF \
  -DKokkos_ROOT=/dartfs-hpc/rc/home/2/f007hd2/dependencies/kokkos/install \
  -Dadios2_ROOT=/dartfs-hpc/rc/home/5/f007gj5/ADIOS2/build \
  -DHDF5_ROOT=/dartfs-hpc/rc/home/5/f007gj5/hdf5src/build/hdf5_install
cmake --build "$BUILD_DIR" -j8

# Per-shape-order symlink used by the SLURM scripts (entity.xc symlinks are gitignored).
ln -sfn "$ENTITY_DIR/$BUILD_DIR/src/entity.xc" "$REPO/twostream/entity_s${SHAPE_ORDER}.xc"
ls -la "$REPO/twostream/entity_s${SHAPE_ORDER}.xc"
