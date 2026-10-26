# MOM6--FABM--BFM installation and compatibility guide

This branch is the examples-side companion to the generic FABM bridge on
[`MinahilAB/MOM6:fabm-port`](https://github.com/MinahilAB/MOM6/tree/fabm-port).
MOM6 owns the bridge source; this repository supplies the coupled MOM6--SIS2
build wrapper, a compatible SIS2 revision, and generic initial-condition
preparation tools.

The workflow is portable across HPC systems. Site-specific module names,
compiler flags, Slurm scripts, input data, and case namelists are deliberately
**not** committed here.

## Compatibility set

This branch pins SIS2 as a Git submodule to the FABM-compatible commit from
[`MinahilAB/SIS2:fabm-port-sis2`](https://github.com/MinahilAB/SIS2/tree/fabm-port-sis2).
That revision provides the coupled ice-fraction interface used by FABM/BFM
light calculations and avoids the `runoff_carbon` interface mismatch between
the MOM6 bridge source and the newer SIS2 driver source.

Record the exact revisions for every experiment:

```bash
git -C /path/to/MOM6 rev-parse HEAD
git -C /path/to/MOM6-examples rev-parse HEAD
git -C /path/to/MOM6-examples/src/SIS2 rev-parse HEAD
git -C /path/to/fabm rev-parse HEAD
git -C /path/to/bfmforfabm-iron rev-parse HEAD  # only for iron-enabled BFM
```

## Clone the source

Clone the MOM6 bridge and this examples branch separately. The build wrapper
uses the explicit `MOM6_ROOT` below, so it does not accidentally compile the
unmodified upstream `src/MOM6` submodule bundled by the examples repository.

```bash
git clone --recurse-submodules --branch fabm-port \
  git@github.com:MinahilAB/MOM6.git MOM6

git clone --recurse-submodules --branch fabm-port-examples \
  git@github.com:MinahilAB/MOM6-examples.git MOM6-examples
```

Verify that the patched SIS2 source was obtained:

```bash
git -C MOM6-examples submodule status src/SIS2
git -C MOM6-examples/src/SIS2 log -1 --oneline
```

No fork of FMS is required: FMS is used unchanged.

## Build and install FABM

Build FABM with the same Fortran compiler, MPI implementation, NetCDF stack,
and real kind used for MOM6. `FABM_ROOT` means an **installation prefix**, not
the FABM source directory and not a CMake build directory. It must contain
`include/fabm.mod` and either `lib/libfabm.*` or `lib64/libfabm.*`.

For ordinary FABM, follow the FABM build documentation for the selected host
API. For the iron-enabled BFM configuration used in this project, clone the
matching BFM source and build FABM against it, for example:

```bash
git clone --recurse-submodules --branch iron \
  https://github.com/inogs/bfmforfabm.git bfmforfabm-iron

cmake -S fabm -B build-fabm-bfm-iron \
  -DFABM_HOST=mom5 \
  -DFABM_REAL_KIND='selected_real_kind(13)' \
  -DCMAKE_Fortran_COMPILER=mpiifort \
  -DCMAKE_BUILD_TYPE=Release \
  -DFABM_OGS_BASE="$PWD/bfmforfabm-iron" \
  -DCMAKE_INSTALL_PREFIX="$PWD/local/fabm/mom6-bfm-iron"

cmake --build build-fabm-bfm-iron -- -j 8
cmake --install build-fabm-bfm-iron
```

`FABM_HOST=mom5` selects the FABM host API and precision conventions required
by this bridge; it does **not** build or run MOM5. The BFM build may provide
an additional `libadj` library. The coupled build wrapper detects and links it
automatically.

## Build a coupled MOM6--SIS2--FABM executable

Load the compiler, MPI, and NetCDF modules for the local system first. Then
select a compatible mkmf template. The wrapper default is the G100 Intel
template, so users on another machine should set `MK_TEMPLATE` explicitly.

```bash
cd MOM6-examples

export MOM6_ROOT="$(cd ../MOM6 && pwd)"
export FABM_ROOT="/absolute/path/to/local/fabm/mom6-bfm-iron"

# Example only: choose or adapt a template appropriate to the local compiler.
export MK_TEMPLATE="$PWD/src/mkmf/templates/linux-intel.mk"

# Keep generated objects outside the source tree, preferably on scratch.
export BUILD_DIR="$PWD/build_fabm_sis2"
export JOBS=8

./build_fabm_sis2.sh
```

The executable is created at `${BUILD_DIR}/MOM6`. The wrapper compiles with
`-D_FABM_`, supplies the FABM module include directory, links `libfabm`, and
links `libadj` when an OGS/BFM installation provides it. Do not commit build
directories, executable files, NetCDF data, output, or restart directories.

On a new HPC system, inspect the available templates before building:

```bash
find src/mkmf/templates -maxdepth 1 -type f | sort
```

Usually a site-specific copy of a suitable Intel or GNU template is needed to
set the compiler, MPI wrapper, NetCDF paths, and scheduler-independent flags.

## Runtime configuration

Compile-time FABM support is enabled by the build above. A particular MOM6
case opts into it at runtime, for example in `MOM_override`:

```text
USE_FABM_TRACERS = True
FABM_CONFIG_FILE = "fabm.yaml"
```

The YAML file declares the FABM or BFM model and its interior state variables.
For cold starts from a tracer NetCDF file, add:

```text
FABM_INITIAL_CONDITIONS_FILE = "INPUT/fabm_initial_conditions.nc"
FABM_INITIAL_CONDITIONS_ON_GRID = True
```

The file must provide every active FABM interior state with the names and units
expected by the YAML configuration. On restart runs, MOM6 restart files take
precedence over this initial-condition file.

Further bridge settings, forcing fallbacks, vertical-movement CFL protection,
and current limitations are documented in
[`MOM6/docs/FABM.md`](https://github.com/MinahilAB/MOM6/blob/fabm-port/docs/FABM.md).

## Generic preparation tools

[`tools/fabm/`](tools/fabm/) contains reusable Python utilities and sample
YAML/mapping files for regridding source biogeochemistry, mapping fields to
FABM state names, and assembling a complete iron-enabled BFM initial-condition
file. They require Python 3.8 or newer plus the packages listed in their
[`README`](tools/fabm/README.md). They are examples, not a complete MOM6 experiment: users must supply
their own grid, forcing, data licence compliance, timestep, diagnostics, and
scientific validation.

## Verification checklist

Before relying on a new installation, perform these checks:

```bash
bash -n build_fabm_sis2.sh
python3 -m py_compile tools/fabm/*.py
git diff --check
```

Then make a short case-specific run with a known FABM YAML and inspect the log
for FABM initialization. A successful build alone does not validate a
scientific BFM experiment. Archive the exact source revisions, modules,
compiler/MPI versions, YAML, namelists, initial-condition provenance, and
diagnostic table alongside every published result.

## Scope and current limitations

The bridge supports generic **interior** FABM state variables, interior
sources, surface and bottom fluxes on those tracers, vertical movement, MOM6
restart handling, and the MOM6--SIS2 ice-fraction path required by BFM light.

Surface-attached and bottom-attached FABM state variables are not yet
implemented. Density is reference-density based; configurations requiring
in-situ density need a dedicated EOS connection. Initial conditions and
forcing require scientific validation for each application.
