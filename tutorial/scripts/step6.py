import h5py as h5


def write_headers(root: h5.Group):
    root.attrs["Version"] = (2, 3)
    root.attrs["Type"] = "PartitionedDataSetCollection"


def generate_composite(root: h5.Group):
    # Link to externally-stored VTKHDF meshes
    root["ImageBlock"] = h5.ExternalLink("step5.vtkhdf", "/VTKHDF")
    root["UnstructuredBlock"] = h5.ExternalLink("step2.vtkhdf", "/VTKHDF")

    # Give them a unique Index
    root["ImageBlock"].attrs["Index"] = 1
    root["UnstructuredBlock"].attrs["Index"] = 0

    # Create an assembly referencing top-level blocks
    assembly = root.create_group("Assembly", track_order=True)
    assembly["BlockName0"] = h5.SoftLink("/VTKHDF/ImageBlock")
    assembly_group = assembly.create_group("Group0", track_order=True)
    assembly_group["BlockName1"] = h5.SoftLink("/VTKHDF/ImageBlock")
    assembly_group["BlockName2"] = h5.SoftLink("/VTKHDF/UnstructuredBlock")


if __name__ == "__main__":
    file = h5.File("step6.vtkhdf", "w")
    root = file.create_group("VTKHDF", track_order=True)
    write_headers(root)
    generate_composite(root)
    file.close()
