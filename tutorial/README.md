# The VTKHDF tutorial

> A gentle introduction to the VTKHDF file format

VTKHDF is a new generation file format to store VTK datasets, that was introduced in 2021, and still being improved as of 2025. This format succeeds XML-based VTK file formats, using a unified API and a single extension for all the different data types it can contain. The general structure of a VTKHDF file is the same for all data types.

[[_TOC_]]

## VTKHDF Basics

VTKHDF is a specification based on the HDF5 container format. This tutorial uses the h5py (3.13.0) Python module to build data files, which you can then read using ParaView (>=6.0). Each step should yield a valid file, progressively enabling more features of the format.

Using the HDF5 container format, the VTKHDF standard defines a hierarchy of groups and datasets, the root of all of them being the `VTKHDF` group. All other root HDF5 groups will be ignored by the reader. The `VTKHDF` group needs to have 2 attributes: `Version`, a vector of 2 elements defining the version of the reader required to read the current file, and `Type`, a fixed-length string indicating which type of dataset should be read.

Using h5py, you can create a new HDF5 file, create a VTKHDF group and the required attributes for an unstructured grid:

```python
import h5py as h5
file = h5.File("step1.vtkhdf", "w")
root = file.create_group("VTKHDF")
root.attrs["Version"] = (2, 3)
root.attrs["Type"] = "UnstructuredGrid"
```

## Creating a basic Unstructured Grid

Unstructured Meshes are one of the base data types that VTKHDF can encode. Unstructured Meshes are defined using points, meshed together to form cells. In this example, we will write a file creating 2 cells, one tetrahedron and one triangle.

First, let's define the cell types we need, and write the `Types` dataset. This dataset lists in order the identifiers of each cell in our data. We have 2 cells in this example, which means the `Types` dataset will have a length of 2. We can look up in the [VTK Documentation](https://vtk.org/doc/nightly/html/vtkCellType_8h.html) which ids the tetrahedron and triangle cell types have in VTK. `VTK_TETRA` has id `10`, and `VTK_TRIANGLE` has id `5`. The `Types` dataset will therefore contain 2 values: `[10, 5]`. Of course, if we wanted to add more triangles, we would need to add the value `5` multiple times. Note that polyhedron and other more complex types of cells are not supported yet.

```python
VTK_TETRA = 10
VTK_TRIANGLE = 5
cell_types = (
    VTK_TETRA,
    VTK_TRIANGLE,
)
root.create_dataset("Types", data=cell_types, dtype="uint8")
root.create_dataset("NumberOfCells", data=(len(cell_types),), dtype="i8")
```

Then, VTKHDF is required to define the points in a 2-dimensional `Points` dataset, using the float type, with the X, Y and Z coordinates spanning the second dimension. These points will be the edges of the 2 cells we will be creating. We must also create a dataset containing a single value, `NumberOfPoints`. This design choice will matter once we start writing datasets with multiple pieces or time steps.

```python
points = (
    (0.0, 0.0, 0.0),
    (2.0, 0.0, 0.0),
    (1.0, 2.0, 0.0),
    (1.0, 0.0, 2.0),
    (2.0, 3.0, 0.0),
    (1.0, 4.0, 0.0),
)
root.create_dataset("NumberOfPoints", data=(len(points),), dtype="i8")
root.create_dataset("Points", data=points, dtype="f")
```

To build cells out of these points, we need to define a connectivity array. The connectivity array tells the reader which point identifiers belong to each cell. A tetraheron has 4 edges, and a triangle has 3. Points can be common between several cells. Here, the point with the id "2", which is the third in the `Points` list we defined earlier, is common between the 2 cells.

```python
tetra_connectivity = (0, 1, 2, 3)
triangle_connectivity = (2, 4, 5)
connectivity = tetra_connectivity + triangle_connectivity
root.create_dataset("NumberOfConnectivityIds", data=(len(connectivity),), dtype="i8")
root.create_dataset("Connectivity", data=connectivity, dtype="i8")
```

Finally, we need to write the `Offsets` dataset, which counts, for each cell, the number of connectivity ids to offset by when reading the connectivity of the cell. This dataset's size is one more than the `Types` array, because it is also required to write the offset after the final cell. For our example, we need to read the connectivity array for the first cell from the start of the `Connectivity` dataset (id `0`). For the second cell, we offset by the number of points in the first tetrahedron cell, so the value is `4`. Lastly, after reading the connectivity of the triangle cell, we are `7` values into the connectivity array.

```python
offsets = (0, len(tetra_connectivity), len(tetra_connectivity+triangle_connectivity))
root.create_dataset("Offsets", data=offsets, dtype="i8")
```

With these datasets created, we now have a basic VTKHDF file that we can open in ParaView. You can find the full code for this step in [step1.py](/tutorial/scripts/step1.py).

## Adding fields

Now, let's see how to set values for points and cells on the geometry we defined previously. In VTKHDF, point data is stored in datasets located in the `PointData` group. Here, we create a `Pressure` point field, with a value for each of the 6 points:

```python
point_data = root.create_group("PointData")
pressure_field = (1.5, 1.2, 1.3, 1.4, 2.2, 0.4)
point_data.create_dataset("Pressure", data=(pressure_field), dtype="f")
```

We can do the same for cell data, stored in the `CellData` group. For each of the 2 cells, we define a 3-components velocity field.
```python
velocity_field= (
    (2.0,1.1,1.3),
    (1.4,0.9,1.5),
)
cell_data = root.create_group("CellData")
cell_data.create_dataset("Velocity", data=(velocity_field), dtype="f")
```

VTKHDF can also store 'field' data, which is not attached to the geometry:
```python
field_data = root.create_group("FieldData")
field_data.create_dataset("Temperature", data=(273,), dtype="i8")
```

You can find the full code for this step in [step2.py](/tutorial/scripts/step2.py).

## Time steps

VTKHDF natively supports temporal (transient) datasets, where the geometry and/or field values might change over time.
To create a temporal VTKHDF dataset, we need to add additional data to the existing datasets we created previously, and add meta information in a new `Steps` group, that controls the read offsets for each time step. Since temporal data often is generated incrementally with no knowledge of the entire number of time steps, it is convenient to be able to add new data per every time step.
The logic of "adding values" to an existing dataset is made possible by the ["Chunked storage" of HDF5](https://docs.h5py.org/en/stable/high/dataset.html#chunked-storage), which allows for resizable datasets. In practice, that means that we need to initialize chunked datasets with an infinite max size in the first dimension, and then resize and append data to them on each time step. 
Note that controlling the chunk size used when writing is crucial for high-performance reading.

To this end, all datasets are created with a null initial shape:

```python
point_data = root.create_group("PointData")
point_data.create_dataset("Pressure", shape=(0,), maxshape=(None,), dtype="f")
```

This creates a 1-dimensional chunked (resizable) dataset with an initial size of 0. The `maxshape` argument ensures that the dataset is written using chunked storage. You can control the size of chunks using the `chunks` argument. The chosen chunk size can affect caching and reading performance, as well as file size.

For a 2-dimensional dataset, for instance storing 3-coordinates point positions, we only need to grow the first dimension, and keep the second one to a constant size of 3:
```python
root.create_dataset("Points", shape=(0, 3), maxshape=(None, 3), dtype="f")
```

Adding data to these chunked requires some extra effort: we need to first resize the dataset to fit the data for the new time step, and then copy the data array to the newly allocated space. Let `dataset` be a chunked `h5.Dataset`, and `array` any collection of items we want to add to the dataset, we define the `append_dataset` function as:

```python
def append_dataset(dataset: h5.Dataset, array: typing.Tuple):
    original_size = dataset.shape[0]
    dataset.resize(original_size + len(array), axis=0)
    dataset[originalLength:] = array
```

This function can then be used as:

```python
append_dataset(root["Types"],(VTK_TETRA, VTK_TRIANGLE))
```

The VTKHDF format stores data in one flattened array per data type. As the VTKHDF reader must be able to read time steps in any order, we need to set offsets to read into the chunked datasets for each time step. These offsets are defined in the `Steps` group. The time step meta data then provides the information on which part of the flattened array corresponds to which time-step via offsets (integers that tell where to look in the flattened array).

Let's say that each time step has 6 points in the mesh. For time step 0, the read offsets into the `"Points"` dataset will be `0`. For the second step, we should read at offset `6`, after the points written for the first time step. For a dataset of 10 time steps, we should have 10 offset values in the `"Steps/PointOffsets"` metadata dataset.

The same way, the `"Steps`" group should also contain offset values `"CellOffsets"`, which tells the reader by how many cells it should offset reading the `"Types"` array, `"ConnectivityOffsets"` for connectivity, and `"PartOffsets"`. The latter gives the information of how many parts (pieces) we should offset reading into the `"NumberOf[Cells/ConnectivityIds/Points]"` datasets. Each time step can decompose data into multiple pieces, that can be distributed across MPI ranks when reading from ParaView. In our case, we have one partition per time step, so `"PartOffset"`'s value for each time step should be equal to one more than the previous value.

Finally, we also need to add a `"NumberOfParts"` dataset in the `"Steps"` group, to specify how many pieces should be read for each time step. Here, we have 1 part for each time step, so this is equal to 1.

```python
append_dataset(steps["PartOffsets"], (step,))
append_dataset(steps["NumberOfParts"], (1,))
```

In the previous steps, the number of parts could be deduced by the reader by reading the length of `"NumberOf[Cells/ConnectivityIds/Points]"`, but here, we need to specify manually how many parts each time step has, and by how many we need to offset.

Each Point, Cell and Field data should also have an offset, defined in `"Steps/[Point/Cell/Field]DataOffsets/[Field]"`.

You can find the full code for this step in [step3.py](/tutorial/scripts/step3.py). We have functions for initializing chunked dataset for the geometry, field data and the steps group. Then, on each new time step, we write new geometry, field values and offsets in the `"Steps"` group.

## Static meshes

The offsets described in the previous section allow creative use for optimization. If we set a read offset for a given time step to the same value as the previous time step, we will not need to write (and read) the dataset twice. This is used to create static meshes, where the geometry does not change but field values do.

Let's say that now, our geometry is constant between time steps. We don't need to write the `"Points"`, `"Types"` and `"Connectivity"` again for each new time step, but only for the first one. Then, when writing offsets in the `"Steps"` group, we use offset `0`, so that for all time steps, we read the same geometry as the same time step.

```
append_dataset(steps["PartOffsets"], (0,))
append_dataset(steps["NumberOfParts"], (1,))
append_dataset(steps["PointOffsets"], (0,))
append_dataset(steps["CellOffsets"], (0,))
append_dataset(steps["ConnectivityIdOffsets"], (0,))
```

We will also benefit from static mesh optimizations and caching allowed by VTK when reading.

You can find the full code for this step in [step4.py](/tutorial/scripts/step4.py).

## More Data types

Unstructured grids, while very common, are not the only data type supported by VTKHDF. The VTKHDF documentation specifies, among others, the ImageData format. An image data represents regular structured data, defined using an origin, spacing and extent.

Points and cells are defined implicitly, so we have much fewer datasets to write. In fact, the image properties are only defined through attributes of the root (`"/VTKHDF"`) group:

```python
root.attrs.create("WholeExtent", (0.0, 2.0, 0, 2.0, 0.0, 1.0), dtype="f")
root.attrs.create("Origin", (10.0, 10.0, 2.0), dtype="f")
root.attrs.create("Spacing", (1.0, 1.0, 1.0), dtype="f")
root.attrs.create('Direction',  (1, 0, 0, 0, 1, 0, 0, 0, 1), dtype="f")
```
We set the extent of the image to be 0->2 on X, 0->2 on Y and 0->1 on the Z axis, with a spacing of 1.0 in each direction. This will create a regular image with 2x2x1 cells. We set the origin so that the starting point is (10, 10, 2), and the direction 3x3 matrix so the image grows in the +X, +Y and +Z directions without rotation or scaling.

Let's now add cell and point data. This image has 2x2x1 = 4 cells, and 3*3*2 = 18 points; The point and cell arrays need to have the shape of the ImageData, so they have respectively shapes (2,2,2) and (3,3,3):

```python
cell_data = root.create_group("CellData")
cell_data.create_dataset(
    "ID",
    data=(
        ((1, 2), (3, 4)),
        ((5, 6), (7, 8)),
    ),
    dtype="f",
)
point_data = root.create_group("PointData")
point_data.create_dataset(
    "Velocity",
    data=(
        ((1.0, 2.0, 3.0), (1.3, 2.3, 3.3), (1.5, 2.6, 3.6)),
        ((1.2, 2.2, 3.2), (1.1, 2.1, 3.1), (1.8, 2.8, 3.8)),
        ((1.5, 2.5, 3.5), (1.4, 2.4, 3.4), (1.9, 2.9, 3.9)),
    ),
    dtype="f",
)
```

We have built an ImageData VTKHDF file that we can open in ParaView!

You can find the full code for this step in [step5.py](/tutorial/scripts/step5.py).

## Composite structures

One can create composite structures made of multiple VTKHDF meshes. For this, we initialize the VTKHDF filetype to "PartitionedDataSetCollection", one of the composite types supported by VTKHDF.

```python
root.attrs["Type"] = "PartitionedDataSetCollection"
```

We can use the [External Links](https://docs.h5py.org/en/stable/high/group.html#external-links) feature from HDF5 to reference datasets from external files. Here, we want to build a composite dataset made of datasets created in previous steps. We create 2 datasets in the root, referencing the `"/VTKHDF"` group of steps 2 and 5.

```python
root["ImageBlock"] = h5.ExternalLink("step5.vtkhdf", "/VTKHDF")
root["UnstructuredBlock"] = h5.ExternalLink("step2.vtkhdf", "/VTKHDF")
```

Note that using external links to reference meshes from existing files is not mandatory, it is also possible to write all data in the main file directly.

Composite blocks need to have an index attribute, so they can be referenced in the reader:
```python
root["ImageBlock"].attrs["Index"] = 1
root["UnstructuredBlock"].attrs["Index"] = 0
```

Once we have our base leaf blocks for the composite structure, we can create an Assembly which represents the tree structure that organizes them. Blocks living in the root group are referenced in the assembly using [HDF5 Soft links](https://docs.h5py.org/en/stable/high/group.html#soft-links).

```python
assembly = root.create_group("Assembly", track_order=True)
assembly["BlockName0"] = h5.SoftLink("/VTKHDF/ImageBlock")
assembly_group = assembly.create_group("Group0", track_order=True)
assembly_group["BlockName1"] = h5.SoftLink("/VTKHDF/ImageBlock")
assembly_group["BlockName2"] = h5.SoftLink("/VTKHDF/UnstructuredBlock")
```

Importantly, the `VTKHDF` group, assembly group and all children need to be created with `track_order=True`, so the composite structure keeps track of an order of children in the assembly. A top-level block can be referenced multiple times, which is what we do with the Image block, used twice in the Assembly.

Composite meshes can have time steps, but each individual block need to have the same number of steps and time values.

You can find the full code for this step in [step6.py](/tutorial/scripts/step6.py). Make sure you have run `step2.py` and `step5.py` in the same Working Directory beforehand.

## Reading and writing VTKHDF in VTK

Unlike the XML formats, there is only a single reader for VTKHDF files in VTK. The output data type of this reader will depend on both the data type stored in the file and the number of pieces stored for a given time step. For a file containing one piece per time step, the output type will be a non-composite type (e.g. vtkUnstructuredGrid). For non-composite datasets containing more than 1 piece per time step, the reader will output a vtkPartitionedDataSet.

There is also a vtkHDFWriter class capable of writing VTKHDF files to disk. As of early 2025, only vtkUnstructuredGrid and vtkPolyData data sets can be written using it, as well as composite types based on those.

Here is a simple script using the VTK Python module, creating a sphere using VTK, writing it to disk using vtkHDFWriter, then loading it using vtkHDFReader and displaying it. This script requires VTK >= 9.5.

```python
from vtkmodules.vtkFiltersSources import vtkSphereSource
from vtkmodules.vtkRenderingCore import (
    vtkPolyDataMapper,
    vtkActor,
    vtkRenderWindow,
    vtkRenderer,
    vtkRenderWindowInteractor,
)
from vtkmodules.vtkIOHDF import vtkHDFReader, vtkHDFWriter
import vtkmodules.vtkRenderingOpenGL2
import vtkmodules.vtkInteractionStyle

sphere = vtkSphereSource(radius=2.0, theta_resolution=32, phi_resolution=32)

writer = vtkHDFWriter(file_name="sphere.vtkhdf")
sphere >> writer
writer.Write()

reader = vtkHDFReader(file_name="sphere.vtkhdf")

mapper = vtkPolyDataMapper()
reader >> mapper

actor = vtkActor(mapper=mapper)
actor.GetProperty().SetColor(0, 0.3, 1)

renderer = vtkRenderer()
renderer.AddActor(actor)
renderer.SetBackground(0, 0, 0)

ren_win = vtkRenderWindow()
ren_win.AddRenderer(renderer)

iren = vtkRenderWindowInteractor()
iren.SetRenderWindow(ren_win)

ren_win.Render()
iren.Start()
```

## VTKHDF in ParaView

ParaView supports reading and writing from/to VTKHDF natively. ParaView will automatically use vtkHDFReader to open `.hdf` and `.vtkhdf` files, if all the metadata is set up correctly. If ParaView does not recognize a file using one of these extensions, it will open a window to select another reader. This means that the file it was given is not correct and does not conform to the VTKHDF specification.

## Resources

- [VTKHDF format specification](https://docs.vtk.org/en/latest/vtk_file_formats/vtkhdf_file_format/vtkhdf_specifications.html)
- [H5PY documentation](https://docs.h5py.org/en/stable/)
- [HDF5 C API reference](https://support.hdfgroup.org/documentation/hdf5/latest/_r_m.html)
- [HDFView software, for inspecting and editing HDF5 files](https://www.hdfgroup.org/download-hdfview/)
- [HDF5View, a lighter Qt-based HDF5 viewer](https://github.com/tgwoodcock/hdf5view)
