import h5py as h5


def write_headers(root: h5.Group):
    root.attrs["Version"] = (2, 3)
    root.attrs["Type"] = "UnstructuredGrid"


def generate_unstructured_grid(root: h5.Group):
    VTK_TETRA = 10
    VTK_TRIANGLE = 5
    cell_types = (
        VTK_TETRA,
        VTK_TRIANGLE,
    )
    root.create_dataset("Types", data=cell_types, dtype="uint8")
    root.create_dataset("NumberOfCells", data=(len(cell_types),), dtype="i8")

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

    tetra_connectivity = (0, 1, 2, 3)
    triangle_connectivity = (2, 4, 5)
    connectivity = tetra_connectivity + triangle_connectivity
    root.create_dataset(
        "NumberOfConnectivityIds", data=(len(connectivity),), dtype="i8"
    )
    root.create_dataset("Connectivity", data=connectivity, dtype="i8")

    offsets = (
        0,
        len(tetra_connectivity),
        len(tetra_connectivity + triangle_connectivity),
    )
    root.create_dataset("Offsets", data=offsets, dtype="i8")


if __name__ == "__main__":
    file = h5.File("step1.vtkhdf", "w")
    root = file.create_group("VTKHDF")
    write_headers(root)
    generate_unstructured_grid(root)
    file.close()
