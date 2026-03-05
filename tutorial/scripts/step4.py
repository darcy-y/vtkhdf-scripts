from math import cos
import typing
import h5py as h5


def append_dataset(dataset: h5.Dataset, array: typing.Tuple):
    """Resize a chunked dataset, adding `array` at the end"""
    original_size = dataset.shape[0]
    dataset.resize(original_size + len(array), axis=0)
    dataset[original_size:] = array


def write_headers(root: h5.Group):
    root.attrs["Version"] = (2, 3)
    root.attrs["Type"] = "UnstructuredGrid"


def initialize_unstructured_grid(root: h5.Group):
    root.create_dataset("NumberOfPoints", shape=(0,), maxshape=(None,), dtype="i8")
    root.create_dataset(
        "Points", shape=(0, 3), maxshape=(None, 3), dtype="f"
    )  # 3D points
    root.create_dataset("Types", shape=(0,), maxshape=(None,), dtype="uint8")
    root.create_dataset("NumberOfCells", shape=(0,), maxshape=(None,), dtype="i8")
    root.create_dataset(
        "NumberOfConnectivityIds", shape=(0,), maxshape=(None,), dtype="i8"
    )
    root.create_dataset("Connectivity", shape=(0,), maxshape=(None,), dtype="i8")
    root.create_dataset("Offsets", shape=(0,), maxshape=(None,), dtype="i8")


def initialize_steps_group(root: h5.Group):
    steps = root.create_group("Steps")
    steps.create_dataset(
        "Values", shape=(0,), maxshape=(None,), dtype="f"
    )  # time values

    steps.create_dataset("PartOffsets", shape=(0,), maxshape=(None,), dtype="i8")
    steps.create_dataset("NumberOfParts", shape=(0,), maxshape=(None,), dtype="i8")
    steps.create_dataset(
        "ConnectivityIdOffsets", shape=(0,), maxshape=(None,), dtype="i8"
    )
    steps.create_dataset("CellOffsets", shape=(0,), maxshape=(None,), dtype="i8")
    steps.create_dataset("PointOffsets", shape=(0,), maxshape=(None,), dtype="i8")

    pointDataOffsets = steps.create_group("PointDataOffsets")
    pointDataOffsets.create_dataset("Pressure", (0,), maxshape=(None,), dtype="i8")

    cellDataOffsets = steps.create_group("CellDataOffsets")
    cellDataOffsets.create_dataset("Velocity", (0,), maxshape=(None,), dtype="i8")

    fieldDataOffsets = steps.create_group("FieldDataOffsets")
    fieldDataOffsets.create_dataset("Temperature", (0,), maxshape=(None,), dtype="i8")


def initialize_fields(root: h5.Group):
    point_data = root.create_group("PointData")
    point_data.create_dataset("Pressure", (0,), maxshape=(None,), dtype="f")

    cell_data = root.create_group("CellData")
    cell_data.create_dataset("Velocity", (0, 3), maxshape=(None, 3), dtype="f")

    field_data = root.create_group("FieldData")
    field_data.create_dataset("Temperature", (0,), maxshape=(None,), dtype="f")


VTK_TETRA = 10
VTK_TRIANGLE = 5
points = (
    (0.0, 0.0, 0.0),
    (2.0, 0.0, 0.0),
    (1.0, 2.0, 0.0),
    (1.0, 0.0, 2.0),
    (2.0, 3.0, 0.0),
    (1.0, 4.0, 0.0),
)
tetra_connectivity = (0, 1, 2, 3)
triangle_connectivity = (2, 4, 5)
total_connectivity = tetra_connectivity + triangle_connectivity
cell_types = (VTK_TETRA, VTK_TRIANGLE)


def append_temporal_unstructured_grid(root: h5.Group, step: int):
    # Points: "grow" the mesh every time step
    append_dataset(root["NumberOfPoints"], (len(points),))
    factor = 1.2 * (step + 1)
    time_points = tuple((x * factor, y * factor, z * factor) for x, y, z in points)
    append_dataset(root["Points"], time_points)

    # Tetra + Triangle cells
    append_dataset(root["Types"], cell_types)
    append_dataset(root["NumberOfConnectivityIds"], (len(total_connectivity),))
    append_dataset(root["NumberOfCells"], (len(cell_types),))
    append_dataset(root["Connectivity"], total_connectivity)
    append_dataset(
        root["Offsets"],
        (0, len(tetra_connectivity), len(total_connectivity)),
    )


def append_temporal_cell_point_data(root: h5.Group, step: int):
    # Point_data
    pressure_field = (1.5, 1.2, 1.3, 1.4, 2.2, 0.4)
    factor = cos(step / 5) * 3
    pressure_values = tuple(pressure * factor for pressure in pressure_field)
    append_dataset(root["PointData/Pressure"], pressure_values)

    # cell data
    velocity_field = (
        (2.0, 1.1, 1.3),
        (1.4, 0.9, 1.5),
    )
    velocity_values = tuple(
        (x * factor, y * factor, z * factor) for x, y, z in velocity_field
    )
    append_dataset(
        root["CellData/Velocity"],
        velocity_values,
    )

    # field data
    temperature = 273 + step
    append_dataset(root["FieldData/Temperature"], (temperature,))


def append_steps_offsets(root: h5.Group, step: int):
    steps = root["Steps"]

    # Static mesh: use the same offsets from time step 0 for geometry datasets, so the geometry does not change between time steps
    append_dataset(steps["PartOffsets"], (0,))
    append_dataset(steps["NumberOfParts"], (1,))
    append_dataset(steps["PointOffsets"], (0,))
    append_dataset(steps["CellOffsets"], (0,))
    append_dataset(steps["ConnectivityIdOffsets"], (0,))

    append_dataset(
        steps["PointDataOffsets/Pressure"], (root["PointData/Pressure"].shape[0],)
    )
    append_dataset(
        steps["CellDataOffsets/Velocity"], (root["CellData/Velocity"].shape[0],)
    )
    append_dataset(
        steps["FieldDataOffsets/Temperature"], (root["FieldData/Temperature"].shape[0],)
    )


if __name__ == "__main__":
    file = h5.File("step4.vtkhdf", "w")
    root = file.create_group("VTKHDF")

    write_headers(root)

    # Initialize chunked datasets
    initialize_unstructured_grid(root)
    initialize_steps_group(root)
    initialize_fields(root)

    # Only append geometry once
    append_temporal_unstructured_grid(root, 0)

    # For each step, append values to datasets and to Steps group offsets
    nsteps = 10
    root["Steps"].attrs["NSteps"] = nsteps
    for step in range(nsteps):
        append_steps_offsets(root, step)
        append_dataset(root["Steps/Values"], (float(step * 0.1),))
        append_temporal_cell_point_data(root, step)

    file.close()
