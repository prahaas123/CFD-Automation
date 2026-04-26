#!/bin/sh

#SBATCH --job-name=Wing
#SBATCH --account=def-jphickey
#SBATCH --time=6-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=50
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=2G
#SBATCH --output=Wing.log
#SBATCH --open-mode=append

module load StdEnv/2023
module load gcc/12.3
module load openmpi/4.1.5
module load paraview/6.0.0
module load python/3.13.2
module load openfoam/v2312
source .venv/bin/activate

python3 solve.py