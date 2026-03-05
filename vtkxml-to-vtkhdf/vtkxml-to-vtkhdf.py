#!/usr/bin/env python3
"""
Converts a vti/pvti or vtu/pvtu to a VTK HDF file.
"""
import argparse
import os.path
import sys
import h5py
import numpy as np
from vtkmodules.util.numpy_support import vtk_to_numpy
from vtkmodules.vtkIOXML import (vtkXMLImageDataReader, vtkXMLUnstructuredGridReader,
    vtkXMLPImageDataReader, vtkXMLPUnstructuredGridReader)
from vtkmodules.vtkCommonExecutionModel import vtkStreamingDemandDrivenPipeline
from vtkmodules.vtkCommonCore import VTK_IMAGE_DATA, VTK_UNSTRUCTURED_GRID

# ------------------------------------------------------------------------------
def h5_dset_kwargs(shape, dtype, maxshape=None):
    """
    Return robust HDF5 dataset kwargs for smaller vtkhdf:
    - gzip compression (portable)
    - shuffle filter (improves compression for numeric arrays)
    - chunking (required for compression and for resizable datasets)
    """
    # --- choose chunk shape ---
    # HDF5 chunks are best when chunk bytes ~ 1–8 MB (rule of thumb).
    # We'll chunk along the first dimension.
    if len(shape) == 1:
        n0 = shape[0]
        c0 = min(max(1, n0), 1_000_000)   # cap to avoid tiny chunks
        chunks = (c0,)
    else:
        n0 = shape[0]
        # pick rows per chunk so that chunk ~ a few MB
        # rough bytes per row:
        itemsize = getattr(dtype, "itemsize", None) or 8
        row_bytes = itemsize
        for s in shape[1:]:
            row_bytes *= s
        target = 4 * 1024 * 1024  # 4MB
        c0 = max(1, min(n0, target // max(row_bytes, 1)))
        chunks = (c0,) + tuple(shape[1:])

    return dict(
        maxshape=maxshape,
        chunks=chunks,
        compression="gzip", 
        compression_opts=4,  # 1 faster、9 smaller, 4 is balance
        shuffle=True,
    )


# ------------------------------------------------------------------------------
def create_dataset(name, anp, group, number_of_pieces):
    """
    Create a HDF dataset 'name' inside 'group' from numpy array 'anp'.
    If number_of_pieces > 1 we create a dataset with size unlimited.
    """
    shape = anp.shape
    if number_of_pieces > 1:
        maxshape = (None,) + shape[1:]
    else:
        maxshape = shape
    # dset = group.create_dataset(
    #     name, shape, anp.dtype, maxshape=maxshape)
    kwargs = h5_dset_kwargs(shape, anp.dtype, maxshape=maxshape)
    dset = group.create_dataset(name, shape=shape, dtype=anp.dtype, **kwargs)
    dset[0:] = anp
    return dset


# ------------------------------------------------------------------------------
def append_dataset(dset, anp, size):
    """
    Append a numpy array 'anp' to a HDF dataset 'dset' of 'size'.
    'size' parameter is needed as sometimes we allocate memory
    for the whole HDF file, so dset.size is different than 'size'
    Returns the new size of dset.
    """
    if dset.size != size:
        print("dset.size={}, size={}".format(dset.size, size))
    new_size = size + anp.shape[0]
    dset.resize(new_size, axis=0)
    dset[size:] = anp
    return new_size


def vtk_to_numpy_imagedata(array, extent, field_location):
    """
    Convert array to a numpy array with the same shape as the original image
    data.
    """
    number_of_components = array.GetNumberOfComponents()
    point_adjustment = 1 if field_location == 0 else 0
    anp = vtk_to_numpy(array)
    dims = [extent[1] - extent[0] + point_adjustment,
            extent[3] - extent[2] + point_adjustment,
            extent[5] - extent[4] + point_adjustment]
    # reverse order of dimensions to account for VTK fortran axis order
    dims.reverse()
    dims.append(number_of_components)
    anp = np.reshape(anp, np.array(dims))
    return anp


# ------------------------------------------------------------------------------
def append_nparray_imagedata(dset, anp, extent, whole_extent, ndims):
    """
    Append a numpy array 'anp' to a HDF dataset 'dset', using hyperslabs.
    """
    # flip axis order to account for VTK fortran order
    start = (extent[4] - whole_extent[4],
             extent[2] - whole_extent[2],
             extent[0] - whole_extent[0],
             0)
    dims = anp.shape
    index = (slice(start[0], start[0] + dims[0], None),
             slice(start[1], start[1] + dims[1], None),
             slice(start[2], start[2] + dims[2], None),
             slice(start[3], start[3] + dims[3], None))
    index = index[:ndims]
    start = start[:ndims]
    dims = dims[:ndims]
    anp = np.reshape(anp, np.array(dims))
    print("whole_extent: {}".format(whole_extent))
    print("extent: {}".format(extent))
    print("Set array of shape {} at start {}".format(anp.shape, start))
    dset[index] = anp
    return dset


# ------------------------------------------------------------------------------
def append_dataset_imagedata(
        dset, array, extent, whole_extent, field_location, ndims):
    """
    Append an array to a HDF dataset 'dset', using hyperslabs.
    """
    anp = vtk_to_numpy_imagedata(array, extent, field_location)
    return append_nparray_imagedata(dset, anp, extent, whole_extent, ndims)


# ------------------------------------------------------------------------------
def count_dims(dims):
    """
    Remove dimensions one from the end of an array shape
    """
    ndims = len(dims)
    for dim in reversed(dims):
        if dim > 1:
            break
        ndims = ndims - 1
    return ndims


# ------------------------------------------------------------------------------
def create_dataset_imagedata(
        array, group, extent, whole_extent, field_location):
    """
    Create a dataset for an image data array and store the first piece
    """
    number_of_components = array.GetNumberOfComponents()
    point_adjustment = 1 if field_location == 0 else 0
    whole_dims = [
        whole_extent[1] - whole_extent[0] + point_adjustment,
        whole_extent[3] - whole_extent[2] + point_adjustment,
        whole_extent[5] - whole_extent[4] + point_adjustment]
    whole_dims.reverse()
    whole_dims.append(number_of_components)
    ndims = count_dims(whole_dims)
    whole_dims = whole_dims[:ndims]
    anp = vtk_to_numpy_imagedata(array, extent, field_location)
    name = array.GetName()
    dset = group.create_dataset(
        name, whole_dims, anp.dtype)
    print("Create HDF dataset maxshape={}".format(whole_dims))
    return (
        append_nparray_imagedata(dset, anp, extent, whole_extent, ndims),
        ndims)


# ------------------------------------------------------------------------------
def setup_reader(input_file_ext):
    """
    Setup reader based on the file extension
    """
    dataset_type = -1
    parallel = False
    reader = None
    if input_file_ext == '.vti':
        dataset_type = VTK_IMAGE_DATA
        reader = vtkXMLImageDataReader()
    elif input_file_ext == '.vtu':
        dataset_type = VTK_UNSTRUCTURED_GRID
        reader = vtkXMLUnstructuredGridReader()
    elif input_file_ext == '.pvti':
        dataset_type = VTK_IMAGE_DATA
        parallel = True
        reader = vtkXMLPImageDataReader()
    elif input_file_ext == '.pvtu':
        dataset_type = VTK_UNSTRUCTURED_GRID
        parallel = True
        reader = vtkXMLPUnstructuredGridReader()
    else:
        raise RuntimeError(
            "Conversion for {} not implemented".format(input_file_ext))
    return (dataset_type, parallel, reader)


# ------------------------------------------------------------------------------
def request_piece(reader, parallel, piece):
    """
    Ask the 'reader' for 'piece'. Returns the number_of_pieces available
    """
    if parallel:
        reader.UpdateInformation()
        number_of_pieces = reader.GetNumberOfPieces()
        out_info = reader.GetOutputInformation(0)
        out_info.Set(
            vtkStreamingDemandDrivenPipeline.UPDATE_NUMBER_OF_PIECES(),
            number_of_pieces)
        out_info.Set(
            vtkStreamingDemandDrivenPipeline.UPDATE_PIECE_NUMBER(), piece)
        reader.PropagateUpdateExtent()
    else:
        number_of_pieces = 1
    reader.Update()
    data = reader.GetOutputDataObject(0)
    return (number_of_pieces, data)


# ------------------------------------------------------------------------------
def create_support_imagedata(reader, data, vtkhdf_group):
    """
    Create attributes WholeExtent, Origin, Spacing, Direction
    needed for an ImageData. Note that we don't split an
    image data into pieces. We rely on hdf5 chunking to
    optimize reading for given number of MPI ranks.
    """
    vtkhdf_group.attrs.create("Type", np.bytes_("ImageData"))
    out_info = reader.GetOutputInformation(0)
    whole_extent = out_info.Get(
        vtkStreamingDemandDrivenPipeline.WHOLE_EXTENT())
    vtkhdf_group.attrs.create("WholeExtent", whole_extent)
    # Origin, Spacing and Direction are the same for all pieces.
    # so we can use the first piece values
    vtkhdf_group.attrs.create("Origin", data.GetOrigin())
    vtkhdf_group.attrs.create("Spacing", data.GetSpacing())
    vtkhdf_group.attrs.create("Direction",
                              data.GetDirectionMatrix().GetData())
    return whole_extent


# ------------------------------------------------------------------------------
def create_support_unstructuredgrid(data, number_of_pieces, vtkhdf_group):
    """
    Creates datasets needed for an unstructured grid: NumberOfConnectivityIds,
    NumberOfPoints, NumberOfCells (needed for showing pieces),
    Points, Connectivity, Offsets, Types
    """
    vtkhdf_group.attrs.create("Type", np.bytes_("UnstructuredGrid"))
    cells = data.GetCells()
    number_of_connectivity_ids = vtkhdf_group.create_dataset(
        "NumberOfConnectivityIds", (number_of_pieces,), np.int64)
    number_of_connectivity_ids[0] = cells.GetNumberOfConnectivityIds()
    number_of_points = vtkhdf_group.create_dataset(
        "NumberOfPoints", (number_of_pieces,), np.int64)
    number_of_points[0] = data.GetNumberOfPoints()
    number_of_cells = vtkhdf_group.create_dataset(
        "NumberOfCells", (number_of_pieces,), np.int64)
    number_of_cells[0] = cells.GetNumberOfCells()

    anp = vtk_to_numpy(data.GetPoints().GetData())
    points = create_dataset(
        "Points", anp, vtkhdf_group, number_of_pieces)
    points_size = anp.shape[0]
    anp = vtk_to_numpy(cells.GetConnectivityArray())
    connectivity = create_dataset(
        "Connectivity", anp, vtkhdf_group, number_of_pieces)
    connectivity_size = anp.shape[0]
    anp = vtk_to_numpy(cells.GetOffsetsArray())
    offset = create_dataset(
        "Offsets", anp, vtkhdf_group, number_of_pieces)
    offset_size = anp.shape[0]
    anp = vtk_to_numpy(data.GetCellTypesArray())
    types = create_dataset(
        "Types", anp, vtkhdf_group, number_of_pieces)
    types_size = anp.shape[0]
    return (points, points_size, connectivity, connectivity_size,
            offset, offset_size, types, types_size,
            number_of_connectivity_ids, number_of_points, number_of_cells)


# ------------------------------------------------------------------------------
def append_support_unstructuredgrid(
        piece, data,
        points, points_size, connectivity, connectivity_size,
        offset, offset_size, types, types_size,
        number_of_connectivity_ids, number_of_points, number_of_cells):
    """
    Appends to geometry and connectivity datasets for unstructured grid
    """
    cells = data.GetCells()
    number_of_connectivity_ids[piece] = cells.GetNumberOfConnectivityIds()
    number_of_points[piece] = data.GetNumberOfPoints()
    number_of_cells[piece] = cells.GetNumberOfCells()
    anp = vtk_to_numpy(data.GetPoints().GetData())
    old_points_size = points_size
    points_size = append_dataset(points, anp, points_size)
    print("Append points, old: {}, new: {}".format(old_points_size, points_size))
    anp = vtk_to_numpy(cells.GetConnectivityArray())
    connectivity_size = append_dataset(
        connectivity, anp, connectivity_size)
    anp = vtk_to_numpy(cells.GetOffsetsArray())
    offset_size = append_dataset(offset, anp, offset_size)
    anp = vtk_to_numpy(data.GetCellTypesArray())
    types_size = append_dataset(types, anp, types_size)
    return (points_size, connectivity_size, offset_size, types_size)


# ------------------------------------------------------------------------------
def create_data_arrays(data, dataset_type, vtkhdf_group, attribute_type_names,
                       all_field_datasets,
                       all_field_datasets_size, number_of_pieces,
                       extent, whole_extent, all_ndims):
    """
    Write data piece 0
    """
    for attribute_type, attribute_type_name in enumerate(
            attribute_type_names):
        field_data = data.GetAttributesAsFieldData(attribute_type)
        if field_data.GetNumberOfArrays() > 0:
            field_data_group = vtkhdf_group.create_group(
                attribute_type_name)
            # only for POINT and CELL attributes
            if attribute_type < 2:
                for field_type in ["Scalars", "Vectors", "Normals",
                                   "Tensors", "TCoords"]:
                    array = getattr(field_data, "Get{}".format(field_type))()
                    if array:
                        field_data_group.attrs.create(
                            field_type, np.bytes_(array.GetName()))

            # FIELD attribute
            if attribute_type == 2:
                for i in range(field_data.GetNumberOfArrays()):
                    array = field_data.GetArray(i)
                    if not array:
                        array = field_data.GetAbstractArray(i)
                        if array.GetClassName() == "vtkStringArray":
                            dtype = h5py.special_dtype(vlen=bytes)
                            dset = field_data_group.create_dataset(
                                array.GetName(),
                                (array.GetNumberOfValues(),), dtype)
                            for index in range(array.GetNumberOfValues()):
                                dset[index] = array.GetValue(index)
                        else:
                            # don't know how to handle this yet. Just skip it.
                            print("Error: Don't know how to write "
                                  "an array of type {}".format(
                                      array.GetClassName()))
                    else:
                        anp = vtk_to_numpy(array)
                        dset = field_data_group.create_dataset(
                            array.GetName(), anp.shape, anp.dtype)
                        dset[0:] = anp
            else:
                for i in range(field_data.GetNumberOfArrays()):
                    array = field_data.GetArray(i)
                    if dataset_type == VTK_IMAGE_DATA:
                        dset, ndims = create_dataset_imagedata(
                            array, field_data_group,
                            extent, whole_extent, attribute_type)
                        all_ndims[attribute_type].append(ndims)
                    elif dataset_type == VTK_UNSTRUCTURED_GRID:
                        anp = vtk_to_numpy(array)
                        print("piece 0, {} array {} with shape: {}".format(
                            attribute_type_names[attribute_type], i,
                            anp.shape))
                        dset = create_dataset(
                            array.GetName(), anp, field_data_group,
                            number_of_pieces)
                        all_field_datasets_size[attribute_type].append(
                            anp.shape[0])
                    else:
                        print("Error: Invalid dataset_type: {}".format(dataset_type))
                        dset = None
                    all_field_datasets[attribute_type].append(dset)

# ------------------------------------------------------------------------------
def append_data_arrays(data, dataset_type, piece, attribute_type_names,
                       all_field_datasets, all_field_datasets_size,
                       extent, whole_extent, all_ndims):
    """
    Write a data piece
    """
    for attribute_type, field_datasets in enumerate(
            all_field_datasets):
        # only for POINT and CELL arrays
        if attribute_type < 2:
            for i, field_dataset in enumerate(field_datasets):
                array = data.GetAttributesAsFieldData(
                    attribute_type).GetArray(i)
                if dataset_type == VTK_IMAGE_DATA:
                    ndim = all_ndims[attribute_type][i]
                    append_dataset_imagedata(
                        field_dataset, array,
                        extent, whole_extent, attribute_type, ndim)
                elif dataset_type == VTK_UNSTRUCTURED_GRID:
                    anp = vtk_to_numpy(array)
                    print("piece {} {} array {} with shape {}".format(
                        piece, attribute_type_names[attribute_type], i,
                        anp.shape))
                    all_field_datasets_size[
                        attribute_type][i] = append_dataset(
                            field_dataset, anp,
                            all_field_datasets_size[attribute_type][i])

# ------------------------------------------------------------------------------
def convert(input_path, output_file):
    input_file = os.path.basename(input_path)
    input_file_array = os.path.splitext(input_file)
    input_file_ext = input_file_array[1]

    (dataset_type, parallel, reader) = setup_reader(input_file_ext)
    reader.SetFileName(input_path)

    (number_of_pieces, data) = request_piece(reader, parallel, 0)
    with h5py.File(output_file, "w") as hdffile:
        # write support data
        whole_extent = None
        extent = None
        vtkhdf_group = hdffile.create_group("VTKHDF")
        vtkhdf_group.attrs.create("Version", [1, 0])
        (points, points_size, connectivity, connectivity_size,
         offset, offset_size, types, types_size,
         number_of_connectivity_ids, number_of_points,
         number_of_cells) = (None, None, None, None,
                             None, None, None, None,
                             None, None, None)
        if dataset_type == VTK_IMAGE_DATA:
            whole_extent = create_support_imagedata(
                reader, data, vtkhdf_group)
            extent = data.GetExtent()
        elif dataset_type == VTK_UNSTRUCTURED_GRID:
            (points, points_size, connectivity, connectivity_size,
             offset, offset_size, types, types_size,
             number_of_connectivity_ids, number_of_points,
             number_of_cells) = create_support_unstructuredgrid(
                 data, number_of_pieces, vtkhdf_group)
        else:
            print("Error: Invalid dataset_type: {}".format(dataset_type))
        # the same order as vtkDataObject::AttributeTypes: POINT, CELL
        attribute_type_names = ["PointData", "CellData", "FieldData"]
        # an HDF dataset for each attribute_type, for each VTK array
        all_field_datasets = [[] for _ in range(len(attribute_type_names))]
        # the size of that dataset (used only for unstructured grids)
        all_field_datasets_size = [
            [] for _ in range(len(attribute_type_names))]
        # the number of dimensions for an array (used only for image data)
        all_ndims = [[] for _ in range(len(attribute_type_names))]
        # create data piece 0
        print("Piece 0")
        create_data_arrays(
            data, dataset_type, vtkhdf_group,
            attribute_type_names, all_field_datasets, all_field_datasets_size,
            number_of_pieces,
            extent, whole_extent, all_ndims)
        # write the rest of the pieces
        for piece in range(1, number_of_pieces):
            data = request_piece(reader, parallel, piece)[1]
            if dataset_type == VTK_IMAGE_DATA:
                extent = data.GetExtent()
            elif dataset_type == VTK_UNSTRUCTURED_GRID:
                (points_size, connectivity_size,
                 offset_size, types_size) = append_support_unstructuredgrid(
                     piece, data,
                     points, points_size, connectivity, connectivity_size,
                     offset, offset_size, types, types_size,
                     number_of_connectivity_ids, number_of_points,
                     number_of_cells)
            print("Piece {}".format(piece))
            append_data_arrays(
                data, dataset_type, piece, attribute_type_names,
                all_field_datasets, all_field_datasets_size,
                extent, whole_extent, all_ndims)

# ------------------------------------------------------------------------------
def main(args):
    """
    Converts a VTK XML file to a VTK HDF file.
    """
    parser = argparse.ArgumentParser(
        description=("Read a vtx/pvtx file and convert it to a hdf "
                     "file where x is i or u"))
    parser.add_argument("input", help="Input XML VTK file.")
    parser.add_argument("--output", help="Output HDF VTK file.")
    args = parser.parse_args(args)

    if not os.path.exists(args.input):
        raise RuntimeError("File does not exits: {}".format(args.input))

    input_file = os.path.basename(args.input)
    input_file_array = os.path.splitext(input_file)
    input_file_noext = input_file_array[0]
    if args.output:
        output_file = args.output
    else:
        output_file = "{}.vtkhdf".format(input_file_noext)
    convert(args.input, output_file)


# ------------------------------------------------------------------------------
if __name__ == "__main__":
    main(sys.argv[1:])
