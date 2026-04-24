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

module load python/3.13.13
module load openfoam/v2312
module load paraview/6.1.0

python3 solve.py