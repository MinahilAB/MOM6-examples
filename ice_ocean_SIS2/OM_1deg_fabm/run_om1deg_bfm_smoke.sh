#!/usr/bin/env bash
# One-day, 16-rank BFM/OGS bridge smoke test for OM_1deg.
# The caller stages MOM_override.bfm_smoke, diag_table.bfm_smoke, a one-day
# input.nml, the 4x4 layouts, and the BFM-linked MOM6 symlink before submission.
# It is deliberately small: this validates integration, not scientific tuning.
#SBATCH --job-name=OM1_BFM_smoke
#SBATCH --output=om1_bfm_smoke_%j.out
#SBATCH --error=om1_bfm_smoke_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=16
#SBATCH --ntasks-per-node=16
#SBATCH --time=00:30:00
#SBATCH --account=OGS_test2528
#SBATCH --partition=g100_usr_prod

set -euo pipefail
module purge
module load intel-oneapi-compilers/2021.4.0
module load intel-oneapi-mpi/2021.4.0
module load netcdf-fortran/4.5.3--intel-oneapi-mpi--2021.4.0--intel--2021.4.0

srun --nodes=1 --ntasks=16 --ntasks-per-node=16 ./MOM6
