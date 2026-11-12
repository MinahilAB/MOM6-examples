#!/usr/bin/env python3
"""Convert MOM6-grid BGC fields into a FABM interior-state initial file.

The source file must already be on the MOM6 grid (for example, produced by
regrid_bgc_to_mom6.py).  Scientific mappings are held in JSON rather than in
this code, allowing a different FABM model to use a different state mapping.
Supported mappings are a scaled source field or an explicit constant field.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import xarray as xr

FILL_VALUE = np.float32(1.0e20)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="MOM6-grid BGC NetCDF input")
    parser.add_argument("--mapping", required=True, type=Path, help="JSON FABM state mapping")
    parser.add_argument("--output", required=True, type=Path, help="FABM initial-condition NetCDF output")
    args = parser.parse_args()

    mapping = json.loads(args.mapping.read_text())
    outputs = mapping["output_variables"]
    with xr.open_dataset(args.input, decode_times=False, mask_and_scale=False) as source:
        for coord in ("Time", "zl", "yh", "xh"):
            if coord not in source:
                raise KeyError(f"Input is missing required coordinate {coord!r}")

        data_vars: dict[str, xr.DataArray] = {}
        source_notes: list[str] = []
        wet = None
        for target, spec in outputs.items():
            if "source" in spec:
                field = source[spec["source"]].astype(np.float64)
                values = field.values * float(spec.get("factor", 1.0)) + float(spec.get("offset", 0.0))
                invalid = (~np.isfinite(values)) | (field.values >= 1.0e19)
                values[invalid] = FILL_VALUE
                source_notes.append(f"{target} <- {spec['source']} * {spec.get('factor', 1.0)}")
            elif "constant" in spec:
                if wet is None:
                    # Any valid source field provides the model's wet/land mask.
                    first_source = next(item["source"] for item in outputs.values() if "source" in item)
                    wet = source[first_source].values < 1.0e19
                values = np.full(source[first_source].shape, float(spec["constant"]), dtype=np.float32)
                values[~wet] = FILL_VALUE
                source_notes.append(f"{target} <- constant {spec['constant']}")
            else:
                raise ValueError(f"Mapping for {target!r} needs 'source' or 'constant'")

            data_vars[target] = xr.DataArray(
                values.astype(np.float32), dims=("Time", "zl", "yh", "xh"),
                attrs={
                    "long_name": spec.get("long_name", target),
                    "units": spec["units"],
                    "cell_methods": "area:mean zl:mean yh:mean xh:mean time: point",
                },
            )

        result = xr.Dataset(
            data_vars=data_vars,
            coords={name: source[name] for name in ("Time", "zl", "yh", "xh")},
            attrs={
                "title": mapping.get("title", "FABM initial conditions mapped from MOM6-grid BGC fields"),
                "source_file": str(args.input),
                "mapping": "; ".join(source_notes),
                "history": mapping.get("history", ""),
                "grid_type": "regular",
            },
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoding = {name: {"zlib": True, "complevel": 4, "shuffle": True, "_FillValue": FILL_VALUE}
                for name in result.data_vars}
    result.to_netcdf(args.output, format="NETCDF4", encoding=encoding)
    print(f"Wrote {args.output}")
    for name in result.data_vars:
        values = result[name].values
        valid = values[values < 1.0e19]
        print(f"{name}: min={valid.min():.6g}, max={valid.max():.6g}, valid={valid.size}")


if __name__ == "__main__":
    main()
