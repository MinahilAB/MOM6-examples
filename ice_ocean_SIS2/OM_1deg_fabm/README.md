# OM1 MOM6--SIS2--FABM configuration overlay

This directory is a small, tracked configuration overlay for the upstream
`ice_ocean_SIS2/OM_1deg` case. It does not include an executable, NOAA input
data, initial-condition NetCDF files, restarts, diagnostics, or Slurm logs.

## Included text configuration

- `MOM_input.bfm_smoke`, `SIS_input`, `SIS_override`, `static_input.nml`,
  `data_table`, and `field_table` provide the MOM6--SIS2 case configuration.
- `MOM_layout` and `SIS_layout` define the small 4-by-4 smoke-test layout;
  users must select layouts compatible with their requested MPI rank count.
- `input.nml.bfm_smoke`, `MOM_override.bfm_smoke`, `diag_table.bfm_smoke`,
  and `fabm_bfm_smoke.yaml` form the one-day YAML-initialised BFM smoke test.
- `input.nml.bfm_iron_smoke`, `MOM_override.bfm_iron_smoke`, and
  `diag_table.bfm_iron_smoke` are reference fragments for the iron-BFM and
  external-initial-condition workflow. Their `OUTPUT` and `RESTART` paths are
  relative so those directories can be symlinked to scratch.

The iron BFM YAML and Copernicus mapping tools are maintained under
[`../../tools/fabm/`](../../tools/fabm/). Copy the selected YAML into the run
directory, or set `FABM_CONFIG_FILE` to a valid path visible to every compute
node.

## Required external data

Obtain the OM1 grid/topography, WOA temperature/salinity, and JRA forcing
archives following the MOM6-examples data instructions. Point the repository
`.datasets` link to the resulting dataset tree, then ensure this case's
`INPUT` links resolve. The large `INPUT`, `OUTPUT`, and `RESTART` directories
must remain outside Git.

Older OM1 settings refer to WOA05. When using the WOA13 archive, apply the
four settings in
[`../../tools/fabm/templates/MOM_input.woa13_z_initialization`](../../tools/fabm/templates/MOM_input.woa13_z_initialization)
to the active `MOM_input`.
