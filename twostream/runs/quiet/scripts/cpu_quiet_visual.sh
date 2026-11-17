#!/bin/bash
#SBATCH --partition=preemptable
#SBATCH --job-name=ts-quiet-visual
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --time=5:00:00
#SBATCH --mem=32G
#SBATCH --requeue
#SBATCH --output=../logs/cpu_visual_%j.out
#SBATCH --error=../logs/cpu_visual_%j.err

# Quiet-start two-stream run for the talk visuals (movie, fastest-mode growth, space-time):
# baseline physics with evenly spaced initial positions (pgens/streaming_quiet), ppc0 = 64,
# to t = 1000 (70/omega_p). 1 MPI rank x 32 OpenMP threads (the account limit is 32 CPUs
# per user). Resumes from the latest checkpoint if requeued.
# Submit from this scripts/ dir:  sbatch cpu_quiet_visual.sh

echo "=== Two-stream quiet-start visual run (CPU, ${SLURM_NNODES} nodes x ${SLURM_NTASKS_PER_NODE} ranks) ==="
echo "Start: $(date)"
echo "Nodes: ${SLURM_JOB_NODELIST}  restart count: ${SLURM_RESTART_COUNT:-0}"

module purge

# entity.xc uses the system OpenMPI at runtime; never load the openmpi module
# (PMIx symbol conflict). See docs/building-and-running.md.
export PATH=/usr/lib64/openmpi/bin:$PATH
export LD_LIBRARY_PATH=/usr/lib64/openmpi/lib:/opt/rh/gcc-toolset-13/root/usr/lib64:${LD_LIBRARY_PATH:-}
export OMPI_MCA_orte_base_help_aggregate=0

export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK}
export OMP_PROC_BIND=spread
export OMP_PLACES=threads

WORK_DIR=/dartfs-hpc/scratch/f007hd2/twostream/quiet
ENTITY_BIN=$HOME/plasma/twostream/entity_quiet_cpu.xc
INPUT_FILE=$HOME/plasma/twostream/runs/quiet/inputs/quiet_visual.toml

mkdir -p $WORK_DIR
cd $WORK_DIR
echo "Working directory: $(pwd)"

RESTART_FLAG=""
if compgen -G "quiet_visual.ckpt/step-*" > /dev/null; then
  RESTART_FLAG="-restart"
  echo "Resuming from checkpoint: $(ls -d quiet_visual.ckpt/step-* | tail -1)"
fi

START_TIME=$(date +%s)
# 2 ranks per node, unbound so each rank's OpenMP threads can spread over its half of the
# node; -x forwards the environment to the ranks on the second node.
mpirun -np $SLURM_NTASKS --map-by ppr:${SLURM_NTASKS_PER_NODE}:node --bind-to none \
  -x PATH -x LD_LIBRARY_PATH -x OMP_NUM_THREADS -x OMP_PROC_BIND -x OMP_PLACES \
  -x OMPI_MCA_orte_base_help_aggregate \
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
