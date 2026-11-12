# Preprocessing scripts

The scripts in this directory prepare external biogeochemical data for the
MOM6--FABM bridge. They do not download proprietary or licensed data and do
not modify a MOM6 case directory automatically.

- `regrid_bgc_to_mom6.py`: maps source fields horizontally and vertically to
  the MOM6 tracer grid.
- `map_bgc_to_fabm_ic.py`: maps regridded variables to state names for a
  simple FABM configuration such as NPZD.
- `prepare_bfm_iron_ic.py`: combines mapped observed fields with YAML default
  values to create a complete iron-enabled BFM initial-condition file.

Use `python3 <script> --help` for command-line arguments. Retain the raw-data
licence, source file names, mapping file, and generated NetCDF provenance with
every experiment.
