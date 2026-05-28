#!/bin/bash
#SBATCH --partition=gpuq
#SBATCH --job-name=turb_gpu
#SBATCH --nodes=1
#SBATCH --gres=gpu:2
#SBATCH --ntasks-per-node=2
#SBATCH --cpus-per-task=4
#SBATCH --time=0:10:00
#SBATCH --mem=5G
#SBATCH --output=../logs/gpu_%j.out
#SBATCH --error=../logs/gpu_%j.err

echo "=== GPU Turbulence Simulation ==="
echo "Start: $(date)"
echo "Node: $(hostname)"

# Load modules
module purge
module load cuda/12
module load openmpi/4.1.3

echo -e "\n=== Loaded Modules ==="
module list

# Environment
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OMP_PROC_BIND=spread
export OMP_PLACES=threads

export OMPI_MCA_orte_base_help_aggregate=0

# Dependencies
export Kokkos_ROOT=/dartfs-hpc/rc/home/5/f007gj5/kokkos/build
export adios2_ROOT=/dartfs-hpc/rc/home/5/f007gj5/ADIOS2/build
export HDF5_ROOT=/dartfs-hpc/rc/home/5/f007gj5/hdf5src/build/hdf5_install

# Paths
WORK_DIR=/dartfs-hpc/scratch/f007hd2/turb2d
ENTITY_BIN=$HOME/plasma/turb2d/turbulence_2d/entity.xc
INPUT_FILE=$HOME/plasma/turb2d/turbulence_2d/inputs/turb_2d_GPU.toml

# GPU info
echo -e "\n=== GPU Information ==="
nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv

# Change to work directory
mkdir -p $WORK_DIR
cd $WORK_DIR
echo -e "\n=== Working Directory ==="
echo "$(pwd)"
ls -lh

START_TIME=$(date +%s)
mpirun -np 2 \
  --bind-to core --map-by ppr:2:node:PE=4 \
  $ENTITY_BIN -input $INPUT_FILE
EXIT_CODE=$?
END_TIME=$(date +%s)
echo "Elapsed time: $((END_TIME - START_TIME)) seconds"

# Results
echo -e "\n=== Finished ==="
echo "Exit code: $EXIT_CODE"
echo "End: $(date)"

exit $EXIT_CODE
