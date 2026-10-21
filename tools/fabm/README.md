# Generic FABM and BFM preparation tools for MOM6

This directory contains example configuration files and generic utilities for
preparing biogeochemical initial conditions for the MOM6--FABM bridge.

The tools are examples rather than complete MOM6 experiment configurations.
Users must select suitable MOM6 forcing, grid, timestep, diagnostics and
initial conditions for their own experiment.

The MOM6 bridge source is maintained on the `fabm-port` branch of MOM6.
Coupled MOM6--SIS2 build instructions are provided in
[`../../FABM_PORT.md`](../../FABM_PORT.md).

## Contents

- `regrid_bgc_to_mom6.py`
  - Horizontally and vertically maps source biogeochemical fields onto a MOM6
    tracer grid.
  - Uses a MOM6 `ocean_geometry.nc` file for tracer-cell coordinates and the
    ocean mask.
  - Uses a MOM6 `Vertical_coordinate.nc` file for target vertical levels.

- `map_bgc_to_fabm_ic.py`
  - Maps regridded source variables to FABM tracer names.
  - It can be used for simple FABM configurations such as NPZD.

- `prepare_bfm_iron_ic.py`
  - Creates a complete initial-condition file for an iron-enabled BFM
    configuration.
  - Observed variables are taken from the regridded source data.
  - BFM states that are not available from the source product are initialized
    using the configured model initial values.

- `examples/fabm_bfm_smoke.yaml`
  - Minimal technical BFM configuration for testing the MOM6--FABM interface.
  - It is not intended as a scientifically complete ecosystem simulation.

- `examples/fabm_bfm_iron_9pft.yaml`
  - Example iron-enabled BFM configuration.
  - It may require the `iron` branch of `bfmforfabm` and the accompanying
    `libadj` library.
  - Users should review all parameters before using it scientifically.

- `examples/copernicus_bfm_iron_mapping.example.json`
  - Example mapping between Copernicus biogeochemical variables and FABM/BFM
    state variables.

## Software requirements

The Python utilities require Python 3 and the following packages:

```text
numpy
scipy
xarray
netCDF4
