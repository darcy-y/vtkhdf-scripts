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

    return root


def add_field_data(root: h5.Group):
    point_data = root.create_group("PointData")
    pressure_field = (1.5, 1.2, 1.3, 1.4, 2.2, 0.4)
    point_data.create_dataset("Pressure", data=(pressure_field), dtype="f")

    velocity_field = (
        (2.0, 1.1, 1.3),
        (1.4, 0.9, 1.5),
    )
    cell_data = root.create_group("CellData")
    cell_data.create_dataset("Velocity", data=(velocity_field), dtype="f")

    field_data = root.create_group("FieldData")
    field_data.create_dataset("Temperature", data=(273,), dtype="i8")


if __name__ == "__main__":
    file = h5.File("step2.vtkhdf", "w")
    root = file.create_group("VTKHDF")
    write_headers(root)
    generate_unstructured_grid(root)
    add_field_data(root)
    file.close()
