#!/bin/bash
#SBATCH --partition=gpuq
#SBATCH --job-name=rad-gpu
#SBATCH --nodes=1
#SBATCH --gres=gpu:l40s:2
#SBATCH --ntasks-per-node=2
#SBATCH --cpus-per-task=4
#SBATCH --time=4:00:00
#SBATCH --mem=16G
#SBATCH --output=../logs/gpu_%j.out
#SBATCH --error=../logs/gpu_%j.err

echo "=== GPU PP Simulation ==="
echo "Start: $(date)"
echo "Node: $(hostname)"

# Load modules
module purge
module load cuda/12

# entity.xc is linked against the system OpenMPI in /usr/lib64/openmpi.
# Loading the openmpi/4.1.3 module mixes MPI/PMIx libraries and causes:
#   undefined symbol: pmix_output_check_verbosity
export PATH=/usr/lib64/openmpi/bin:$PATH
export LD_LIBRARY_PATH=/usr/lib64/openmpi/lib:${LD_LIBRARY_PATH:-}

echo -e "\n=== Loaded Modules ==="
module list

# Avoid OFI/UCX RDMA transports on this node; OFI fails on irdma1 with
# "fi_endpoint: Invalid argument" / "Operation not permitted".
export OMPI_MCA_orte_base_help_aggregate=0

# Paths
WORK_DIR=/dartfs-hpc/scratch/f007hd2/radiative/pp
ENTITY_BIN=$HOME/plasma/radiative/pp/entity.xc
INPUT_FILE=$HOME/plasma/radiative/pp/inputs/toml_pp.toml

# GPU info
echo -e "\n=== GPU Information ==="
nvidia-smi --query-gpu=index,name,memory.total,memory.free,memory.used --format=csv

# Change to work directory
mkdir -p $WORK_DIR
cd $WORK_DIR
echo -e "\n=== Working Directory ==="
echo "$(pwd)"
ls -lh

START_TIME=$(date +%s)
mpirun -np $SLURM_NTASKS \
  --mca pml ob1 \
  --mca btl self,tcp \
  --mca mtl ^ofi \
  --mca osc ^ucx \
  $HOME/plasma/radiative/pp/scripts/bind_gpu.sh \
  $ENTITY_BIN -input $INPUT_FILE
EXIT_CODE=$?
END_TIME=$(date +%s)
echo "Elapsed time: $((END_TIME - START_TIME)) seconds"

# Results
echo -e "\n=== Finished ==="
echo "Exit code: $EXIT_CODE"
echo "End: $(date)"

exit $EXIT_CODE
