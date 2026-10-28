#!/usr/bin/env bash
# One-day, 16-rank MOM6--SIS2--FABM--BFM smoke test for OM_1deg.
#
# This is a portable Slurm template, not a complete experiment setup. Before
# submission, stage the OM1 external INPUT dataset, copy the smoke-specific
# MOM_override/diag_table/input.nml/layout files into the run directory, and
# link ./MOM6 to a locally built coupled executable. Adapt account, partition,
# modules, and task layout for the local machine.
#
# The tested 4x4 layout uses 16 MPI ranks. This short run validates software
# integration only; it is not intended for scientific interpretation.
#SBATCH --job-name=OM1_BFM_smoke
#SBATCH --output=om1_bfm_smoke_%j.out
#SBATCH --error=om1_bfm_smoke_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=16
#SBATCH --ntasks-per-node=16
#SBATCH --time=00:30:00

set -euo pipefail

# Load the compiler, MPI, and NetCDF modules that match the executable build.
# For example, add the site-specific `module load ...` commands here in a local
# copy.  Set #SBATCH --account and #SBATCH --partition above if required.

test -x ./MOM6 || {
  echo "ERROR: ./MOM6 is missing or is not executable." >&2
  exit 2
}

srun ./MOM6
