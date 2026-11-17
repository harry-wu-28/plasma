#!/bin/bash
#SBATCH --partition=preemptable
#SBATCH --job-name=twostream-cpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --time=6:00:00
#SBATCH --mem=16G
#SBATCH --requeue
#SBATCH --output=../logs/cpu_%j.out
#SBATCH --error=../logs/cpu_%j.err

# Two-stream baseline on CPU (OpenMP Kokkos), 1 rank x 16 threads.
# Submit from this scripts/ dir:  mkdir -p ../logs && sbatch cpu_twostream.sh
# Requires twostream/entity_cpu.xc (build_twostream_cpu, Kokkos 4.7.01 OpenMP).
# preemptable jobs can be killed and requeued: resumes from the latest checkpoint
# (<WORK_DIR>/twostream_baseline.ckpt/step-*) when one exists.

echo "=== Two-stream baseline (CPU) ==="
echo "Start: $(date)"
echo "Node: $(hostname)  restart count: ${SLURM_RESTART_COUNT:-0}"

module purge

# entity.xc uses the system OpenMPI at runtime; never load the openmpi module
# (PMIx symbol conflict). See docs/building-and-running.md.
export PATH=/usr/lib64/openmpi/bin:$PATH
export LD_LIBRARY_PATH=/usr/lib64/openmpi/lib:/opt/rh/gcc-toolset-13/root/usr/lib64:${LD_LIBRARY_PATH:-}
export OMPI_MCA_orte_base_help_aggregate=0

export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK}
export OMP_PROC_BIND=spread
export OMP_PLACES=threads

# Separate from the GPU run's output dir so the two never collide.
WORK_DIR=/dartfs-hpc/scratch/f007hd2/twostream/cpu
ENTITY_BIN=$HOME/plasma/twostream/entity_cpu.xc
INPUT_FILE=$HOME/plasma/twostream/runs/baseline/inputs/twostream_baseline.toml

mkdir -p $WORK_DIR
cd $WORK_DIR
echo "Working directory: $(pwd)"

RESTART_FLAG=""
if compgen -G "twostream_baseline.ckpt/step-*" > /dev/null; then
  RESTART_FLAG="-restart"
  echo "Resuming from checkpoint: $(ls -d twostream_baseline.ckpt/step-* | tail -1)"
fi

START_TIME=$(date +%s)
# --bind-to none: OpenMPI otherwise pins the single rank to one core, serializing OpenMP.
mpirun -np $SLURM_NTASKS --bind-to none \
  --mca pml ob1 \
  --mca btl self,tcp \
  --mca mtl ^ofi \
  --mca osc ^ucx \
  $ENTITY_BIN -input $INPUT_FILE $RESTART_FLAG
EXIT_CODE=$?
END_TIME=$(date +%s)
echo "Elapsed time: $((END_TIME - START_TIME)) seconds"
echo "Exit code: $EXIT_CODE"
echo "End: $(date)"
exit $EXIT_CODE
