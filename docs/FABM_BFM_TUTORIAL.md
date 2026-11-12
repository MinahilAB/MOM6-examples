# MOM6--FABM--BFM reproducibility guide

This guide documents the portable workflow developed for the `fabm-port`
MOM6 bridge and its MOM6--SIS2 examples. It separates a technically verified
coupling workflow from scientific validation of any particular ecosystem
configuration.

## 1. Scope and supported configurations

The bridge dynamically registers FABM **interior** state variables as MOM6
tracers. MOM6 owns their transport, restart handling and diagnostics; FABM
calculates biological sources, diagnostics, fluxes and relative vertical
movement. Surface- and bottom-attached FABM state variables are not yet
supported.

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

```bash
git -C /path/to/MOM6 rev-parse HEAD
git -C /path/to/MOM6-examples rev-parse HEAD
git -C /path/to/MOM6-examples/src/SIS2 rev-parse HEAD
git -C /path/to/fabm rev-parse HEAD
git -C /path/to/bfmforfabm-iron rev-parse HEAD   # iron BFM only
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

```bash
export MOM6_ROOT=/absolute/path/to/MOM6
export FABM_ROOT=/absolute/path/to/local/fabm/mom6-bfm-iron
export MK_TEMPLATE=/absolute/path/to/mkmf-template.mk
export BUILD_DIR=/scratch/path/to/build/mom6-sis2-fabm-bfm
./build_fabm_sis2.sh
```

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

## 8. Diagnostics and troubleshooting

Only fields listed in `diag_table` are written. Match diagnostic names to the
selected YAML. For short tests, output at least daily; a monthly stream can
contain only NetCDF fill values before its first scheduled output time.

Full BFM configurations require a sufficiently large `MAX_FIELDS` setting
(the tested iron configuration uses `MAX_FIELDS = 128`) and may require a
larger FMS domain stack. See `FABM_PORT.md` for known runtime issues,
including vertical-movement CFL limits, memory pressure and shared filesystem
logging.

## 9. Status of platform recipes

The KPP, OM1 FABM, iron-enabled BFM and Copernicus-preprocessing workflows
were developed on G100. A Leonardo independent-build and full-BFM smoke test
is being documented; add site-specific module selections only after that
annual test is complete. Keep portable instructions in this file and place
cluster-specific module blocks in a separate appendix or Wiki page.
