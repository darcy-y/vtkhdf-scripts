# VTKHDF Scripts

Utilities for converting VTK mesh outputs to VTKHDF files that follow the official VTKHDF standard.

Current scope: VTU and legacy VTK unstructured-grid time series.

Future scope: VTP conversion can be added later, but that path is not active yet.

## Layout

```text
converters/
  vtu_series_to_vtkhdf.py    # active VTU time-series converter
  vtk_series_to_vtkhdf.py    # active legacy VTK time-series converter
scripts/
  batch_convert_vtkhdf.sh    # batch workflow for input/case_* directories
tools/
  add_json_to_hdf.py         # attach case JSON metadata to VTKHDF
  check_time.py              # inspect time steps with vtkHDFReader
legacy/
  vtkxml-to-vtkhdf/          # reference-only old XML converter code
input/                       # ignored local input data
output/                      # ignored local conversion output
```

The `legacy/` directory is kept only as reference material. It is not part of the active conversion workflow.

## Requirements

- Python 3
- `vtk`
- `h5py`
- `numpy`

Install dependencies in your preferred Python environment.

## Convert One VTU Series

From the repository root:

```bash
python3 converters/vtu_series_to_vtkhdf.py \
  --input "input/case_000001/dump/particle/dump_*.vtu" \
  --output output/case_000001.vtkhdf \
  --dt 0.1 \
  --t0 0.1 \
  --time-mode index
```

Time modes:

- `index`: time is `t0 + index * dt`
- `filename`: time is inferred from the last number in each filename
- `auto`: use filename numbers when possible, otherwise use index

Use `--static-mesh` when all time steps share the same mesh topology and only field data changes.

## Convert One Legacy VTK Series

This converter supports legacy `.vtk` files that contain `vtkUnstructuredGrid` data.

```bash
python3 converters/vtk_series_to_vtkhdf.py \
  --input "input/case_000001/dump/particle/dump_*.vtk" \
  --output output/case_000001.vtkhdf \
  --dt 0.1 \
  --t0 0.1 \
  --time-mode index
```

The time options and `--static-mesh` behavior match the VTU converter.

## Batch Convert Cases

The batch script expects case directories like:

```text
input/
  case_000001/
    case_000001.json
    dump/particle/dump_*.vtu
```

Run:

```bash
scripts/batch_convert_vtkhdf.sh input output
```

Optional environment variables:

```bash
DT=0.1 T0=0.1 TIME_MODE=index scripts/batch_convert_vtkhdf.sh input output
```

For each `input/case_*` directory, the script writes `output/case_*.vtkhdf` and stores the matching case JSON under the `CONFIG` group.

## Inspect Time Steps

```bash
python3 tools/check_time.py output/case_000001.vtkhdf
```

## Development Notes

- Keep the active converter aligned with the official VTKHDF specification.
- Read VTK files through VTK Python APIs and convert arrays with `vtk_to_numpy`.
- Keep format-specific logic isolated. When VTP support is added, add a separate converter module instead of mixing that reader into the VTU or legacy VTK paths.
- Do not wire new workflows through `legacy/`; copy only the useful reference behavior into active code.
