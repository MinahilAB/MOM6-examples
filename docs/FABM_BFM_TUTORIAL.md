# MOM6--FABM--BFM reproducibility guide

This guide documents the portable workflow developed for the `fabm-port`
MOM6 bridge and its MOM6--SIS2 examples. It separates a technically verified
coupling workflow from scientific validation of any particular ecosystem
configuration. The source bridge is maintained in MOM6; this repository
contains coupled-build support, small case overlays, and reusable preparation
tools. Large input archives, executables, restart files, and model output are
intentionally excluded from Git.

## 1. Scope and supported configurations

The bridge dynamically registers FABM **interior** state variables as MOM6
tracers. MOM6 owns their transport, restart handling and diagnostics; FABM
calculates biological sources, diagnostics, fluxes and relative vertical
movement. Surface- and bottom-attached FABM state variables are not yet
supported.

The bridge supports source tendencies, diagnostics, surface/bottom fluxes
*into an interior state*, and relative vertical movement. It does not yet
provide MOM6 storage, restart, or diagnostics for truly two-dimensional
surface-attached or bottom-attached FABM state variables. A successful run
therefore establishes technical coupling, not automatic scientific validation.

| Configuration | FABM library | MOM6 executable | Intended use |
|---|---|---|---|
| Physics only | none | standard MOM6 or MOM6--SIS2 | physical baseline |
| Ocean-only FABM | FABM | ocean-only FABM build | KPP/NPZD testing |
| MOM6--SIS2--FABM | FABM | coupled FABM build | sea-ice/ocean NPZD |
| MOM6--SIS2--BFM | FABM plus BFM | coupled BFM build | BFM technical tests |
| MOM6--SIS2--BFM--Fe | FABM plus iron BFM | iron-enabled BFM build | OM1 reference workflow |

## 2. Repository and revision matrix

Use matching, recorded revisions of MOM6, MOM6-examples, SIS2, FABM and, when
needed, BFM. The examples repository supplies the compatible SIS2 submodule
revision and case-side build wrapper; the bridge source is maintained in MOM6.

For a clean installation, initialise the source trees and their submodules:

```bash
git clone --recursive --branch fabm-port \
  git@github.com:MinahilAB/MOM6.git MOM6
git clone --recursive --branch fabm-port-examples \
  git@github.com:MinahilAB/MOM6-examples.git MOM6-examples
git clone --recursive https://github.com/fabm-model/fabm.git fabm
```

For BFM, obtain the BFM/OGS source revision appropriate to the selected YAML
and initialise any required submodules. The BFM source is an input to the
FABM build; it is not bundled with MOM6.

```bash
git -C /path/to/MOM6 rev-parse HEAD
git -C /path/to/MOM6-examples rev-parse HEAD
git -C /path/to/MOM6-examples/src/SIS2 rev-parse HEAD
git -C /path/to/fabm rev-parse HEAD
git -C /path/to/bfmforfabm-iron rev-parse HEAD   # iron BFM only
```

Use unambiguous paths in scripts:

```bash
export MOM6_ROOT=/absolute/path/to/MOM6
export EXAMPLES_ROOT=/absolute/path/to/MOM6-examples
export FABM_SOURCE=/absolute/path/to/fabm

# FABM_ROOT is the CMake installation prefix, not FABM_SOURCE.
# It must contain include/fabm.mod and lib/ or lib64/libfabm.*.
export FABM_ROOT=/absolute/path/to/local/fabm/mom6-bfm-iron
```

## 3. Documentation map

- [`../FABM_PORT.md`](../FABM_PORT.md) describes compatibility, builds and
  bridge-level runtime settings.
- [`../tools/fabm/README.md`](../tools/fabm/README.md) describes reusable
  configuration and initial-condition preparation tools.
- [`../tools/fabm/configurations/`](../tools/fabm/configurations/) contains
  tested NPZD and BFM YAML examples.
- [`../tools/fabm/templates/`](../tools/fabm/templates/) contains portable
  override and diagnostic-table fragments.

## 4. Build workflow

The FABM library and MOM6 executable must use one compatible compiler, MPI and
NetCDF stack. Build directories, executables and libraries are machine-local;
do not commit them. The coupled build wrapper is `build_fabm_sis2.sh` at the
repository root. Set at least:

Record the loaded environment before compiling:

```bash
module list
which mpiifort
nc-config --all
nf-config --all
```

Build and install each materially different FABM dependency combination into a
separate prefix. This avoids replacing a compact NPZD library with a BFM
library. The general standard-FABM pattern is:

```bash
cmake -S "$FABM_SOURCE" -B build-fabm-mom6 \
  -DFABM_HOST=mom5 \
  -DFABM_REAL_KIND='selected_real_kind(13)' \
  -DCMAKE_Fortran_COMPILER=mpiifort \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$FABM_ROOT"
cmake --build build-fabm-mom6 --parallel 8
cmake --install build-fabm-mom6
test -f "$FABM_ROOT/include/fabm.mod"
```

The `mom5` host interface provides the FABM column API used by this bridge;
it does not link MOM5 into MOM6. For BFM or iron BFM, configure FABM against
the corresponding BFM/OGS source and install to a distinct prefix.

```bash
export MOM6_ROOT=/absolute/path/to/MOM6
export FABM_ROOT=/absolute/path/to/local/fabm/mom6-bfm-iron
export MK_TEMPLATE=/absolute/path/to/mkmf-template.mk
export BUILD_DIR=/scratch/path/to/build/mom6-sis2-fabm-bfm
./build_fabm_sis2.sh
```

The wrapper enables `_FABM_`, creates FMS/MOM6 source manifests that allow
`BUILD_DIR` outside the repository, and links `libfabm`. When an installed
BFM provides `libadj`, it is linked automatically. On systems whose linker
does not retain transitive MPI dependencies, add explicit MPI libraries (for
example `-lmpifort -lmpi`) after the FABM libraries in the wrapper, then
rebuild. This is a platform-linking issue, not a runtime FABM option.

For ocean-only cases, use the build instructions in MOM6 `docs/FABM.md`
rather than this SIS2 wrapper. Rebuild after changing MOM6 bridge source,
SIS2 source, compiler/MPI libraries, or FABM installation; YAML and
diagnostic-table changes alone do not require a rebuild.

For a standard FABM/NPZD build, point `FABM_ROOT` to a library installed from
the ordinary FABM source. For BFM or iron-enabled BFM, rebuild FABM against
the corresponding BFM source first. See `FABM_PORT.md` for the full commands.

## 5. Runtime configuration and initialization

Enable FABM in a case-specific `MOM_override`:

```text
USE_FABM_TRACERS = True
FABM_CONFIG_FILE = "fabm.yaml"
```

Without `FABM_INITIAL_CONDITIONS_FILE`, each interior state receives the
`initialization` value from the YAML file. To initialize from a complete
NetCDF file already on the MOM6 tracer grid, add:

```text
FABM_INITIAL_CONDITIONS_FILE = "INPUT/fabm_initial_conditions.nc"
FABM_INITIAL_CONDITIONS_ON_GRID = True
```

MOM6 restart fields take precedence over YAML and external initial-condition
values. Use the templates rather than copying an entire `MOM_override` from a
different case.

### Initializing from an external NetCDF file

Use YAML initialization for an inexpensive technical smoke test or when
scientifically justified uniform/default concentrations are desired. Use
`FABM_INITIAL_CONDITIONS_FILE` when a cold start should use spatially
varying fields, for example a Copernicus-derived file. The bridge does not
automatically read an arbitrary observational product: the source fields must
first be placed on the MOM6 tracer grid and then mapped to the state names
declared by the selected YAML.

The generic preparation sequence is:

```text
source BGC NetCDF files
  -> regrid_bgc_to_mom6.py
  -> MOM6-grid BGC fields
  -> map_bgc_to_fabm_ic.py or prepare_bfm_iron_ic.py
  -> complete FABM/BFM initial-condition NetCDF file
```

The scripts are in `tools/fabm/scripts/`. Run each with `--help` and retain
the raw-data licence, source-file names, grid/mask, mapping JSON, command
line, and generated-file provenance. A complete BFM file includes every
active state: observed fields are used where available, while the remaining
states receive the YAML defaults during file preparation. For the tested
Copernicus iron workflow, source dissolved iron is in `mmol m-3` and the
BFM iron state is in `umol m-3`; the mapping applies a factor of 1000.
Verify units for every other source product and BFM configuration.

The supplied YAML files have deliberately different roles:

| Configuration | Purpose |
|---|---|
| `configurations/fabm_npzd.yaml` | Four-state NPZD test: nutrient, phytoplankton, zooplankton, detritus. |
| `configurations/fabm_bfm_smoke.yaml` | Small BFM-library linkage smoke test, not a complete BFM experiment. |
| `configurations/fabm_bfm_iron_9pft.yaml` | Reference full iron-enabled BFM configuration. |

Full BFM registers many tracer and restart fields. The tested iron-BFM case
uses:

```text
MAX_FIELDS = 128
FABM_MINIMUM_ACTIVE_THICKNESS = 0.1
FABM_MAXIMUM_VERTICAL_SUBSTEPS = 100
```

`MAX_FIELDS` is a MOM6 tracer/restart registration limit, not
`MAX_INPUT_FIELDS`. The last two settings protect against evaluation in very
thin layers and excessive sinking-related vertical-movement substeps.

## 6. External data, forcing and storage

The OM1 workflow requires NOAA grid, WOA temperature/salinity and JRA forcing
archives. Configure the `.datasets` link as described by MOM6-examples, while
keeping large JRA forcing files, restarts and diagnostic output in scratch.

Some older OM1 inputs refer to a combined `WOA05_pottemp_salt.nc` file and
`PTEMP`/`SALT` variables. The downloaded WOA13 archive instead provides
separate temperature and salinity files with `ptemp_an` and `s_an`. Apply
[`MOM_input.woa13_z_initialization`](../tools/fabm/templates/MOM_input.woa13_z_initialization)
to the case's `MOM_input` when using that archive.

The NOAA short JRA sample covers only a few days. A one-year or multi-year run
requires the padded annual JRA files. A multi-year run advances the ocean,
sea-ice and BFM restart state continuously but repeats the annual atmospheric
forcing; it is therefore not a historical atmospheric simulation.

The basic data setup is:

```bash
cd "$EXAMPLES_ROOT"
ln -sfn /absolute/path/to/datasets .datasets

readlink -e ice_ocean_SIS2/OM_1deg/INPUT/grid_spec.nc
readlink -e ice_ocean_SIS2/OM_1deg/INPUT/JRA_rsds.nc
```

Both commands must resolve to real files. The files in a case `INPUT`
directory are expected to be symbolic links. Test them with `readlink -e`
or `ls -lL`; merely seeing links in `find` output is not itself an error.

Keep mutable large files on scratch:

```bash
export CASE_DIR="$EXAMPLES_ROOT/ice_ocean_SIS2/OM_1deg_fabm"
export RUN_ROOT="/scratch/$USER/mom6_fabm_runs/om1"
mkdir -p "$RUN_ROOT/RESTART" "$RUN_ROOT/OUTPUT"
ln -sfn "$RUN_ROOT/RESTART" "$CASE_DIR/RESTART"
ln -sfn "$RUN_ROOT/OUTPUT" "$CASE_DIR/OUTPUT"
```

For a repeated-forcing multi-year experiment, start the first segment with
`input_filename = 'n'` and physical data in `INPUT`. Later segments use
`input_filename = 'r'` and read the evolving MOM6/SIS2/FABM state from
`RESTART`. Forcing files are still read from `INPUT`; they are not restart
fields.

## 7. Test ladder

1. Run the KPP NPZD case with `configurations/fabm_npzd.yaml`.
2. Start from the tracked
   [`OM1 configuration overlay`](../ice_ocean_SIS2/OM_1deg_fabm/README.md),
   supply the external OM1 data, and run a short MOM6--SIS2 FABM smoke test.
3. Run the short iron-BFM smoke test using YAML initialization.
4. Run an annual BFM test using padded annual JRA forcing.
5. Optionally create a Copernicus-derived initial-condition file with the
   scripts in `tools/fabm/scripts/`.
6. Optionally continue from restarts for a multi-year repeated-forcing test.

The tracked OM1 overlay is intentionally small. To run a smoke test, activate
the matching text fragments and link the executable:

```bash
cd "$EXAMPLES_ROOT/ice_ocean_SIS2/OM_1deg_fabm"
cp MOM_input.bfm_smoke MOM_input
cp input.nml.bfm_smoke input.nml
cp MOM_override.bfm_smoke MOM_override
cp diag_table.bfm_smoke diag_table
cp fabm_bfm_smoke.yaml fabm.yaml
ln -sfn "$BUILD_DIR/MOM6" MOM6
```

The product of `MOM_layout` must match the MPI rank count. The supplied
`4 x 4` layout is only a 16-rank smoke-test layout; choose a valid layout
for larger jobs. A minimal site job script loads the same modules used for the
build, changes into the case directory, verifies `./MOM6` is executable,
and launches `srun ./MOM6`.

## 8. Diagnostics and troubleshooting

Only fields listed in `diag_table` are written. Match diagnostic names to the
selected YAML. For short tests, output at least daily; a monthly stream can
contain only NetCDF fill values before its first scheduled output time.

Full BFM configurations require a sufficiently large `MAX_FIELDS` setting
(the tested iron configuration uses `MAX_FIELDS = 128`) and may require a
larger FMS domain stack. See the MOM6
[`docs/FABM.md`](https://github.com/MinahilAB/MOM6/blob/fabm-port/docs/FABM.md)
for bridge runtime controls and limitations, including vertical-movement CFL
protection. `FABM_PORT.md` remains the examples-side compatibility and
coupled-build guide.

For NPZD, start with the four state concentrations, their FABM source
tendencies, PAR, and production. For BFM, begin with nitrate, phosphate,
iron, selected organic pools, and total chlorophyll. The templates
`diag_table.npzd` and `diag_table.bfm` are starting fragments; diagnostic
names must match the selected YAML exactly. Writing every BFM state hourly can
produce prohibitively large files.

| Symptom | Likely cause | Resolution |
|---|---|---|
| WOA `PTEMP` or `SALT` error | Obsolete WOA05 settings used with WOA13 data. | Apply the WOA13 fragment from Section 6. |
| Forcing time-range error | A short JRA sample is used beyond its final time. | Use padded annual forcing or shorten the run. |
| Missing `libnetcdff.so` at launch | Batch environment differs from the build environment. | Load the same compiler, MPI, and NetCDF modules in the job script. |
| `MAX_FIELDS` or too-many-restart-fields error | Full BFM exceeds MOM6 registration capacity. | Increase `MAX_FIELDS`. |
| `mpp_domains_stack overflow` | FMS stack is too small for the decomposition/field count. | Increase `domains_stack_size` consistently on all ranks. |
| Vertical-movement CFL fatal error | Sinking, timestep, or thin layers require too many substeps. | Review timestep, sinking speed, thin-layer treatment, and substep limit. |
| Fill values in output | No scheduled sample, field not registered, or land cell inspected. | Check `diag_table`, `Time`, field name, and ocean mask. |
| Disk-quota write error | Output/restarts/geometry are written in the checkout. | Link output and restart directories to scratch. |
