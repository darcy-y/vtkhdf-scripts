import numpy as np
import h5py as h5

# -----------------------------------------------------------------
# Global metadata
fType = "f"
idType = "i8"
charType = "uint8"

VTK_POLYHEDRON = 42
VTK_HEXAHEDRON = 12

# -----------------------------------------------------------------
# Convenient method to fill h5py node with a numpy array
def append_dataset(dset, array):
    origLen = dset.shape[0]
    dset.resize(origLen + array.shape[0], axis=0)
    dset[origLen:] = array


# -----------------------------------------------------------------
# Generate a UnstructuredGrid VTKHDF polyhedron structure based on the spec
def generate_structure_for_unstructured(root):
    root.attrs["Version"] = (2, 5)
    ascii_type = "UnstructuredGrid".encode("ascii")
    root.attrs.create(
        "Type", ascii_type, dtype=h5.string_dtype("ascii", len(ascii_type))
    )

    root.create_dataset("NumberOfPoints", (0,), maxshape=(None,), dtype=idType)
    root.create_dataset("Types", (0,), maxshape=(None,), dtype=charType)
    root.create_dataset("Points", (0, 3), maxshape=(None, 3), dtype=fType)

    root.create_dataset("NumberOfConnectivityIds", (0,), maxshape=(None,), dtype=idType)
    root.create_dataset("NumberOfCells", (0,), maxshape=(None,), dtype=idType)
    root.create_dataset("Offsets", (0,), maxshape=(None,), dtype=idType)
    root.create_dataset("Connectivity", (0,), maxshape=(None,), dtype=idType)

    root.create_dataset("NumberOfFaces", (0,), maxshape=(None,), dtype=idType)
    root.create_dataset(
        "NumberOfFaceConnectivityIds", (0,), maxshape=(None,), dtype=idType
    )
    root.create_dataset(
        "NumberOfPolyhedronToFaceIds", (0,), maxshape=(None,), dtype=idType
    )

    root.create_dataset("FaceConnectivity", (0,), maxshape=(None,), dtype=idType)
    root.create_dataset("FaceOffsets", (0,), maxshape=(None,), dtype=idType)
    root.create_dataset("PolyhedronOffsets", (0,), maxshape=(None,), dtype=idType)
    root.create_dataset("PolyhedronToFaces", (0,), maxshape=(None,), dtype=idType)


# -----------------------------------------------------------------
def fill_with_hexahedron(root):
    points = np.array(
        [
            # Hexahedron defined as polyhedron
            [-1, -1, -1],
            [1, -1, -1],
            [1, 1, -1],
            [-1, 1, -1],
            [-1, -1, 1],
            [1, -1, 1],
            [1, 1, 1],
            [-1, 1, 1],

            # Real hexahedron
            [2, -1, -1],
            [4, -1, -1],
            [4, 1, -1],
            [2, 1, -1],
            [2, -1, 1],
            [4, -1, 1],
            [4, 1, 1],
            [2, 1, 1],
        ]
    )

    # Each tetra is connected to 8 points
    connectivity = np.array([0, 1, 2, 3, 4, 5, 6, 7,
                             8, 9, 10, 11, 12, 13, 14, 15])
    
    # Read connectivities at indices 0 and 8, add the next unread value (16)
    offsets = np.array([0, 8, 16])
    types = np.array([VTK_POLYHEDRON, VTK_HEXAHEDRON])
    # 6 faces of 4 points, plus the last value
    faceoffsets = np.array([0, 4, 8, 12, 16, 20, 24])
    faces = np.array(
        [0, 3, 2, 1, 0,
         4, 7, 3, 4, 5,
         6, 7, 5, 1, 2,
         6, 0, 1, 5, 4,
         2, 3, 7, 6]
    )

    # Use all 6 faces described above
    polyhedron_to_faces = np.array([0, 1, 2, 3, 4, 5])
    polyhedron_to_faces_offsets = np.array([0, 6, 6])

    append_dataset(root["NumberOfPoints"], np.array([len(points)]))
    append_dataset(root["Points"], points)
    append_dataset(root["NumberOfConnectivityIds"], np.array([len(connectivity)]))
    append_dataset(root["Connectivity"], connectivity)
    append_dataset(root["NumberOfCells"], np.array([len(offsets)-1]))
    append_dataset(root["Offsets"], offsets)
    append_dataset(root["Types"], types)

    append_dataset(root["NumberOfFaces"], np.array([6]))
    append_dataset(root["NumberOfPolyhedronToFaceIds"], np.array([6]))
    append_dataset(root["NumberOfFaceConnectivityIds"], np.array([len(faces)]))

    append_dataset(root["FaceConnectivity"], faces)
    append_dataset(root["FaceOffsets"], faceoffsets)
    append_dataset(root["PolyhedronToFaces"], polyhedron_to_faces)
    append_dataset(root["PolyhedronOffsets"], polyhedron_to_faces_offsets)

# -----------------------------------------------------------------
def fill_with_temporal_poly(root):
    points = np.array(
        [
            # T=0, Hexa
            [-1, -1, -1],
            [1, -1, -1],
            [1, 1, -1],
            [-1, 1, -1],
            [-1, -1, 1],
            [1, -1, 1],
            [1, 1, 1],
            [-1, 1, 1],

            # T=1, Tetra
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0.5, 0.5, 1],
        ]
    )
    connectivity = np.array([0, 1, 2, 3, 4, 5, 6, 7,
                            0, 1, 2, 3])
    offsets = np.array([0, 8,
                        0, 4])
    types = np.array([VTK_POLYHEDRON,
                      VTK_POLYHEDRON])
    faceoffsets = np.array([0, 4, 8, 12, 16, 20, 24, # Hexa
                            0, 3, 6, 9, 12]) # Tetra
    faces = np.array(
        [0, 3, 2, 1,
         0, 4, 7, 3,
         4, 5, 6, 7,
         5, 1, 2, 6,
         0, 1, 5, 4,
         2, 3, 7, 6, # Hexa
         0, 1, 2,
         1,2, 3,
         0, 1, 3,
         0, 2, 3] # Tetra
    )
    polyhedron_to_faces = np.array([0, 1, 2, 3, 4, 5, # Hexa
                                     0, 1, 2, 3])    # Tetra
    polyhedron_to_faces_offsets = np.array([0, 6, # Hexa
                                            0, 4]) # Tetra

    append_dataset(root["NumberOfPoints"], np.array([8,
                                                     4]))
    append_dataset(root["Points"], points)
    append_dataset(root["NumberOfConnectivityIds"], np.array([8, 4]))
    append_dataset(root["Connectivity"], connectivity)
    append_dataset(root["NumberOfCells"], np.array([1, 1]))
    append_dataset(root["Offsets"], offsets)
    append_dataset(root["Types"], types)

    append_dataset(root["NumberOfFaces"], np.array([6, 4]))
    append_dataset(root["NumberOfPolyhedronToFaceIds"], np.array([6, 4]))
    append_dataset(root["NumberOfFaceConnectivityIds"], np.array([24, 12]))

    append_dataset(root["FaceConnectivity"], faces)
    append_dataset(root["FaceOffsets"], faceoffsets)
    append_dataset(root["PolyhedronToFaces"], polyhedron_to_faces)
    append_dataset(root["PolyhedronOffsets"], polyhedron_to_faces_offsets)

    # Temporal information
    steps = root.create_group("Steps")
    steps.attrs["NSteps"] = 2
    steps["PointOffsets"] = [0, 8]
    steps["CellOffsets"] = [0, 1]
    steps["ConnectivityIdOffsets"] = [0, 8]
    steps["PartOffsets"] = [0, 1]
    steps["Values"] = [0.0, 1.0]

    # Polyhedron-specific
    steps["FaceConnectivityOffsets"] = [0, 24]
    steps["PolyhedronToFaceIdOffsets"] = [0, 6]
    steps["FaceOffsetsOffsets"] = [0, 6]


# -----------------------------------------------------------------
def fill_with_complex_poly(root):
    points = np.array(
        [
            [-0.57735, -0.57735, -0.57735],
            [-0.707107, -0.707107, -5.55112e-17],
            [-1, -6.63324e-17, -6.63324e-17],
            [-0.707107, -5.55112e-17, -0.707107],
            [-0.707107, 0.707107, -5.55112e-17],
            [-0.57735, 0.57735, -0.57735],
            [-0.57735, -0.57735, 0.57735],
            [-0.707107, -5.55112e-17, 0.707107],
            [-0.57735, 0.57735, 0.57735],
            [0.57735, -0.57735, -0.57735],
            [0.707107, -5.55112e-17, -0.707107],
            [1, -6.63324e-17, -6.63324e-17],
            [0.707107, -0.707107, -5.55112e-17],
            [0.57735, 0.57735, -0.57735],
            [0.707107, 0.707107, -5.55112e-17],
            [0.707107, -5.55112e-17, 0.707107],
            [0.57735, -0.57735, 0.57735],
            [0.57735, 0.57735, 0.57735],
            [-5.55112e-17, -0.707107, -0.707107],
            [-6.63324e-17, -1, -6.63324e-17],
            [-5.55112e-17, -0.707107, 0.707107],
            [6.63324e-17, 1, -6.63324e-17],
            [5.55112e-17, 0.707107, -0.707107],
            [5.55112e-17, 0.707107, 0.707107],
            [0, -6.63324e-17, -1],
            [0, -6.63324e-17, 1],
        ]
    )
    connectivity = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25])
    offsets = np.array([0, 26])
    types = np.array([VTK_POLYHEDRON])
    faceoffsets = np.array([0,4,8,12,16,20,24,28,32,36,40,44,48,52,56,60,64,68,72,76,80,84,88,92,96])
    faces = np.array([0,1,2,3,3,2,4,5,1,6,7,2,2,7,8,4,9,10,11,12,10,13,14,11,12,11,15,16,11,14,17,15,0,18,19,1,1,19,20,6,18,9,12,19,19,12,16,20,5,4,21,22,4,8,23,21,22,21,14,13,21,23,17,14,0,3,24,18,3,5,22,24,18,24,10,9,24,22,13,10,6,20,25,7,7,25,23,8,20,16,15,25,25,15,17,23])
    polyhedron_to_faces_offsets = np.array([0, 24])
    polyhedron_to_faces = np.array([i for i in range(24)])

    append_dataset(root["NumberOfPoints"], np.array([len(points)]))
    append_dataset(root["Points"], points)
    append_dataset(root["NumberOfConnectivityIds"], np.array([len(connectivity)]))
    append_dataset(root["Connectivity"], connectivity)
    append_dataset(root["NumberOfCells"], np.array([1]))
    append_dataset(root["Offsets"], offsets)
    append_dataset(root["Types"], types)

    append_dataset(root["NumberOfFaces"], np.array([24]))
    append_dataset(root["NumberOfPolyhedronToFaceIds"], np.array([24]))
    append_dataset(root["NumberOfFaceConnectivityIds"], np.array([len(faces)]))

    append_dataset(root["FaceConnectivity"], faces)
    append_dataset(root["FaceOffsets"], faceoffsets)
    append_dataset(root["PolyhedronToFaces"], polyhedron_to_faces)
    append_dataset(root["PolyhedronOffsets"], polyhedron_to_faces_offsets)


# -----------------------------------------------------------------
def generate_double_hexa(root):
    generate_structure_for_unstructured(root)
    fill_with_hexahedron(root)


# -----------------------------------------------------------------
def generate_poly(root):
    generate_structure_for_unstructured(root)
    fill_with_complex_poly(root)

def generate_temporal_poly(root):
    generate_structure_for_unstructured(root)
    fill_with_temporal_poly(root)

# -----------------------------------------------------------------
def generate_unstructured_grid(name):
    f = h5.File("hexahedron.vtkhdf", "w")
    root = f.create_group(name)
    generate_double_hexa(root)

    f2 = h5.File("polyhedron.vtkhdf", "w")
    root2 = f2.create_group(name)
    generate_poly(root2)

    f3 = h5.File("polyhedron_temporal.vtkhdf", "w")
    root3 = f3.create_group(name)
    generate_temporal_poly(root3)


# -----------------------------------------------------------------
if __name__ == "__main__":
    generate_unstructured_grid("VTKHDF")
