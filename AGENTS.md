# AGENTS.md

## Project Purpose

This repository is for converting VTK XML/legacy-style mesh outputs into VTKHDF files that follow the official VTKHDF format specification.

Current active scope: VTU and legacy VTK unstructured-grid conversion.

Planned or historical formats such as VTP may be useful context, but do not implement or change those paths unless the user explicitly asks for them.

## Active Code

- `converters/vtu_series_to_vtkhdf.py` is the primary converter.
- `converters/vtk_series_to_vtkhdf.py` converts legacy `.vtk` unstructured-grid series.
- `scripts/batch_convert_vtkhdf.sh` and `tools/add_json_to_hdf.py` are supporting workflow scripts.
- `tools/` contains helper/checking code.

## Legacy Code

Code under `legacy/` is reference-only. Treat it as historical material for understanding previous behavior or VTKHDF layout choices.

Do not restore, extend, or wire new workflows through legacy scripts unless the user explicitly asks for that. If legacy behavior is useful, copy only the relevant idea into the active VTU path with a small, direct implementation.

## Implementation Rules

- Follow the official VTKHDF standard for file layout, dataset names, offsets, types, and time-series structure.
- Prefer VTK Python APIs and `vtkmodules.util.numpy_support.vtk_to_numpy` for reading VTK data.
- Keep changes surgical. Do not refactor unrelated scripts or revive deleted XML conversion tooling.
- Preserve existing command-line behavior unless a requested fix requires changing it.
- Validate VTU assumptions explicitly, especially point shape, cell connectivity, offsets, cell types, and point/cell data lengths.
- Use simple h5py/numpy code over new abstractions unless repeated active code clearly needs a helper.

## Verification

For converter changes, run the smallest practical check available:

```bash
python3 converters/vtu_series_to_vtkhdf.py --help
python3 converters/vtk_series_to_vtkhdf.py --help
```

When sample VTU or VTK inputs are present, also run a real conversion against one small input or series and inspect the generated VTKHDF structure with `h5dump`, `h5ls`, or Python/h5py.

If dependencies such as VTK or h5py are missing, report that clearly instead of guessing.
