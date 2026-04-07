#!/usr/bin/env python3
# @ Author      :  darcy-y
# @ Time        :  2026-04-07 14:07:47

"""
Usage: python3 vtu_series_to_vtkhdf.py --input "input/case_000001/dump/particle/dump_*.vtu" --output output/dump.vtkhdf --dt 3.5e-06


For dump interval in physical time instead of relying on filename parsing:

    python3 vtu_series_to_vtkhdf.py --input "input/case_000001/dump/particle/dump_*.vtu" --output output/dump.vtkhdf --dt 0.1 --t0 0.1 --time-mode index

"""

from __future__ import annotations

import argparse
import glob
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

import h5py
import numpy as np

from vtkmodules.vtkIOXML import vtkXMLUnstructuredGridReader
from vtkmodules.util.numpy_support import vtk_to_numpy


# ---------------------------------------------------------------------
# VTKHDF bookkeeping dtypes
# ---------------------------------------------------------------------
ID_DTYPE = np.int64
TIME_DTYPE = np.float64


# ---------------------------------------------------------------------
# HDF5 config
# ---------------------------------------------------------------------
@dataclass
class H5Config:
    compression: str | None = "gzip"  # None, "gzip", "lzf"
    compression_level: int | None = 4  # only used for gzip
    chunk_1d: int = 8192
    chunk_2d_rows: int = 4096


# ---------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------
def natural_key(text: str) -> List[Any]:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", text)]


def infer_step_from_filename(path: str) -> int | None:
    name = os.path.basename(path)
    stem = os.path.splitext(name)[0]
    matches = re.findall(r"\d+", stem)
    if not matches:
        return None

    return int(matches[-1])


def create_dataset(
    group: h5py.Group,
    name: str,
    shape: Tuple[int, ...],
    maxshape: Tuple[int | None, ...],
    dtype: np.dtype | type,
    chunks: Tuple[int, ...],
    cfg: H5Config,
) -> h5py.Dataset:
    kwargs: Dict[str, Any] = {
        "shape": shape,
        "maxshape": maxshape,
        "dtype": dtype,
        "chunks": chunks,
    }
    if cfg.compression is not None:
        kwargs["compression"] = cfg.compression
        if cfg.compression == "gzip" and cfg.compression_level is not None:
            kwargs["compression_opts"] = cfg.compression_level
    return group.create_dataset(name, **kwargs)


def make_1d(
    group: h5py.Group, name: str, dtype: np.dtype | type, cfg: H5Config
) -> h5py.Dataset:
    return create_dataset(
        group=group,
        name=name,
        shape=(0,),
        maxshape=(None,),
        dtype=dtype,
        chunks=(cfg.chunk_1d,),
        cfg=cfg,
    )


def make_2d(
    group: h5py.Group,
    name: str,
    ncomp: int,
    dtype: np.dtype | type,
    cfg: H5Config,
) -> h5py.Dataset:
    return create_dataset(
        group=group,
        name=name,
        shape=(0, ncomp),
        maxshape=(None, ncomp),
        dtype=dtype,
        chunks=(cfg.chunk_2d_rows, ncomp),
        cfg=cfg,
    )


def append_1d(dset: h5py.Dataset, arr: np.ndarray | List[Any]) -> None:
    arr = np.asarray(arr, dtype=dset.dtype)
    if arr.ndim != 1:
        raise ValueError(f"{dset.name} expects 1D input, got shape={arr.shape}")
    old = dset.shape[0]
    new = old + arr.shape[0]
    dset.resize((new,))
    dset[old:new] = arr


def append_2d(dset: h5py.Dataset, arr: np.ndarray) -> None:
    arr = np.asarray(arr, dtype=dset.dtype)
    if arr.ndim != 2:
        raise ValueError(f"{dset.name} expects 2D input, got shape={arr.shape}")
    if arr.shape[1] != dset.shape[1]:
        raise ValueError(
            f"{dset.name} second dimension mismatch: {arr.shape[1]} vs {dset.shape[1]}"
        )
    old = dset.shape[0]
    new = old + arr.shape[0]
    dset.resize((new, arr.shape[1]))
    dset[old:new, :] = arr


def append_row_2d(dset: h5py.Dataset, row: np.ndarray | List[Any]) -> None:
    row = np.asarray(row, dtype=dset.dtype)
    if row.ndim != 2 or row.shape[0] != 1:
        raise ValueError(f"{dset.name} expects shape (1, n), got {row.shape}")
    if row.shape[1] != dset.shape[1]:
        raise ValueError(
            f"{dset.name} second dimension mismatch: {row.shape[1]} vs {dset.shape[1]}"
        )
    old = dset.shape[0]
    dset.resize((old + 1, dset.shape[1]))
    dset[old : old + 1, :] = row


# ---------------------------------------------------------------------
# VTU reading
# ---------------------------------------------------------------------
def read_vtu(filename: str) -> Dict[str, Any]:
    reader = vtkXMLUnstructuredGridReader()
    reader.SetFileName(filename)
    reader.Update()
    ug = reader.GetOutput()

    if ug is None:
        raise RuntimeError(f"Failed to read VTU: {filename}")
    if ug.GetPoints() is None:
        raise RuntimeError(f"VTU has no points: {filename}")

    # Geometry
    points = np.asarray(vtk_to_numpy(ug.GetPoints().GetData()))
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"Points must have shape (N, 3), got {points.shape}")

    # Topology
    cells = ug.GetCells()
    connectivity = np.asarray(vtk_to_numpy(cells.GetConnectivityArray()))
    raw_offsets = np.asarray(vtk_to_numpy(cells.GetOffsetsArray()))
    types_ = np.asarray(vtk_to_numpy(ug.GetCellTypesArray()))

    if types_.ndim != 1:
        raise ValueError(f"Cell types must be 1D, got shape={types_.shape}")
    if types_.dtype != np.uint8:
        types_ = types_.astype(np.uint8, copy=False)

    ncells = int(types_.shape[0])

    if raw_offsets.ndim != 1:
        raise ValueError(f"Offsets must be 1D, got shape={raw_offsets.shape}")

    if raw_offsets.shape[0] != ncells + 1:
        raise ValueError(
            f"Offsets length must equal ncells+1 in {filename}: "
            f"{raw_offsets.shape[0]} vs {ncells}+1"
        )

    if raw_offsets[0] != 0:
        raise ValueError(
            f"Offsets must start from 0 in {filename}, got {raw_offsets[0]}"
        )

    offsets = raw_offsets

    if connectivity.ndim != 1:
        raise ValueError(f"Connectivity must be 1D, got shape={connectivity.shape}")

    # PointData
    point_data: Dict[str, np.ndarray] = {}
    pd = ug.GetPointData()
    for i in range(pd.GetNumberOfArrays()):
        arr = pd.GetArray(i)
        if arr is None:
            continue
        name = arr.GetName()
        if not name:
            continue
        np_arr = np.asarray(vtk_to_numpy(arr))
        if np_arr.shape[0] != points.shape[0]:
            raise ValueError(
                f"PointData array '{name}' first dimension mismatch in {filename}: "
                f"{np_arr.shape[0]} vs {points.shape[0]}"
            )
        point_data[name] = np_arr

    # CellData
    cell_data: Dict[str, np.ndarray] = {}
    cd = ug.GetCellData()
    for i in range(cd.GetNumberOfArrays()):
        arr = cd.GetArray(i)
        if arr is None:
            continue
        name = arr.GetName()
        if not name:
            continue
        np_arr = np.asarray(vtk_to_numpy(arr))
        if np_arr.shape[0] != ncells:
            raise ValueError(
                f"CellData array '{name}' first dimension mismatch in {filename}: "
                f"{np_arr.shape[0]} vs {ncells}"
            )
        cell_data[name] = np_arr

    if not np.issubdtype(points.dtype, np.floating):
        raise ValueError(f"Points dtype must be floating, got {points.dtype}")

    return {
        "points": points,
        "connectivity": connectivity,
        "offsets": offsets,  # length = ncells + 1, starting from 0
        "types": types_,
        "point_data": point_data,
        "cell_data": cell_data,
        "npoints": int(points.shape[0]),
        "ncells": ncells,
        "nconn": int(connectivity.shape[0]),
    }


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------
def validate_schema(
    reference: Dict[str, Any], current: Dict[str, Any], filename: str
) -> None:
    ref_pd = set(reference["point_data"].keys())
    cur_pd = set(current["point_data"].keys())
    ref_cd = set(reference["cell_data"].keys())
    cur_cd = set(current["cell_data"].keys())

    if ref_pd != cur_pd:
        raise ValueError(
            f"PointData arrays mismatch in {filename}\n"
            f"reference={sorted(ref_pd)}\ncurrent={sorted(cur_pd)}"
        )
    if ref_cd != cur_cd:
        raise ValueError(
            f"CellData arrays mismatch in {filename}\n"
            f"reference={sorted(ref_cd)}\ncurrent={sorted(cur_cd)}"
        )

    for name in ref_pd:
        a = np.asarray(reference["point_data"][name])
        b = np.asarray(current["point_data"][name])
        if a.ndim != b.ndim:
            raise ValueError(
                f"PointData ndim mismatch for '{name}' in {filename}: {a.ndim} vs {b.ndim}"
            )
        if a.ndim == 2 and a.shape[1] != b.shape[1]:
            raise ValueError(
                f"PointData component mismatch for '{name}' in {filename}: "
                f"{a.shape} vs {b.shape}"
            )
        if a.dtype != b.dtype:
            raise ValueError(
                f"PointData dtype mismatch for '{name}' in {filename}: "
                f"{a.dtype} vs {b.dtype}"
            )

    for name in ref_cd:
        a = np.asarray(reference["cell_data"][name])
        b = np.asarray(current["cell_data"][name])
        if a.ndim != b.ndim:
            raise ValueError(
                f"CellData ndim mismatch for '{name}' in {filename}: {a.ndim} vs {b.ndim}"
            )
        if a.ndim == 2 and a.shape[1] != b.shape[1]:
            raise ValueError(
                f"CellData component mismatch for '{name}' in {filename}: "
                f"{a.shape} vs {b.shape}"
            )
        if a.dtype != b.dtype:
            raise ValueError(
                f"CellData dtype mismatch for '{name}' in {filename}: "
                f"{a.dtype} vs {b.dtype}"
            )

    if current["types"].dtype != np.uint8:
        raise ValueError(
            f"Types dtype must be uint8 in {filename}, got {current['types'].dtype}"
        )

    if current["offsets"].shape[0] != current["ncells"] + 1:
        raise ValueError(
            f"Offsets length must equal ncells+1 in {filename}: "
            f"{current['offsets'].shape[0]} vs {current['ncells']}+1"
        )


def meshes_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return (
        a["npoints"] == b["npoints"]
        and a["ncells"] == b["ncells"]
        and a["nconn"] == b["nconn"]
        and np.array_equal(a["points"], b["points"])
        and np.array_equal(a["types"], b["types"])
        and np.array_equal(a["connectivity"], b["connectivity"])
        and np.array_equal(a["offsets"], b["offsets"])
    )


# ---------------------------------------------------------------------
# VTKHDF initialization
# ---------------------------------------------------------------------
def init_vtkhdf_unstructured(
    root: h5py.Group, sample: Dict[str, Any], cfg: H5Config
) -> None:
    root.attrs["Version"] = np.array([2, 1], dtype=np.int64)
    root.attrs["Type"] = np.bytes_("UnstructuredGrid")

    # Count arrays
    make_1d(root, "NumberOfPoints", ID_DTYPE, cfg)
    make_1d(root, "NumberOfCells", ID_DTYPE, cfg)
    make_1d(root, "NumberOfConnectivityIds", ID_DTYPE, cfg)

    # Main flattened arrays
    make_2d(root, "Points", sample["points"].shape[1], sample["points"].dtype, cfg)
    make_1d(root, "Types", sample["types"].dtype, cfg)
    make_1d(root, "Connectivity", sample["connectivity"].dtype, cfg)
    make_1d(root, "Offsets", sample["offsets"].dtype, cfg)

    # PointData
    pd_group = root.create_group("PointData", track_order=True)
    for name, arr in sample["point_data"].items():
        arr = np.asarray(arr)
        if arr.ndim == 1:
            make_1d(pd_group, name, arr.dtype, cfg)
        elif arr.ndim == 2:
            make_2d(pd_group, name, arr.shape[1], arr.dtype, cfg)
        else:
            raise ValueError(f"Unsupported PointData ndim for '{name}': {arr.ndim}")

    # CellData
    cd_group = root.create_group("CellData", track_order=True)
    for name, arr in sample["cell_data"].items():
        arr = np.asarray(arr)
        if arr.ndim == 1:
            make_1d(cd_group, name, arr.dtype, cfg)
        elif arr.ndim == 2:
            make_2d(cd_group, name, arr.shape[1], arr.dtype, cfg)
        else:
            raise ValueError(f"Unsupported CellData ndim for '{name}': {arr.ndim}")

    # Steps
    steps = root.create_group("Steps", track_order=True)
    steps.attrs["NSteps"] = np.int64(0)

    make_1d(steps, "Values", TIME_DTYPE, cfg)
    make_1d(steps, "PartOffsets", ID_DTYPE, cfg)
    make_1d(steps, "NumberOfParts", ID_DTYPE, cfg)
    make_1d(steps, "PointOffsets", ID_DTYPE, cfg)

    # UnstructuredGrid => NTopologies = 1
    create_dataset(
        group=steps,
        name="CellOffsets",
        shape=(0, 1),
        maxshape=(None, 1),
        dtype=ID_DTYPE,
        chunks=(cfg.chunk_2d_rows, 1),
        cfg=cfg,
    )

    create_dataset(
        group=steps,
        name="ConnectivityIdOffsets",
        shape=(0, 1),
        maxshape=(None, 1),
        dtype=ID_DTYPE,
        chunks=(cfg.chunk_2d_rows, 1),
        cfg=cfg,
    )

    pd_offsets = steps.create_group("PointDataOffsets", track_order=True)
    for name in sample["point_data"].keys():
        make_1d(pd_offsets, name, ID_DTYPE, cfg)

    cd_offsets = steps.create_group("CellDataOffsets", track_order=True)
    for name in sample["cell_data"].keys():
        make_1d(cd_offsets, name, ID_DTYPE, cfg)


# ---------------------------------------------------------------------
# Append data
# ---------------------------------------------------------------------
def append_frame_data(root: h5py.Group, frame: Dict[str, Any]) -> Tuple[int, int, int]:
    """
    Append one frame's geometry/topology/fields to the main VTKHDF arrays.

    Returns
    -------
    point_offset, cell_offset, conn_offset
    """
    if frame["offsets"].shape[0] != frame["ncells"] + 1:
        raise ValueError(
            f"Offsets length must equal ncells+1: "
            f"{frame['offsets'].shape[0]} vs {frame['ncells']}+1"
        )

    point_offset = root["Points"].shape[0]
    cell_offset = root["Types"].shape[0]
    # cell_offset = root["Offsets"].shape[0]
    # cell_offset = point_offset

    conn_offset = root["Connectivity"].shape[0]

    append_1d(root["NumberOfPoints"], [frame["npoints"]])
    append_1d(root["NumberOfCells"], [frame["ncells"]])
    append_1d(root["NumberOfConnectivityIds"], [frame["nconn"]])

    append_2d(root["Points"], frame["points"])
    append_1d(root["Types"], frame["types"])
    append_1d(root["Connectivity"], frame["connectivity"])
    append_1d(root["Offsets"], frame["offsets"])

    for name, arr in frame["point_data"].items():
        arr = np.asarray(arr)
        if arr.ndim == 1:
            append_1d(root["PointData"][name], arr)
        elif arr.ndim == 2:
            append_2d(root["PointData"][name], arr)
        else:
            raise ValueError(f"Unsupported PointData ndim for '{name}': {arr.ndim}")

    for name, arr in frame["cell_data"].items():
        arr = np.asarray(arr)
        if arr.ndim == 1:
            append_1d(root["CellData"][name], arr)
        elif arr.ndim == 2:
            append_2d(root["CellData"][name], arr)
        else:
            raise ValueError(f"Unsupported CellData ndim for '{name}': {arr.ndim}")

    return point_offset, cell_offset, conn_offset


def append_step(
    root: h5py.Group,
    time_value: float,
    frame: Dict[str, Any],
    static_mesh: bool,
    first_mesh_offsets: Tuple[int, int, int] | None,
) -> Tuple[int, int, int] | None:
    steps = root["Steps"]

    # Current part index in NumberOfPoints/Cells/ConnectivityIds arrays
    current_part_offset = root["NumberOfPoints"].shape[0]

    # Field array offsets for this time step
    point_data_offsets = {
        name: root["PointData"][name].shape[0] for name in frame["point_data"].keys()
    }
    cell_data_offsets = {
        name: root["CellData"][name].shape[0] for name in frame["cell_data"].keys()
    }

    if static_mesh:
        if first_mesh_offsets is None:
            first_mesh_offsets = append_frame_data(root, frame)
        else:
            # Counts still grow every step
            append_1d(root["NumberOfPoints"], [frame["npoints"]])
            append_1d(root["NumberOfCells"], [frame["ncells"]])
            append_1d(root["NumberOfConnectivityIds"], [frame["nconn"]])

            # Only fields grow; mesh/topology arrays are reused
            for name, arr in frame["point_data"].items():
                arr = np.asarray(arr)
                if arr.ndim == 1:
                    append_1d(root["PointData"][name], arr)
                elif arr.ndim == 2:
                    append_2d(root["PointData"][name], arr)
                else:
                    raise ValueError(
                        f"Unsupported PointData ndim for '{name}': {arr.ndim}"
                    )

            for name, arr in frame["cell_data"].items():
                arr = np.asarray(arr)
                if arr.ndim == 1:
                    append_1d(root["CellData"][name], arr)
                elif arr.ndim == 2:
                    append_2d(root["CellData"][name], arr)
                else:
                    raise ValueError(
                        f"Unsupported CellData ndim for '{name}': {arr.ndim}"
                    )

        point_offset, cell_offset, conn_offset = first_mesh_offsets
    else:
        point_offset, cell_offset, conn_offset = append_frame_data(root, frame)

    append_1d(steps["Values"], [time_value])
    append_1d(steps["PartOffsets"], [current_part_offset])
    append_1d(steps["NumberOfParts"], [1])
    append_1d(steps["PointOffsets"], [point_offset])

    append_row_2d(steps["CellOffsets"], np.array([[cell_offset]], dtype=ID_DTYPE))
    append_row_2d(
        steps["ConnectivityIdOffsets"], np.array([[conn_offset]], dtype=ID_DTYPE)
    )

    for name, off in point_data_offsets.items():
        append_1d(steps["PointDataOffsets"][name], [off])

    for name, off in cell_data_offsets.items():
        append_1d(steps["CellDataOffsets"][name], [off])

    steps.attrs["NSteps"] = np.int64(int(steps.attrs["NSteps"]) + 1)

    return first_mesh_offsets


# ---------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------
def collect_files(pattern: str) -> List[str]:
    files = sorted(glob.glob(pattern), key=natural_key)
    if not files:
        raise FileNotFoundError(f"No files matched pattern: {pattern}")
    return files


def build_times(
    files: List[str],
    mode: str,
    dt: float = 1.0,
    t0: float = 0.0,
) -> np.ndarray:
    if mode == "index":
        steps = np.arange(len(files), dtype=np.int64)
        return t0 + steps.astype(TIME_DTYPE) * dt

    inferred_steps = [infer_step_from_filename(f) for f in files]

    if mode == "filename":
        if any(s is None for s in inferred_steps):
            raise ValueError("Failed to infer step from at least one filename.")
        steps = np.asarray(inferred_steps, dtype=np.int64)
        return t0 + steps.astype(TIME_DTYPE) * dt

    # auto
    if all(s is not None for s in inferred_steps):
        steps = np.asarray(inferred_steps, dtype=np.int64)
        return t0 + steps.astype(TIME_DTYPE) * dt

    steps = np.arange(len(files), dtype=np.int64)
    return t0 + steps.astype(TIME_DTYPE) * dt


def vtu_series_to_vtkhdf(
    input_pattern: str,
    output_file: str,
    cfg: H5Config,
    time_mode: str = "auto",
    static_mesh: bool = False,
    dt: float = 1.0,
    t0: float = 0.0,
) -> None:
    files = collect_files(input_pattern)
    times = build_times(files, time_mode, dt=dt, t0=t0)

    sample = read_vtu(files[0])

    # Basic sanity checks
    if sample["types"].dtype != np.uint8:
        raise ValueError(f"Types dtype must be uint8, got {sample['types'].dtype}")
    if sample["offsets"].shape[0] != sample["ncells"] + 1:
        raise ValueError(
            f"Offsets length must equal ncells+1 in sample: "
            f"{sample['offsets'].shape[0]} vs {sample['ncells']}+1"
        )

    if static_mesh:
        for f in files[1:]:
            cur = read_vtu(f)
            validate_schema(sample, cur, f)
            if not meshes_equal(sample, cur):
                raise ValueError(
                    f"--static-mesh is enabled, but mesh differs in file: {f}"
                )

    with h5py.File(output_file, "w") as h5f:
        root = h5f.create_group("VTKHDF", track_order=True)
        init_vtkhdf_unstructured(root, sample, cfg)

        first_mesh_offsets = None

        for t, f in zip(times, files):
            frame = read_vtu(f)
            validate_schema(sample, frame, f)

            first_mesh_offsets = append_step(
                root=root,
                time_value=float(t),
                frame=frame,
                static_mesh=static_mesh,
                first_mesh_offsets=first_mesh_offsets,
            )

            print(f"[OK] wrote step t={t} from {f}")

        # Final bounds checks
        steps = root["Steps"]
        if int(steps.attrs["NSteps"]) > 0:
            last_cell_offset = int(steps["CellOffsets"][-1, 0])
            last_ncells = int(root["NumberOfCells"][-1])
            total_offsets = int(root["Offsets"].shape[0])

            if last_cell_offset + last_ncells + 1 > total_offsets:
                raise RuntimeError(
                    "Final Offsets bounds check failed: "
                    f"last_cell_offset={last_cell_offset}, "
                    f"last_ncells={last_ncells}, total_offsets={total_offsets}"
                )

            last_conn_offset = int(steps["ConnectivityIdOffsets"][-1, 0])
            last_nconn = int(root["NumberOfConnectivityIds"][-1])
            total_conn = int(root["Connectivity"].shape[0])

            if last_conn_offset + last_nconn > total_conn:
                raise RuntimeError(
                    "Final Connectivity bounds check failed: "
                    f"last_conn_offset={last_conn_offset}, "
                    f"last_nconn={last_nconn}, total_conn={total_conn}"
                )

    print(f"\nDone: {output_file}")


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert multiple VTU files to one temporal VTKHDF file."
    )
    parser.add_argument(
        "--input",
        required=True,
        help='Input VTU glob pattern, e.g. "step_*.vtu"',
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

    vtu_series_to_vtkhdf(
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
