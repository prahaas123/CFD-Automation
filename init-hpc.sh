#!/bin/sh

# check if python is installed and is version 3.13
PYTHON_VERSION=$(python3 -c "import sys; print(str(sys.version_info.major) + '.' + str(sys.version_info.minor))")
if [ "$PYTHON_VERSION" = "3.13" ]; then
    echo "You are using Python 3.13."
else
    echo "Python version $PYTHON_VERSION detected. Requires Python 3.13."
fi

# create virtual environment
echo "Creating virtual environment"
virtualenv .venv

# activate virtual environment
echo "Activating virtual environment"
source .venv/bin/activate

# install python dependencies
echo "Installing Python dependencies"
pip install -r requirements-hpc.txt

# ensure SQUEUE_FORMAT is configred for simple-slurm
echo "Configuring SQUEUE_FORMAT for simple-slurm"
export SQUEUE_FORMAT='%i","%j","%t","%M","%L","%D","%C","%m","%b","%R'
echo "SQUEUE_FORMAT=$SQUEUE_FORMAT"

echo 'Initialized for HPC!'