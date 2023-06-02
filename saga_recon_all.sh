#!/bin/bash
# Job name:
#SBATCH --job-name=jorgennr_recon_all
#
# Project:
#SBATCH --account=nn9279k
#SBATCH --time='48:00:00'
#
# Max memory usage per task
#SBATCH --mem-per-cpu=20000M
#
# Number of tasks (cores):
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1

# System setup
set -o errexit  # Exit the script on any error
set -o nounset  # Treat any unset variables as an error

module --quiet purge  # Reset the modules to the system default
module load FreeSurfer/7.2.0-GCCcore-11.2.0
module list  # easier debugging

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
OUTPUT_DIR="$SCRIPT_DIR/RECONNED/"
mkdir $OUTPUT_DIR

# Command to copy files to some specific location after job end.
cleanup "cp -r $SCRATCH/$1 /cluster/projects/nn9279k/jorgennr/parkrec/$OUTPUT_DIR/$1"

echo $SCRATCH
echo `date`
echo "subjid=$1, T1=$2, T2=$3"

cp -t $SCRATCH $2 $3 -r
recon-all -sd $SCRATCH -subjid $1 -i $2 -T2 $3 -T2pial
