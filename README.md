# VTKHDF-scripts

## 🔧 Custom Modifications

- Add the `h5_dset_kwargs` function in `vtkxml-to-vtkhdf.py` to compress the vtkhdf file. The chunk size will calculate automatically based on the data shape.
- Run `vtkxml2vtkhdf.sh` to convert files.
- Automatically put vtkhdf file in `output/` dir.

---

> [!NOTE]
> Below is the original content.

Repository used to store h5py scripts to generate VTKHDF file format based on the [file format specification](https://docs.vtk.org/en/latest/vtk_file_formats/vtkhdf_file_format/vtkhdf_specifications.html).

## Tutorial

An introduction to writing VTKHDF files can be found in [Tutorial](/tutorial/README.md).

## VTKHDF Generation scripts

`scripts` folder contains h5py scripts to generate VTKHDF File format. For now we can generate:

- PolyData
- UnstructuredGrid, with and without polyhedrons
- ImageData
- Overlapping AMR
- Composite Datasets (PartitionedDataSetCollection)
- HyperTreeGrid

Note that the script writing temporal data requires `vtkpython`.

## vtkxml-to-vtkhdf

This folder contains a script named vtkxml-to-vtkhdf.py which converts VTK XML image data and unstructured grid, serial and parallel formats to the VTK HDF format.

We include a simple test script called `test.sh` that converts a file stored using each of the supported input formats into VTK HDF and then it checks the results. The script should not produce any difference with the stored baselines.

To be able to use this `test.sh`, it will be needed to clone the sample data repository : https://gitlab.kitware.com/keu-public/vtkhdf/vtkhdf-data-samples. An editing theses 2 variables:
- `VTK_PYTHONPATH` : for where your vtkpython is located
- `VTKHDF_DATA_SAMPLES_LOCATION` : for where the data samples repository has been cloned.

Note that to be able to use this `test.sh`, you will need to clone this repository which have

## License

This repository is under the Apache 2.0 license, see NOTICE and LICENSE file.
