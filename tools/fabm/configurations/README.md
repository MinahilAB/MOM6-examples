# FABM and BFM sample configurations

These YAML and JSON files are tracked examples for configuring the generic
MOM6 interior-state FABM bridge.

- `fabm_npzd.yaml` is the smallest recommended functional test. Its four
  state variables are `npzd_nut`, `npzd_phy`, `npzd_zoo`, and `npzd_det`.
- `fabm_bfm_smoke.yaml` tests that a BFM-enabled FABM library can initialize
  and exchange an interior state with MOM6. It is not a full BFM experiment.
- `fabm_bfm_iron_9pft.yaml` is the reference configuration for the tested
  iron-enabled BFM workflow. It declares many interior states; use a MOM6
  `MAX_FIELDS` setting large enough for tracer and restart registration.
- `copernicus_bfm_iron_mapping.example.json` records the intended mapping of
  regridded Copernicus fields to selected BFM states.

YAML `initialization` values are used only for a cold start without
`FABM_INITIAL_CONDITIONS_FILE`. A MOM6 restart takes precedence, followed by a
complete NetCDF initial-condition file when configured.
