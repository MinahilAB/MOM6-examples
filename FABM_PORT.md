# FABM port compatibility and regression workflow

## Branch pairing

This branch (`fabm-port-examples`) is the examples-side companion to
`MOM6/fabm-port`.  The generic bridge is maintained in MOM6; this repository
contains coupled source dependencies, case configurations and regression
recipes.  The exact tested revisions at the time this document was added are:

```text
MOM6 fabm-port:                   1c0caa3e1895bdae9c227d93355b4e5fa487d7d7
MOM6-examples fabm-port-examples: 84135d3688755ffb407712de1bce68a700f35f3e
FABM:                             f85de87ae0ab0bb42c1bf65ed6fdda4fa5ca5813
```

Update these values only after a successful regression run.  A future public
release should pin MOM6 as the `src/MOM6` submodule, or provide an equivalent
machine-readable compatibility manifest.

## Coupled FABM build

Load the site compiler, MPI and NetCDF modules, then run the tracked wrapper:

```bash
cd MOM6-examples
export FABM_ROOT=/absolute/path/to/fabm-install
export MOM6_ROOT=/absolute/path/to/MOM6
BUILD_DIR="/build_fabm_sis2" ./build_fabm_sis2.sh
```

For a non-destructive regression build while retaining an older executable, use
`BUILD_DIR="/build_fabm_sis2_portable"`. The script generates
`/MOM6` and does not edit generated Makefiles.

The coupled build must compile MOM6 with all of the following:

```text
-D_FABM_
-I${FABM_ROOT}/include
-L${FABM_ROOT}/lib64 -lfabm
```

`FABM_ROOT` must be built with the same MPI compiler and floating-point kind
as the MOM6/SIS2 executable.  Build directories (`build_fabm*`), datasets,
NetCDF output and restart directories are intentionally ignored by Git.

## OM1 synthetic-initialization regression

The isolated case `ice_ocean_SIS2/OM_1deg_fabm_ic_test` is a local regression
case and is not a small distributable test: it requires the OM1 input dataset.
It uses a synthetic file linked as:

```text
INPUT/fabm_npzd_initial.nc
```

and enables:

```text
USE_FABM_TRACERS = True
FABM_CONFIG_FILE = "fabm.yaml"
FABM_INITIAL_CONDITIONS_FILE = "INPUT/fabm_npzd_initial.nc"
FABM_INITIAL_CONDITIONS_ON_GRID = True
```

The 2026-09-03 one-day regression completed successfully with Slurm job
`22166947` (exit code `0`) and produced
`19580101.ocean_fabm__1958_002.nc`.  Its log includes `Initialize from Z` and
`Initialize tracer from Z`, verifying that MOM6’s standard NetCDF
initialization machinery was called for the FABM state variables.

Before rerunning, copy the case or move existing `*.nc`, `RESTART*`, `*.out`
and `*.err` files to an archive directory.  Do not overwrite a known-good
result.  A 16-rank one-day test uses:

```bash
cd ice_ocean_SIS2/OM_1deg_fabm_ic_test
srun --nodes=1 --ntasks=16 --ntasks-per-node=16 ./MOM6
```

Check completion with `sacct -j JOBID -X --format=JobID,State,ExitCode,Elapsed`
and inspect the log for `FABM`, `Initialize tracer from Z`, `FATAL`, and
`ERROR`.

## Scope boundary

The earlier `runoff_carbon` build issue is an interface-version mismatch
between the MOM6 and SIS2/coupler source revisions.  It is not part of the
FABM bridge.  Resolve it by pinning/rebasing to a compatible MOM6/SIS2 pair
(or by a separately reviewed interface port); do not hide it in FABM logic.
