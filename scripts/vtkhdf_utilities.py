from vtkmodules.vtkCommonCore import vtkDoubleArray, vtkPoints
from vtkmodules.vtkCommonDataModel import vtkPolyData, vtkUnstructuredGrid, vtkCellArray
from vtkmodules.vtkFiltersCore import vtkAppendFilter
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter
from vtkmodules.vtkFiltersSources import vtkSphereSource,vtkCellTypeSource
from vtkmodules.vtkIOXML import vtkXMLPolyDataWriter

import vtkmodules.numpy_interface.dataset_adapter as dsa
from vtkmodules.util.numpy_support import (numpy_to_vtk as npvtk, vtk_to_numpy as vtknp)

import numpy as np
import h5py as h5

# Global metadata
fType = 'f'
idType = 'i8'
connectivities = ['Vertices', 'Lines', 'Polygons', 'Strips']


# -----------------------------------------------------------------
def generate_geometry_structure(f):
    root = f
    root.attrs['Version'] = (2,0)
    ascii_type = 'PolyData'.encode('ascii')
    root.attrs.create('Type', ascii_type, dtype=h5.string_dtype('ascii', len(ascii_type))) 

    root.create_dataset('NumberOfPoints', (0,), maxshape=(None,), dtype=idType)
    root.create_dataset('Points', (0,3), maxshape=(None,3), dtype=fType)

    for connect in connectivities:
        group = root.create_group(connect)
        group.create_dataset('NumberOfConnectivityIds', (0,), maxshape=(None,), dtype=idType)
        group.create_dataset('NumberOfCells', (0,), maxshape=(None,), dtype=idType)
        group.create_dataset('Offsets', (0,), maxshape=(None,), dtype=idType)
        group.create_dataset('Connectivity', (0,), maxshape=(None,), dtype=idType)

    pData = root.create_group('PointData')
    pData.create_dataset('Warping', (0,3), maxshape=(None,3), dtype=fType)
    pData.create_dataset('Normals', (0,3), maxshape=(None,3), dtype=fType)

    cData = root.create_group('CellData')
    cData.create_dataset('Materials', (0,), maxshape=(None,), dtype=idType)

# -----------------------------------------------------------------
def generate_geometry_structure_unstructured(f):
    root = f
    root.attrs['Version'] = (2,0)
    ascii_type = 'UnstructuredGrid'.encode('ascii')
    root.attrs.create('Type', ascii_type, dtype=h5.string_dtype('ascii', len(ascii_type))) 

    root.create_dataset('NumberOfPoints', (0,), maxshape=(None,), dtype=idType)
    root.create_dataset('Types', (0,), maxshape=(None,), dtype=idType)
    root.create_dataset('Points', (0,3), maxshape=(None,3), dtype=fType)
    
    root.create_dataset('NumberOfConnectivityIds', (0,), maxshape=(None,), dtype=idType)
    root.create_dataset('NumberOfCells', (0,), maxshape=(None,), dtype=idType)
    root.create_dataset('Offsets', (0,), maxshape=(None,), dtype=idType)
    root.create_dataset('Connectivity', (0,), maxshape=(None,), dtype=idType)

    pData = root.create_group('PointData')
    pData.create_dataset('Polynomial', (0,1), maxshape=(None,1), dtype=fType)

# -----------------------------------------------------------------
def generate_step_structure(f):
    root = f
    steps = root.create_group('Steps')
    steps.attrs['NSteps'] = 0

    steps.create_dataset('Values', (0,), maxshape=(None,), dtype=fType)

    singleDSs = ['PartOffsets', 'NumberOfParts', 'PointOffsets']
    for name in singleDSs:
        steps.create_dataset(name, (0,), maxshape=(None,), dtype=idType)

    nTopoDSs = ['CellOffsets', 'ConnectivityIdOffsets']
    for name in nTopoDSs:
        steps.create_dataset(name, (0,4), maxshape=(None,4), dtype=idType)

    pData = steps.create_group('PointDataOffsets')
    pData.create_dataset('Warping', (0,), maxshape=(None,), dtype=idType)
    pData.create_dataset('Normals', (0,), maxshape=(None,), dtype=idType)

    cData = steps.create_group('CellDataOffsets')
    cData.create_dataset('Materials', (0,), maxshape=(None,), dtype=idType)

# -----------------------------------------------------------------
def append_data(f, poly_data, newStep=None, geometryOffset=None):

    root = f

    if not newStep == None:
        steps = root['Steps']
        steps.attrs['NSteps'] = steps.attrs['NSteps'] + 1
        append_dataset(steps['Values'], np.array([newStep]))

        geomOffs = []
        if geometryOffset == None:
            geomOffs.append(root['NumberOfPoints'].shape[0])
            geomOffs.append(1)
            geomOffs.append(root['Points'].shape[0])
            for connect in connectivities:
                geomOffs.append(root[connect + '/Offsets'].shape[0] - geomOffs[0])
            for connect in connectivities:
                geomOffs.append(root[connect + '/Connectivity'].shape[0])
        else:
            geomOffs.append(steps['PartOffsets'][geometryOffset])
            geomOffs.append(1)
            geomOffs.append(steps['PointOffsets'][geometryOffset])
            for iC in range(len(connectivities)):
                geomOffs.append(steps['CellOffsets'][geometryOffset, iC])
            for connect in connectivities:
                geomOffs.append(steps['ConnectivityIdOffsets'][geometryOffset, iC])

        append_dataset(steps['PartOffsets'], np.array([geomOffs[0]]))
        append_dataset(steps['NumberOfParts'], np.array([geomOffs[1]]))
        append_dataset(steps['PointOffsets'], np.array([geomOffs[2]]))
        append_dataset(steps['CellOffsets'], np.array(geomOffs[3:3+len(connectivities)]).reshape(1, len(connectivities)))
        append_dataset(steps['ConnectivityIdOffsets'], np.array(geomOffs[3+len(connectivities):3+2*len(connectivities)]).reshape(1, len(connectivities)))

        append_dataset(steps['PointDataOffsets/Warping'], np.array([root['PointData/Warping'].shape[0]]))
        append_dataset(steps['PointDataOffsets/Normals'], np.array([root['PointData/Normals'].shape[0]]))
        append_dataset(steps['CellDataOffsets/Materials'], np.array([root['CellData/Materials'].shape[0]]))
    # TODO Lucas: check it later
    # else:
    #     print("apply step?")
    #     # steps = root['Steps']
    #     # steps['NumberOfParts'][-1] += 1


    if geometryOffset == None:
        append_dataset(root['NumberOfPoints'], np.array([poly_data.GetNumberOfPoints()]))
        append_dataset(root['Points'], poly_data.Points)

        cellArrays = [poly_data.GetVerts(), poly_data.GetLines(), poly_data.GetPolys(), poly_data.GetStrips()]
        for name, connect in zip(connectivities, cellArrays):
            ca = vtknp(connect.GetConnectivityArray())
            append_dataset(root[name]['NumberOfConnectivityIds'], np.array([ca.shape[0]]))
            append_dataset(root[name]['Connectivity'], ca)
            oa = vtknp(connect.GetOffsetsArray())
            append_dataset(root[name]['NumberOfCells'], np.array([oa.shape[0]-1]))
            append_dataset(root[name]['Offsets'], oa)

    append_dataset(root['PointData']['Warping'], poly_data.PointData['Warping'])
    append_dataset(root['PointData']['Normals'], poly_data.PointData['Normals'])
    append_dataset(root['CellData']['Materials'], poly_data.CellData['Materials'])

# -----------------------------------------------------------------
def append_ug(root, complete, newStep=None, geometryOffset=None):

    poly_data = complete[0]
    poly_data_unwrapped = complete[1]

    append_dataset(root['NumberOfPoints'], np.array([poly_data.GetNumberOfPoints()]))
    append_dataset(root['Points'], poly_data.Points)

    ca = vtknp(poly_data_unwrapped.GetCells().GetConnectivityArray())
    print(ca)
    print(type(ca))
    append_dataset(root['NumberOfConnectivityIds'], np.array([ca.shape[0]]))
    append_dataset(root['Connectivity'], ca)
    oa = vtknp(poly_data_unwrapped.GetCells().GetOffsetsArray())
    append_dataset(root['NumberOfCells'], np.array([oa.shape[0]-1]))
    append_dataset(root['Offsets'], oa)

    # append_dataset(root['PointData']['Polynomial'], poly_data.PointData['Polynomial'])

# -----------------------------------------------------------------
def append_dataset(dset, array):
    origLen = dset.shape[0]
    dset.resize(origLen + array.shape[0], axis=0)
    dset[origLen:] = array

def generate_unstructured_grid():
    ugSource = vtkCellTypeSource()
    ugSource.Update()
    ug = dsa.WrapDataObject(ugSource.GetOutput())

    return [ug,ugSource.GetOutput()]

# -----------------------------------------------------------------
def generate_static_spheres(center, resolution):
    sphereSrc0 = vtkSphereSource()
    sphereSrc0.Update()
    sphere0 = dsa.WrapDataObject(sphereSrc0.GetOutput())

    sphereSrc1 = vtkSphereSource()
    sphereSrc1.SetCenter(center)
    sphereSrc1.SetThetaResolution(resolution)
    sphereSrc1.SetPhiResolution(resolution)
    sphereSrc1.Update()
    sphere1 = dsa.WrapDataObject(sphereSrc1.GetOutput())

    warping0 = npvtk(np.cross(sphere0.Points, [0, 0, 1]).astype(fType))
    warping0.SetName('Warping')
    sphere0.GetPointData().AddArray(warping0)
    warping1 = npvtk(np.cross(sphere1.Points - [2, 2, 2], [0, 0, 1]).astype(fType))
    warping1.SetName('Warping')
    sphere1.GetPointData().AddArray(warping1)

    mats0 = npvtk(np.full((sphere0.GetNumberOfCells(),), 0, dtype=idType))
    mats0.SetName('Materials')
    sphere0.GetCellData().AddArray(mats0)
    mats1 = npvtk(np.full((sphere1.GetNumberOfCells(),), 1, dtype=idType))
    mats1.SetName('Materials')
    sphere1.GetCellData().AddArray(mats1)

    return [sphere0]

# -----------------------------------------------------------------
def generate_morphing_spheres(t, morphGeometry=False):
    pds = generate_static_spheres()

    for pd in pds:
        mod = (np.sin(pd.Points[:, 0]) + np.sin(pd.Points[:,1])+1)*np.cos(np.pi*t)/2.0
        if morphGeometry:
            pd.Points = pd.Points * mod
        warped = npvtk(pd.PointData['Warping'] * mod)
        warped.SetName('Warping')
        pd.GetPointData().AddArray(warped)

    return pds

# -----------------------------------------------------------------
def write_vtp(filepath, pds):
    appender = vtkAppendFilter()
    for iPD, pd in enumerate(pds):
        appender.AddInputData(pd.VTKObject)
    appender.Update()
    surface = vtkGeometryFilter()
    surface.SetInputConnection(appender.GetOutputPort())
    surface.Update()
    writer = vtkXMLPolyDataWriter()
    writer.SetFileName(filepath)
    writer.SetInputConnection(surface.GetOutputPort())
    writer.Update()
