#!/bin/bash
#SBATCH --partition=gpuq
#SBATCH --job-name=twostream-base
#SBATCH --nodes=1
#SBATCH --gres=gpu:l40s:1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --time=2:00:00
#SBATCH --mem=16G
#SBATCH --output=../logs/gpu_%j.out
#SBATCH --error=../logs/gpu_%j.err

# Two-stream baseline (upstream v1.3.3 twostream.toml), 1D, 12288 cells, single GPU.
# ~2.4e5 steps, ~4e5 particles: small, latency-bound. Submit from this scripts/ dir
# so ../logs/ resolves:  mkdir -p ../logs && sbatch gpu_twostream.sh
# Requires entity_s1.xc from twostream/scripts/build_twostream.sh.

echo "=== Two-stream baseline ==="
echo "Start: $(date)"
echo "Node: $(hostname)"

module purge
module load cuda/12

# entity.xc uses the system OpenMPI at runtime; never load the openmpi module
# (PMIx symbol conflict). See docs/building-and-running.md.
export PATH=/usr/lib64/openmpi/bin:$PATH
export LD_LIBRARY_PATH=/usr/lib64/openmpi/lib:${LD_LIBRARY_PATH:-}
export OMPI_MCA_orte_base_help_aggregate=0

# Entity writes output into <WORK_DIR>/<simulation.name>/
WORK_DIR=/dartfs-hpc/scratch/f007hd2/twostream
ENTITY_BIN=$HOME/plasma/twostream/entity_s1.xc
INPUT_FILE=$HOME/plasma/twostream/runs/baseline/inputs/twostream_baseline.toml

nvidia-smi --query-gpu=index,name,memory.total,memory.free,memory.used --format=csv

mkdir -p $WORK_DIR
cd $WORK_DIR
echo "Working directory: $(pwd)"

START_TIME=$(date +%s)
mpirun -np $SLURM_NTASKS \
  --mca pml ob1 \
  --mca btl self,tcp \
  --mca mtl ^ofi \
  --mca osc ^ucx \
  $HOME/plasma/twostream/scripts/bind_gpu.sh \
  $ENTITY_BIN -input $INPUT_FILE
EXIT_CODE=$?
END_TIME=$(date +%s)
echo "Elapsed time: $((END_TIME - START_TIME)) seconds"
echo "Exit code: $EXIT_CODE"
echo "End: $(date)"
exit $EXIT_CODE
