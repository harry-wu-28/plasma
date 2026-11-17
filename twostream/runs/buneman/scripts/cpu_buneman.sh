#!/bin/bash
#SBATCH --partition=preemptable
#SBATCH --job-name=buneman-cpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --time=24:00:00
#SBATCH --mem=32G
#SBATCH --requeue
#SBATCH --output=../logs/cpu_%j.out
#SBATCH --error=../logs/cpu_%j.err

# Electron beam through stationary ions (Chen §6.6, Buneman), CPU (OpenMP Kokkos),
# 1 rank x 32 threads. Same binary as the e-e baseline (streaming pgen, unmodified).
# Submit from this scripts/ dir:  sbatch cpu_buneman.sh
# Resumes from the latest checkpoint (<WORK_DIR>/buneman.ckpt/step-*) if requeued.

echo "=== Buneman: e- beam through ions (CPU) ==="
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

WORK_DIR=/dartfs-hpc/scratch/f007hd2/twostream/cpu
ENTITY_BIN=$HOME/plasma/twostream/entity_cpu.xc
INPUT_FILE=$HOME/plasma/twostream/runs/buneman/inputs/buneman.toml

mkdir -p $WORK_DIR
cd $WORK_DIR
echo "Working directory: $(pwd)"

RESTART_FLAG=""
if compgen -G "buneman.ckpt/step-*" > /dev/null; then
  RESTART_FLAG="-restart"
  echo "Resuming from checkpoint: $(ls -d buneman.ckpt/step-* | tail -1)"
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
