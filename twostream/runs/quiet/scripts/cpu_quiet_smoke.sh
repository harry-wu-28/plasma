#!/bin/bash
#SBATCH --partition=preemptable
#SBATCH --job-name=ts-quiet-smoke
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --time=0:45:00
#SBATCH --mem=16G
#SBATCH --requeue
#SBATCH --output=../logs/cpu_smoke_%j.out
#SBATCH --error=../logs/cpu_smoke_%j.err

# Quiet-start smoke test: baseline physics, grid and ppc0, evenly spaced initial
# positions (pgens/streaming_quiet), run to t = 300 (~21/omega_p) to measure the noise
# floor the instability amplifies vs the random-start baseline.
# Submit from this scripts/ dir:  sbatch cpu_quiet_smoke.sh
# Requires twostream/entity_quiet_cpu.xc (build_twostream_quiet_cpu).

echo "=== Two-stream quiet-start smoke test (CPU) ==="
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

WORK_DIR=/dartfs-hpc/scratch/f007hd2/twostream/quiet
ENTITY_BIN=$HOME/plasma/twostream/entity_quiet_cpu.xc
INPUT_FILE=$HOME/plasma/twostream/runs/quiet/inputs/quiet_smoke.toml

mkdir -p $WORK_DIR
cd $WORK_DIR
echo "Working directory: $(pwd)"

RESTART_FLAG=""
if compgen -G "quiet_smoke.ckpt/step-*" > /dev/null; then
  RESTART_FLAG="-restart"
  echo "Resuming from checkpoint: $(ls -d quiet_smoke.ckpt/step-* | tail -1)"
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
