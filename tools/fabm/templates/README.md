# MOM6--FABM--BFM configuration templates

These are portable fragments, not complete MOM6 case directories. Copy the
relevant settings into a case and retain the case's original physics,
coordinate, forcing, and coupler settings.

- `MOM_override.fabm` enables generic FABM with the NPZD sample configuration.
- `MOM_override.bfm` enables the full iron-enabled BFM configuration and sets
  bridge safety options required by the tested OM1 workflow.
- `diag_table.npzd` requests NPZD states, source terms, PAR, and production.
- `diag_table.bfm` requests a compact set of BFM states and total chlorophyll.
- `MOM_input.woa13_z_initialization` is a four-setting fragment that updates
  an OM1-like case from obsolete WOA05 names to the WOA13 archive files and
  variable names used by the reproducible workflow.

The names in a diagnostic table must exactly match the state and diagnostic
names declared by the selected YAML configuration. A full BFM diagnostic
table is intentionally not supplied: writing every state at high frequency can
produce very large files.
