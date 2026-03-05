import sys
from typing import Iterable
import numpy as np
import h5py as h5

from vtkmodules.vtkFiltersSources import vtkRandomHyperTreeGridSource, vtkHyperTreeGridSource
from vtkmodules.vtkIOXML import vtkXMLHyperTreeGridWriter
import xml.etree.ElementTree as ET


"""
This file provides utilities that create VTKHDF files describing HyperTreeGrid structures
from the XML HTG representation to write VTKHDF files that match them nearly 1:1.

The script can produce simple, multi-piece and transient data to give the vtkHDFReader for testing purposes.
Requires VTK 9.4 (uses the modern VTK Python wrapping)
"""

fType = "f8"
idType = "i8"
charType = "u1"

XML_TO_HDF_TYPE = {
    "Float64": "f8",
    "Float32": "f4",
    "UInt8": "u1",
    "UInt32": "u4",
    "UInt64": "u8",
    "Int32": "i4",
    "Int64": "i4"
}

# -----------------------------------------------------------------
def append_dataset(dset: h5.Dataset, array, offset=False) -> None:
    """Append data to an existing h5py dataset"""
    origLen = dset.shape[0]
    dset.resize(origLen + len(array), axis=0)

    if offset: # Only add one value, that is offsetted from the previous one
        dset[origLen] = (dset[origLen-1] + array[0],)
    else:
        dset[origLen:] = array

def create_structure(xml_root: ET.Element, hdf_root: h5.Group) -> None:
    """Create the VTKHDF HTG file structure from an XML file"""

    hdf_root.attrs["Version"] = (2, 4)
    ascii_type = "HyperTreeGrid".encode("ascii")
    hdf_root.attrs.create("Type", ascii_type, dtype=h5.string_dtype("ascii", len(ascii_type)))

    hdf_root.attrs.create("Dimensions", data=tuple(map(int,xml_root[0].attrib["Dimensions"].split())))
    hdf_root.attrs.create("BranchFactor", data=(int(xml_root[0].attrib["BranchFactor"]),))
    
    hdf_root.attrs.create("TransposedRootIndexing", data=(int(xml_root[0].attrib["TransposedRootIndexing"]),), dtype=idType)
    
    if "InterfaceNormalsName" in xml_root[0].attrib:
        ascii_interface = xml_root[0].attrib["InterfaceNormalsName"].encode("ascii")
        hdf_root.attrs.create("InterfaceNormalsName", ascii_interface, dtype=h5.string_dtype("ascii", len(ascii_interface)))
    
    if "InterfaceInterceptsName" in xml_root[0].attrib:
        ascii_interface = xml_root[0].attrib["InterfaceInterceptsName"].encode("ascii")
        hdf_root.attrs.create("InterfaceInterceptsName", ascii_interface, dtype=h5.string_dtype("ascii", len(ascii_interface)))

    
    hdf_root.create_dataset("XCoordinates", (0,), maxshape=(None,), dtype=fType)
    hdf_root.create_dataset("YCoordinates", (0,), maxshape=(None,), dtype=fType)
    hdf_root.create_dataset("ZCoordinates", (0,), maxshape=(None,), dtype=fType)

    hdf_root.create_dataset("Descriptors", (0,), maxshape=(None,), dtype=charType)
    hdf_root.create_dataset("DescriptorsSize", (0,), maxshape=(None,), dtype=idType)
    hdf_root.create_dataset("NumberOfCellsPerTreeDepth", (0,), maxshape=(None,), dtype=idType)
    hdf_root.create_dataset("TreeIds", (0,), maxshape=(None,), dtype=idType)
    hdf_root.create_dataset("DepthPerTree", (0,), maxshape=(None,), dtype=idType)
    hdf_root.create_dataset("NumberOfTrees", (0,), maxshape=(None,), dtype=idType)
    hdf_root.create_dataset("NumberOfDepths", (0,), maxshape=(None,), dtype=idType)
    hdf_root.create_dataset("NumberOfCells", (0,), maxshape=(None,), dtype=idType)

    hdf_root.create_dataset("Mask", (0,), maxshape=(None,), dtype=charType)

    cData = hdf_root.create_group('CellData')
    for array in xml_root[0][2]:
        ncomp = 1
        if 'NumberOfComponents' in array.attrib:
            ncomp = int(array.attrib['NumberOfComponents'])
            cData.create_dataset(array.attrib["Name"], (0,ncomp), maxshape=(None,ncomp), dtype=XML_TO_HDF_TYPE[array.attrib["type"]])
        else:
            cData.create_dataset(array.attrib["Name"], (0,), maxshape=(None,), dtype=XML_TO_HDF_TYPE[array.attrib["type"]])



def create_steps_structure(xml_root: ET.Element, hdf_root: h5.Group, nsteps: int):
    """Create VTKHDF steps group structure for temporal datasets"""

    steps = hdf_root.create_group("Steps")
    steps.attrs.create("NSteps", data=nsteps, dtype=idType)
    steps.create_dataset("Values", (1,), data=(0,), maxshape=(None,), dtype=fType)

    steps.create_dataset("PartOffsets", (1,), data=(0,), maxshape=(None,), dtype=idType)
    steps.create_dataset("TreeIdsOffsets", (1,), data=(0,), maxshape=(None,), dtype=idType)
    steps.create_dataset("DepthPerTreeOffsets", (1,), data=(0,), maxshape=(None,), dtype=idType)
    steps.create_dataset("NumberOfCellsPerTreeDepthOffsets", (1,), data=(0,), maxshape=(None,), dtype=idType)

    steps.create_dataset("DescriptorsOffsets", (1,), data=(0,), maxshape=(None,), dtype=idType)
    steps.create_dataset("MaskOffsets", (1,), data=(0,), maxshape=(None,), dtype=idType)

    steps.create_dataset("XCoordinatesOffsets", (1,), data=(0,), maxshape=(None,), dtype=idType)
    steps.create_dataset("YCoordinatesOffsets", (1,), data=(0,), maxshape=(None,), dtype=idType)
    steps.create_dataset("ZCoordinatesOffsets", (1,), data=(0,), maxshape=(None,), dtype=idType)

    cd_offsets = steps.create_group("CellDataOffsets")
    for array in xml_root[0][2]:
        cd_offsets.create_dataset(array.attrib["Name"], (1,), data=(0,), maxshape=(None,), dtype=idType)

# -----------------------------------------------------------------
def unformatted_nums_to_list(text: str, type=int) -> None:
    """Turn VTK XML ASCII array into a int array"""
    if type == int:
        return tuple(map(int," ".join(l.strip() for l in text.strip().split("\n")).split())) 
    else:
        return tuple(map(float," ".join(l.strip() for l in text.strip().split("\n")).split())) 

# -----------------------------------------------------------------
def append_data_from_xml(xml_root: ET.Element, hdf_root: h5.Group, temporal: bool = False, step: int=0) -> None:
    """Append data from HTG XML root to VTKHDF HTG root"""

    # Coordinates of the grid cells
    # Assume static coordinates
    if step == 0:
        append_dataset(hdf_root["XCoordinates"], tuple(map(float, xml_root[0][0][0].text.strip().split(" "))))
        append_dataset(hdf_root["YCoordinates"], tuple(map(float, xml_root[0][0][1].text.strip().split(" "))))
        append_dataset(hdf_root["ZCoordinates"], tuple(map(float, xml_root[0][0][2].text.strip().split(" "))))

    nb_verts_per_tree_depth = unformatted_nums_to_list(xml_root[0][1][1].text)
    append_dataset(hdf_root["NumberOfCellsPerTreeDepth"], nb_verts_per_tree_depth)
    append_dataset(hdf_root["NumberOfDepths"], (len(nb_verts_per_tree_depth),))
    depth_per_tree = unformatted_nums_to_list(xml_root[0][1][3].text)
    append_dataset(hdf_root["DepthPerTree"], depth_per_tree)

    treeids = unformatted_nums_to_list(xml_root[0][1][2].text)
    if step == 0:
        append_dataset(hdf_root["TreeIds"],  treeids)
    append_dataset(hdf_root["NumberOfTrees"], (len(treeids),))

    
    mask = unformatted_nums_to_list(xml_root[0][1][4].text)
    packed_mask = np.packbits(mask)
    append_dataset(hdf_root["Mask"], packed_mask)
    append_dataset(hdf_root["NumberOfCells"], (len(mask),))

    descriptor = unformatted_nums_to_list(xml_root[0][1][0].text)
    packed_descriptor = []
    if (descriptor):
        packed_descriptor = np.packbits(descriptor)
        append_dataset(hdf_root["Descriptors"], packed_descriptor)
    append_dataset(hdf_root["DescriptorsSize"], (len(descriptor),))

    # Cell data
    for xml_array in xml_root[0][2]:
        type = int
        if "Float" in xml_array.attrib["type"]:
            type= float
        hdf_array = unformatted_nums_to_list(xml_array.text, type)
        ncomp = 1
        if 'NumberOfComponents' in xml_array.attrib:
            ncomp = int(xml_array.attrib['NumberOfComponents'])
            hdf_2D_array = [hdf_array[ncomp*i:ncomp*(i+1)] for i in range(int(len(hdf_array)/ncomp))]
            append_dataset(hdf_root[f"CellData/{xml_array.attrib['Name']}"], hdf_2D_array)
        else:
            append_dataset(hdf_root[f"CellData/{xml_array.attrib['Name']}"], hdf_array)


    # Temporal offset data
    if temporal:
        stepg = hdf_root["Steps"]
        append_dataset(stepg["Values"], (round((step+1)*0.1,1),))
        append_dataset(stepg["PartOffsets"], (hdf_root["NumberOfTrees"].shape[0],))
        append_dataset(stepg["TreeIdsOffsets"], (0,)) # Static
        append_dataset(stepg["DepthPerTreeOffsets"], (hdf_root["TreeIds"].shape[0],), True) # Offset, because static
        append_dataset(stepg["NumberOfCellsPerTreeDepthOffsets"], (hdf_root["NumberOfCellsPerTreeDepth"].shape[0],))
        append_dataset(stepg["DescriptorsOffsets"], (hdf_root["Descriptors"].shape[0],))
        append_dataset(stepg["MaskOffsets"], (hdf_root["Mask"].shape[0],))
        append_dataset(stepg["XCoordinatesOffsets"], (0,))
        append_dataset(stepg["YCoordinatesOffsets"], (0,))
        append_dataset(stepg["ZCoordinatesOffsets"], (0,))

        for array in xml_root[0][2]:
            name = array.attrib['Name']
            append_dataset(stepg[f"CellDataOffsets/{name}"], (hdf_root[f"CellData/{name}"].shape[0],))



# -----------------------------------------------------------------
def generate_htg_from_xml(name: str) -> None:
    """Generate HDF file from Random HTG, written as VTK XML."""

    source = vtkRandomHyperTreeGridSource(dimensions=(3,3,3), seed=123, split_fraction=0.75,masked_fraction=0.25)
    writer = vtkXMLHyperTreeGridWriter(input_connection=source.output_port)
    writer.SetDataModeToAscii()
    writer.SetFileName(f"{name}.htg")
    writer.Write()

    tree = ET.parse(f"{name}.htg")
    xml_root = tree.getroot()

    f = h5.File("randomhtg.vtkhdf", "w")
    hdf_root = f.create_group("VTKHDF")

    create_structure(xml_root, hdf_root)
    append_data_from_xml(xml_root, hdf_root)

# -----------------------------------------------------------------
def generate_temporal_htg(name: str) -> None:
    """Generate a temporal HyperTree VTKHDF file, from HTG Source using descriptors"""
    descriptors = (
        "....",
        ".R.. | ....",
        "RR.. | .... ....",
        "RR.. | .... ....", # Static tree
        "RRRR | .... R... .... .... | ...."
    )

    f = h5.File(f"{name}.vtkhdf", "w")
    hdf_root = f.create_group("VTKHDF")

    source = vtkHyperTreeGridSource(branch_factor=2,max_depth=3,dimensions=(3,3,1))
    writer = vtkXMLHyperTreeGridWriter(input_connection=source.output_port)
    writer.SetDataModeToAscii()
    for step, descr in enumerate(descriptors):
        filename = f"{name}_{step}.htg"
        source.SetDescriptor(descr)
        source.Update()
        writer.SetFileName(filename)
        writer.Write()

        tree = ET.parse(filename)
        xml_root = tree.getroot()

        if step == 0:
            create_structure(xml_root, hdf_root)
            create_steps_structure(xml_root, hdf_root, len(descriptors))

        temporal = step != len(descriptors) -1
        append_data_from_xml(xml_root, hdf_root, temporal=temporal, step=step)

def generate_multipiece_htg(name: str) -> None:
    """Generate a temporal HyperTree VTKHDF file, from HTG Source using descriptors"""
    descriptors = (
        "... .R. ... ... ... | ....",
        "... ... ... .R. ... | ....",
    )

    masks = (
        "111 111 111 000 000 | 1111",
        "000 000 000 111 111 | 1111"
    )

    f = h5.File(f"{name}.vtkhdf", "w")
    hdf_root = f.create_group("VTKHDF")


    source = vtkHyperTreeGridSource(branch_factor=2,max_depth=2,dimensions=(6,4,1))
    writer = vtkXMLHyperTreeGridWriter(input_connection=source.output_port)
    writer.SetDataModeToAscii()

    for piece, descr in enumerate(descriptors):
        filename = f"{name}_{piece}.htg"
        source.SetDescriptor(descr)
        source.SetMask(masks[piece])
        source.UseMaskOn()
        source.Update()

        writer.SetFileName(filename)
        writer.Write()

        tree = ET.parse(filename)
        xml_root = tree.getroot()

        if piece == 0:
            create_structure(xml_root, hdf_root)

        append_data_from_xml(xml_root, hdf_root)

def generate_multipiece_temporal_htg(name: str) -> None:
    """Generate a temporal HyperTree VTKHDF file, from HTG Source using descriptors"""
    descriptors = (
        "... .R. ... ... ... | ....",
        "... ... ... .R. ... | ....",
        "... RRR ... ... ... | .... ...R .... | ....",
        "... ... ... .RR ... | .... ....",
    )

    masks = (
        "111 111 111 000 000 | 1111",
        "000 000 000 111 111 | 1111",
        "111 111 111 000 000 | 1111 1111 1111 | 1111",
        "000 000 000 111 111 | 1111 1111"
    )

    f = h5.File(f"{name}.vtkhdf", "w")
    hdf_root = f.create_group("VTKHDF")

    source = vtkHyperTreeGridSource(branch_factor=2,max_depth=3,dimensions=(6,4,1))
    writer = vtkXMLHyperTreeGridWriter(input_connection=source.output_port)
    writer.SetDataModeToAscii()

    for step in range(2):
        for piece in range(2):
            filename = f"{name}_{step}_{piece}.htg"
            source.SetDescriptor(descriptors[step * 2 + piece])
            source.SetMask(masks[step * 2 + piece])
            source.UseMaskOn()
            source.Update()

            writer.SetFileName(filename)
            writer.Write()

            tree = ET.parse(filename)
            xml_root = tree.getroot()

            if piece == 0 and step == 0:
                create_structure(xml_root, hdf_root)
                create_steps_structure(xml_root, hdf_root, 2)


            temporal = step == 0 and piece == 1
            append_data_from_xml(xml_root, hdf_root, temporal=temporal, step=step)

def generate_shell3D_interfaces(shell_path: str, name: str) -> None:
    """Generate HTG with interfaces"""
    f = h5.File(f"{name}.vtkhdf", "w")
    hdf_root = f.create_group("VTKHDF")

    tree = ET.parse(shell_path)
    xml_root = tree.getroot()

    create_structure(xml_root, hdf_root)

    hdf_root.attrs.create("Dimensions", data=tuple(map(int,xml_root[0].attrib["Dimensions"].split())))
    hdf_root.attrs.create("BranchFactor", data=(int(xml_root[0].attrib["BranchFactor"]),))

    append_data_from_xml(xml_root, hdf_root)


# -----------------------------------------------------------------
if __name__ == "__main__":
    generate_htg_from_xml("randomhtg")
    generate_temporal_htg("temporal_htg")
    generate_multipiece_htg("multipiece_htg")
    generate_multipiece_temporal_htg("multipiece_temporal_htg")

    # pass the path to shell_3D to write it to VTKHDF, including interfaces
    if len(sys.argv) == 2:
        generate_shell3D_interfaces(sys.argv[1], "shell_3d")
