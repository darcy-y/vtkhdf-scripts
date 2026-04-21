#!/usr/bin/env python3

"""
Convert a legacy VTK unstructured-grid file series to one temporal VTKHDF file.

Example:

    python3 converters/vtk_series_to_vtkhdf.py \
        --input "input/case_000001/dump/particle/dump_*.vtk" \
        --output output/case_000001.vtkhdf \
        --dt 0.1 \
        --t0 0.1 \
        --time-mode index
"""

from __future__ import annotations

import argparse
from typing import Any, Dict

from vtkmodules.vtkIOLegacy import vtkDataSetReader

from vtu_series_to_vtkhdf import (
    H5Config,
    read_unstructured_grid,
    unstructured_series_to_vtkhdf,
)


def _read_all_attribute_arrays(reader: vtkDataSetReader) -> None:
    for method_name in (
        "ReadAllScalarsOn",
        "ReadAllVectorsOn",
        "ReadAllNormalsOn",
        "ReadAllTensorsOn",
        "ReadAllColorScalarsOn",
        "ReadAllFieldsOn",
    ):
        method = getattr(reader, method_name, None)
        if method is not None:
            method()


def read_vtk(filename: str) -> Dict[str, Any]:
    reader = vtkDataSetReader()
    reader.SetFileName(filename)
    _read_all_attribute_arrays(reader)
    reader.Update()

    output = reader.GetOutput()
    if output is None:
        raise RuntimeError(f"Failed to read VTK file: {filename}")
    if not output.IsA("vtkUnstructuredGrid"):
        raise ValueError(
            f"Only legacy VTK unstructured-grid files are supported, got "
            f"{output.GetClassName()} in {filename}"
        )

    return read_unstructured_grid(output, filename)


def vtk_series_to_vtkhdf(
    input_pattern: str,
    output_file: str,
    cfg: H5Config,
    time_mode: str = "auto",
    static_mesh: bool = False,
    dt: float = 1.0,
    t0: float = 0.0,
) -> None:
    unstructured_series_to_vtkhdf(
        input_pattern=input_pattern,
        output_file=output_file,
        cfg=cfg,
        read_frame=read_vtk,
        time_mode=time_mode,
        static_mesh=static_mesh,
        dt=dt,
        t0=t0,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert multiple legacy VTK unstructured-grid files to one temporal VTKHDF file."
    )
    parser.add_argument(
        "--input",
        required=True,
        help='Input legacy VTK glob pattern, e.g. "step_*.vtk"',
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output .vtkhdf filename",
    )
    parser.add_argument(
        "--time-mode",
        choices=["auto", "filename", "index"],
        default="auto",
        help="How to assign time values: auto / filename / index",
    )
    parser.add_argument(
        "--static-mesh",
        action="store_true",
        help="Reuse mesh/topology from first step; only fields vary with time.",
    )
    parser.add_argument(
        "--compression",
        choices=["gzip", "lzf", "none"],
        default="gzip",
        help="HDF5 compression filter",
    )
    parser.add_argument(
        "--compression-level",
        type=int,
        default=4,
        help="Compression level for gzip",
    )
    parser.add_argument(
        "--chunk-1d",
        type=int,
        default=8192,
        help="Chunk length for 1D datasets",
    )
    parser.add_argument(
        "--chunk-2d-rows",
        type=int,
        default=4096,
        help="Chunk row count for 2D datasets",
    )
    parser.add_argument(
        "--dt",
        type=float,
        default=1.0,
        help="Physical time increment per step",
    )
    parser.add_argument(
        "--t0",
        type=float,
        default=0.0,
        help="Starting physical time",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    compression = None if args.compression == "none" else args.compression
    cfg = H5Config(
        compression=compression,
        compression_level=args.compression_level,
        chunk_1d=args.chunk_1d,
        chunk_2d_rows=args.chunk_2d_rows,
    )

    vtk_series_to_vtkhdf(
        input_pattern=args.input,
        output_file=args.output,
        cfg=cfg,
        time_mode=args.time_mode,
        static_mesh=args.static_mesh,
        dt=args.dt,
        t0=args.t0,
    )


if __name__ == "__main__":
    main()
