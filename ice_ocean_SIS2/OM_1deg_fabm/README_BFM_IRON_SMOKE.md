# OM_1deg FABM--BFM iron test

This case is isolated from the NPZD and non-iron BFM cases. It uses the
MOM6 executable linked against `local/fabm/mom6-bfm-iron`, the upstream
`bfmforfabm` `iron` branch, and the 9-PFT iron YAML. The first run is one day
on 480 ranks and writes only the ten supervisor-requested BFM state variables.

The IC file is intentionally a separate, complete BFM state file. It will
combine Copernicus mappings for N1_p, N3_n, N5_s, N7_f, O2_o, O3_c and O3h_h
with YAML initialization constants for N4_n, R3_c, X3_c and all other BFM
states.
