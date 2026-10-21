#!/usr/bin/env python3
"""Regrid gridded biogeochemical fields to a MOM6 tracer grid.

The program is deliberately model agnostic: it interpolates named source
variables and preserves their units.  A separate FABM mapping step should
convert these fields to the state variables required by a specific model
(e.g., NPZD or BFM).  This separation prevents scientific conversions from
being hidden in the horizontal/vertical regridding machinery.

Supported input format
----------------------
Regular longitude/latitude/depth NetCDF fields with dimensions ordered in any
order and with one optional time dimension.  Coordinate and variable names
are described by a small JSON mapping file, so the same tool can be used with
other products.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import distance_transform_edt

FILL_VALUE = np.float32(1.0e20)


def parse_inputs(items: list[str]) -> dict[str, Path]:
    """Parse LABEL=PATH command-line values."""
    result: dict[str, Path] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"--input must be LABEL=PATH, got {item!r}")
        label, filename = item.split("=", 1)
        if not label or not filename:
            raise ValueError(f"--input must be LABEL=PATH, got {item!r}")
        path = Path(filename).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        result[label] = path
    return result


def normalise_longitude(longitude: np.ndarray) -> np.ndarray:
    """Convert longitudes to the half-open interval [-180, 180)."""
    return ((np.asarray(longitude, dtype=np.float64) + 180.0) % 360.0) - 180.0


def fill_missing_horizontally(values: np.ndarray) -> np.ndarray:
    """Fill source land/missing cells from the nearest valid horizontal cell.

    This is performed independently at each source depth before interpolation.
    It avoids NaNs leaking from a source land cell into an adjacent MOM6 wet
    cell.  The output file records that nearest-valid filling was used.
    """
    filled = np.asarray(values, dtype=np.float64).copy()
    populated_layers = np.flatnonzero(np.isfinite(filled).any(axis=(1, 2)))
    if populated_layers.size == 0:
        raise ValueError("Source variable has no valid ocean values")

    # The deepest nominal product level can be entirely below the ocean floor.
    # RegularGridInterpolator still requires a finite value at every depth
    # level, so use the nearest populated source level before horizontal fill.
    for k in range(filled.shape[0]):
        if not np.isfinite(filled[k]).any():
            donor = populated_layers[np.argmin(np.abs(populated_layers - k))]
            filled[k] = filled[donor]

    for k in range(filled.shape[0]):
        layer = filled[k]
        valid = np.isfinite(layer)
        if valid.all():
            continue
        nearest = distance_transform_edt(~valid, return_distances=False,
                                         return_indices=True)
        layer[~valid] = layer[tuple(nearest[:, ~valid])]
    return filled


def source_array(dataset: xr.Dataset, variable: str, names: dict[str, str]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    """Read one field as (depth, latitude, longitude), removing time if present."""
    if variable not in dataset:
        raise KeyError(f"Variable {variable!r} is not present in {dataset.encoding.get('source', '<dataset>')}")
    da = dataset[variable]
    time_name = names.get("time")
    if time_name and time_name in da.dims:
        if da.sizes[time_name] != 1:
            raise ValueError(f"{variable!r} has {da.sizes[time_name]} times; select one time before regridding")
        da = da.isel({time_name: 0}, drop=True)

    depth_name = names["depth"]
    latitude_name = names["latitude"]
    longitude_name = names["longitude"]
    da = da.transpose(depth_name, latitude_name, longitude_name)
    raw = np.asarray(da.values, dtype=np.float64)
    fill = da.attrs.get("_FillValue", da.encoding.get("_FillValue"))
    if fill is not None:
        raw[np.isclose(raw, float(fill), rtol=0.0, atol=abs(float(fill)) * 1.0e-7)] = np.nan
    raw[~np.isfinite(raw)] = np.nan

    depth = np.asarray(dataset[depth_name].values, dtype=np.float64)
    latitude = np.asarray(dataset[latitude_name].values, dtype=np.float64)
    longitude = normalise_longitude(dataset[longitude_name].values)
    order = np.argsort(longitude)
    longitude = longitude[order]
    raw = raw[:, :, order]

    # Periodic longitude: append the first source column at +360 degrees.
    longitude = np.concatenate((longitude, [longitude[0] + 360.0]))
    raw = np.concatenate((raw, raw[:, :, :1]), axis=2)
    return raw, depth, latitude, longitude, dict(da.attrs)


def source_ocean_mask(filename: Path, variable: str, names: dict[str, str],
                      depth: np.ndarray, latitude: np.ndarray,
                      longitude: np.ndarray) -> np.ndarray:
    """Read an official source land/sea mask on the source field grid.

    The Copernicus mask uses one for ocean and zero for land. It is applied
    before nearest-ocean filling so source land values cannot influence a MOM6
    wet cell. Coordinates are checked after the field longitude processing.
    """
    with xr.open_dataset(filename, decode_times=False, mask_and_scale=False) as dataset:
        if variable not in dataset:
            raise KeyError(f"Mask variable {variable!r} is not present in {filename}")
        depth_name = names["depth"]
        latitude_name = names["latitude"]
        longitude_name = names["longitude"]
        da = dataset[variable].transpose(depth_name, latitude_name, longitude_name)
        mask = np.asarray(da.values, dtype=np.float64)
        mask_depth = np.asarray(dataset[depth_name].values, dtype=np.float64)
        mask_latitude = np.asarray(dataset[latitude_name].values, dtype=np.float64)
        mask_longitude = normalise_longitude(dataset[longitude_name].values)

    order = np.argsort(mask_longitude)
    mask_longitude = mask_longitude[order]
    mask = mask[:, :, order]
    mask_longitude = np.concatenate((mask_longitude, [mask_longitude[0] + 360.0]))
    mask = np.concatenate((mask, mask[:, :, :1]), axis=2)
    if not (np.array_equal(mask_depth, depth) and np.array_equal(mask_latitude, latitude)
            and np.allclose(mask_longitude, longitude)):
        raise ValueError("Official source mask coordinates do not match the source field grid")
    return np.isfinite(mask) & (mask > 0.0)


def interpolate_field(values: np.ndarray, source_depth: np.ndarray,
                      source_latitude: np.ndarray, source_longitude: np.ndarray,
                      target_depth: np.ndarray, target_latitude: np.ndarray,
                      target_longitude: np.ndarray, wet: np.ndarray,
                      chunk_layers: int) -> np.ndarray:
    """Linearly interpolate a field in z/lat/lon space in bounded memory."""
    values = fill_missing_horizontally(values)
    interpolator = RegularGridInterpolator(
        (source_depth, source_latitude, source_longitude), values,
        method="linear", bounds_error=False, fill_value=None,
    )
    nz, ny, nx = len(target_depth), target_latitude.shape[0], target_latitude.shape[1]
    result = np.full((nz, ny, nx), FILL_VALUE, dtype=np.float32)

    lon = normalise_longitude(target_longitude)
    # The appended periodic endpoint requires target values at/above its first
    # value.  Shift negative wrapped values by one cycle where necessary.
    lon = np.where(lon < source_longitude[0], lon + 360.0, lon)
    lat = np.clip(target_latitude, source_latitude.min(), source_latitude.max())
    wet_points = wet > 0.0

    for first in range(0, nz, chunk_layers):
        last = min(first + chunk_layers, nz)
        depths = np.clip(target_depth[first:last], source_depth.min(), source_depth.max())
        z3 = np.broadcast_to(depths[:, None, None], (last - first, ny, nx))
        lat3 = np.broadcast_to(lat[None, :, :], z3.shape)
        lon3 = np.broadcast_to(lon[None, :, :], z3.shape)
        points = np.column_stack((z3.ravel(), lat3.ravel(), lon3.ravel()))
        interpolated = interpolator(points).reshape(z3.shape)
        interpolated[:, ~wet_points] = FILL_VALUE
        result[first:last] = interpolated.astype(np.float32)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", required=True, type=Path, help="MOM6 ocean_geometry.nc")
    parser.add_argument("--vertical", required=True, type=Path, help="MOM6 Vertical_coordinate.nc")
    parser.add_argument("--mapping", required=True, type=Path, help="JSON field mapping")
    parser.add_argument("--input", action="append", required=True, metavar="LABEL=PATH",
                        help="Input NetCDF file; repeat for each label in the mapping")
    parser.add_argument("--source-mask", type=Path,
                        help="Optional official 3-D source land/sea-mask NetCDF file (1=ocean, 0=land)")
    parser.add_argument("--source-mask-variable", default="mask",
                        help="Variable in --source-mask (default: mask)")
    parser.add_argument("--output", required=True, type=Path, help="Output MOM6-grid NetCDF file")
    parser.add_argument("--chunk-layers", type=int, default=4,
                        help="Target layers per interpolation chunk (default: 4)")
    args = parser.parse_args()
    if args.chunk_layers < 1:
        parser.error("--chunk-layers must be positive")

    mapping = json.loads(args.mapping.read_text())
    names = mapping.get("coordinate_names", {})
    for required in ("longitude", "latitude", "depth"):
        if required not in names:
            raise ValueError(f"mapping coordinate_names must define {required!r}")
    inputs = parse_inputs(args.input)

    with xr.open_dataset(args.grid, decode_times=False) as grid, xr.open_dataset(args.vertical, decode_times=False) as vertical:
        target_lat = np.asarray(grid["geolat"].values, dtype=np.float64)
        target_lon = np.asarray(grid["geolon"].values, dtype=np.float64)
        wet = np.asarray(grid["wet"].values, dtype=np.float64)
        target_z = np.abs(np.asarray(vertical["Layer"].values, dtype=np.float64))
        xh = np.asarray(grid["lonh"].values, dtype=np.float64)
        yh = np.asarray(grid["lath"].values, dtype=np.float64)

    data_vars: dict[str, xr.DataArray] = {}
    source_notes: list[str] = []
    for output_name, spec in mapping["output_variables"].items():
        label = spec["input"]
        variable = spec.get("variable", output_name)
        if label not in inputs:
            raise KeyError(f"Mapping needs input label {label!r}; available labels: {sorted(inputs)}")
        with xr.open_dataset(inputs[label], decode_times=False, mask_and_scale=False) as dataset:
            values, depth, latitude, longitude, attrs = source_array(dataset, variable, names)
        if args.source_mask is not None:
            ocean = source_ocean_mask(args.source_mask, args.source_mask_variable,
                                      names, depth, latitude, longitude)
            values[~ocean] = np.nan
        interpolated = interpolate_field(values, depth, latitude, longitude,
                                         target_z, target_lat, target_lon, wet,
                                         args.chunk_layers)
        units = spec.get("units", attrs.get("units", "unknown"))
        data_vars[output_name] = xr.DataArray(
            interpolated[None, :, :, :], dims=("Time", "zl", "yh", "xh"),
            attrs={
                "long_name": spec.get("long_name", attrs.get("long_name", output_name)),
                "units": units,
                "source_variable": variable,
                "source_input": label,
                "interpolation": "linear in depth/latitude/longitude; nearest-valid source fill at source land",
            },
        )
        source_notes.append(f"{output_name} <- {inputs[label].name}:{variable}")

    output = xr.Dataset(
        data_vars=data_vars,
        coords={
            "Time": xr.DataArray([0.0], dims="Time", attrs={
                "long_name": "Time", "units": "days since 1958-01-01 00:00:00",
                "cartesian_axis": "T", "calendar": "JULIAN",
            }),
            "zl": xr.DataArray(target_z, dims="zl", attrs={
                "long_name": "Layer z-rho", "units": "meter",
                "cartesian_axis": "Z", "positive": "down",
            }),
            "yh": xr.DataArray(yh, dims="yh", attrs={
                "long_name": "h point nominal latitude", "units": "degrees_north", "cartesian_axis": "Y",
            }),
            "xh": xr.DataArray(xh, dims="xh", attrs={
                "long_name": "h point nominal longitude", "units": "degrees_east", "cartesian_axis": "X",
            }),
        },
        attrs={
            "title": "Biogeochemical fields regridded to MOM6 tracer grid",
            "source_files": "; ".join(source_notes),
            "grid_type": "regular",
            "regridding_notes": (
                "Target points outside the Copernicus latitude/depth coverage are clipped to the nearest source "
                "coordinate. Source missing/land cells are filled from the nearest valid horizontal source cell. "
                + ("The official source land/sea mask was applied before filling."
                   if args.source_mask is not None else
                   "No separate official source mask was supplied; field missing values defined source land.")
            ),
        },
    )
    encoding = {name: {"zlib": True, "complevel": 4, "shuffle": True, "_FillValue": FILL_VALUE}
                for name in data_vars}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_netcdf(args.output, format="NETCDF4", encoding=encoding)
    print(f"Wrote {args.output}")
    for name, field in data_vars.items():
        valid = field.values[field.values != FILL_VALUE]
        print(f"{name}: shape={tuple(field.shape)}, min={valid.min():.6g}, max={valid.max():.6g}")


if __name__ == "__main__":
    main()
