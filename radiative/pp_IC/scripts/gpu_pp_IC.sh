#!/bin/bash
#SBATCH --partition=gpuq
#SBATCH --job-name=rad-gpu
#SBATCH --nodes=1
#SBATCH --gres=gpu:2
#SBATCH --ntasks-per-node=2
#SBATCH --cpus-per-task=4
#SBATCH --time=0:20:00
#SBATCH --mem=10G
#SBATCH --output=../logs/gpu_%j.out
#SBATCH --error=../logs/gpu_%j.err

echo "=== GPU Turbulence Simulation ==="
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

# Environment
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OMP_PROC_BIND=spread
export OMP_PLACES=threads

# Avoid OFI/UCX RDMA transports on this node; OFI fails on irdma1 with
# "fi_endpoint: Invalid argument" / "Operation not permitted".
export OMPI_MCA_pml="ob1"
export OMPI_MCA_btl="self,vader,tcp"
export OMPI_MCA_mtl="^ofi"
export OMPI_MCA_osc="^ucx"
export OMPI_MCA_orte_base_help_aggregate=0

# Dependencies
export Kokkos_ROOT=/dartfs-hpc/rc/home/5/f007gj5/kokkos/build
export adios2_ROOT=/dartfs-hpc/rc/home/5/f007gj5/ADIOS2/build
export HDF5_ROOT=/dartfs-hpc/rc/home/5/f007gj5/hdf5src/build/hdf5_install

# Paths
WORK_DIR=/dartfs-hpc/scratch/f007hd2/radiative/pp_IC
ENTITY_BIN=$HOME/plasma/radiative/pp_IC/entity.xc
INPUT_FILE=$HOME/plasma/radiative/pp_IC/inputs/toml_pp_IC.toml

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
mpirun -np $SLURM_NTASKS \
  --mca pml ob1 \
  --mca btl self,tcp \
  --mca mtl ^ofi \
  --mca osc ^ucx \
  $ENTITY_BIN -input $INPUT_FILE
EXIT_CODE=$?
END_TIME=$(date +%s)
echo "Elapsed time: $((END_TIME - START_TIME)) seconds"

# Results
echo -e "\n=== Finished ==="
echo "Exit code: $EXIT_CODE"
echo "End: $(date)"

exit $EXIT_CODE
