#!/usr/bin/env python3
"""Create a complete iron-BFM initial-condition file from Copernicus fields.

MOM6's current FABM bridge requires every active interior state in a selected
NetCDF IC file. This utility derives all state names/defaults from the iron BFM
YAML and overwrites only observed Copernicus pools. Missing observations remain
explicit YAML-default constants rather than implicit zero values.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import xarray as xr
import yaml
from netCDF4 import Dataset

FILL_VALUE = np.float32(1.0e20)
# source field, multiplier to BFM state units, provenance description
COPERNICUS_MAPPING = {
    "N1_p": ("po4", 1.0, "Copernicus phosphate"),
    "N3_n": ("no3", 1.0, "Copernicus nitrate"),
    "N5_s": ("si", 1.0, "Copernicus dissolved silicate"),
    # Copernicus stores dissolved iron in mmol Fe m-3, whereas the BFM N7/f
    # state is registered in umol Fe m-3. MOM6 does not infer this conversion
    # from NetCDF metadata, so apply the factor explicitly while creating ICs.
    "N7_f": ("fe", 1000.0, "Copernicus dissolved iron; mmol Fe m-3 to umol Fe m-3"),
    "O2_o": ("o2", 1.0, "Copernicus dissolved oxygen"),
    "O3_c": ("dissic", 12000.0, "Copernicus DIC; mol C m-3 to mg C m-3"),
    "O3h_h": ("talk", 1000.0, "Copernicus alkalinity; mol m-3 to mmol m-3"),
}

def yaml_initial_states(path: Path) -> dict[str, float]:
    """Return every scalar YAML initialization as its FABM state name/value."""
    document = yaml.safe_load(path.read_text())
    states: dict[str, float] = {}
    for instance, specification in document["instances"].items():
        initialization = specification.get("initialization", {})
        if not isinstance(initialization, dict):
            continue
        for component, value in initialization.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"{instance}/{component}: non-scalar initialization {value!r}")
            name = f"{instance}_{component}"
            if name in states:
                raise ValueError(f"Duplicate state {name}")
            states[name] = float(value)
    if not states:
        raise ValueError("No scalar state initializations were found in YAML")
    return states

def units_for_state(name: str) -> str:
    component = name.rsplit("_", 1)[-1]
    return {"c": "mg C m-3", "Chl": "mg m-3", "n": "mmol N m-3", "p": "mmol P m-3", "s": "mmol Si m-3", "f": "umol Fe m-3", "o": "mmol O2 m-3", "h": "mmol m-3", "r": "mmol Eq m-3"}.get(component, "unknown")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Regridded Copernicus MOM6-grid file")
    parser.add_argument("--yaml", type=Path, required=True, help="Iron-BFM YAML used by MOM6")
    parser.add_argument("--output", type=Path, required=True, help="Complete FABM BFM IC NetCDF file")
    args = parser.parse_args()
    states = yaml_initial_states(args.yaml)
    required = sorted({source for source, _, _ in COPERNICUS_MAPPING.values()})
    with xr.open_dataset(args.input, decode_times=False, mask_and_scale=False) as source:
        absent = [name for name in required if name not in source]
        if absent:
            raise ValueError("Regridded file lacks required Copernicus fields: " + ", ".join(absent))
        for coordinate in ("Time", "zl", "yh", "xh"):
            if coordinate not in source:
                raise ValueError(f"Regridded file lacks coordinate {coordinate!r}")
        nz, ny, nx = (source.sizes["zl"], source.sizes["yh"], source.sizes["xh"])
        reference = np.asarray(source["no3"].isel(Time=0).values, dtype=np.float32)
        input_fill = np.float32(source["no3"].attrs.get("_FillValue", FILL_VALUE))
        wet = reference != input_fill
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with Dataset(args.output, "w", format="NETCDF4") as output:
            output.createDimension("Time", None)
            output.createDimension("zl", nz)
            output.createDimension("yh", ny)
            output.createDimension("xh", nx)
            for coordinate in ("Time", "zl", "yh", "xh"):
                src = source[coordinate]
                dst = output.createVariable(coordinate, src.dtype, src.dims)
                dst[:] = src.values
                for key, value in src.attrs.items():
                    # netCDF4 requires _FillValue at createVariable time;
                    # coordinates do not need it, so do not copy it afterward.
                    if key != "_FillValue":
                        dst.setncattr(key, value)
            output.title = "Complete MOM6 FABM iron-BFM IC from Copernicus plus YAML defaults"
            output.source_file = str(args.input)
            output.yaml_file = str(args.yaml)
            output.history = "Observed Copernicus fields overwrite selected BFM pools; all others use YAML defaults."
            output.setncattr("copernicus_mappings", "; ".join(f"{state} <- {source_name} * {factor:g}" for state, (source_name, factor, _) in COPERNICUS_MAPPING.items()))
            for state, default in states.items():
                variable = output.createVariable(state, "f4", ("Time", "zl", "yh", "xh"), zlib=True, complevel=4, shuffle=True, fill_value=FILL_VALUE)
                variable.long_name = f"BFM initial state {state}"
                variable.units = units_for_state(state)
                if state in COPERNICUS_MAPPING:
                    source_name, factor, description = COPERNICUS_MAPPING[state]
                    values = np.asarray(source[source_name].isel(Time=0).values, dtype=np.float32)
                    valid = values != np.float32(source[source_name].attrs.get("_FillValue", FILL_VALUE))
                    variable[0, :, :, :] = np.where(valid, values * np.float32(factor), FILL_VALUE).astype(np.float32)
                    variable.initialization_source = description
                else:
                    layer = np.where(wet[0, :, :], np.float32(default), FILL_VALUE).astype(np.float32)
                    for k in range(nz):
                        variable[0, k, :, :] = layer
                    variable.initialization_source = f"YAML default {default:g}"
    print(f"Wrote {args.output} with {len(states)} BFM state variables.")
    print("Copernicus-mapped states:", ", ".join(COPERNICUS_MAPPING))
    print("YAML-default states:", len(states) - len(COPERNICUS_MAPPING))

if __name__ == "__main__":
    main()
