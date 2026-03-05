import h5py as h5


def write_headers(root: h5.Group):
    root.attrs["Version"] = (2, 3)
    root.attrs["Type"] = "ImageData"


def generate_image_data(root: h5.Group):
    root.attrs.create("WholeExtent", (0.0, 2.0, 0, 2.0, 0.0, 2.0), dtype="f")
    root.attrs.create("Origin", (0.0, 0.0, 0.0), dtype="f")
    root.attrs.create("Spacing", (1.0, 1.0, 1.0), dtype="f")
    root.attrs.create("Direction", (1, 0, 0, 0, 1, 0, 0, 0, 1), dtype="f")

    # 2x2x2 cells, cell array needs to have shape (2,2,2)
    cell_data = root.create_group("CellData")
    cell_data.create_dataset(
        "ID",
        data=(
            ((1, 2), (3, 4)),
            ((5, 6), (7, 8)),
        ),
        dtype="f",
    )

    # 3x3x3 points, point array needs to be (3,3,3)
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


if __name__ == "__main__":
    file = h5.File("step5.vtkhdf", "w")
    root = file.create_group("VTKHDF")
    write_headers(root)
    generate_image_data(root)
    file.close()
