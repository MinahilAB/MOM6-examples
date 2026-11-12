# Generic FABM and BFM preparation tools for MOM6

This directory contains portable example configurations, template fragments,
and Python utilities for the MOM6--FABM bridge. They are deliberately not a
complete MOM6 experiment: each user must choose a suitable grid, forcing,
timestep, diagnostics, and scientifically justified initial conditions.

The bridge source is maintained on the MOM6 `fabm-port` branch. For coupled
MOM6--SIS2 build and compatibility instructions, see
[`../../FABM_PORT.md`](../../FABM_PORT.md). For the complete reproducibility
workflow, see [`../../docs/FABM_BFM_TUTORIAL.md`](../../docs/FABM_BFM_TUTORIAL.md).

## Directory layout

- `configurations/`
  - `fabm_npzd.yaml`: minimal four-state NPZD configuration.
  - `fabm_bfm_smoke.yaml`: minimal BFM/OGS technical smoke configuration.
  - `fabm_bfm_iron_9pft.yaml`: tested iron-enabled BFM reference
    configuration; it requires the matching `bfmforfabm` iron source and may
    require its `libadj` dependency.
  - `copernicus_bfm_iron_mapping.example.json`: example mapping of regridded
    Copernicus fields to iron-BFM state variables.
- `templates/`
  - portable `MOM_override` and `diag_table` fragments for NPZD and BFM.
- `scripts/`
  - `regrid_bgc_to_mom6.py`: maps source fields onto a MOM6 tracer grid.
  - `map_bgc_to_fabm_ic.py`: maps regridded fields to simple FABM state names.
  - `prepare_bfm_iron_ic.py`: completes an iron-BFM IC file using observed
    fields where available and YAML defaults for the remaining states.

## Python requirements

The preprocessing utilities require Python 3.8 or newer plus:

```text
numpy
scipy
xarray
netCDF4
```

Run a script with `--help` before use, for example:

```bash
python3 scripts/regrid_bgc_to_mom6.py --help
```

The scripts do not download external data, modify a MOM6 case automatically,
or establish scientific validity. Retain the source-data licence, exact input
file names, mapping file, generated-NetCDF provenance, and source revisions
with every experiment.
