import numpy as np
import h5py as h5

"""
This file is an example illustrating how to create a VTKHDF file describing a HyperTreeGrid structure.
"""

# -----------------------------------------------------------------
# Global metadata
fType = "f8"
idType = "i8"
charType = "u1"

# -----------------------------------------------------------------
def generate_simple_htg(name: str) -> None:
    """Generate simple VTKHDF HTG file by filling each field manually."""

    """
    Possible lookup order in the reader:
    NumberOfTrees
    TreeIds (size is NumberOfTrees for the current piece)
    DepthPerTree (size is NumberOfTrees)
    NumberOfDepths
    NumberOfCellsPerTreeDepth (size is NumberOfDepths)
    DescriptorsSize
    Descriptors (size in bits is DescriptorsSize)
    NumberOfCells
    Mask (size is NumberOfCells)
    CellData (size is NumberOfCells)
    FieldData
    """

    f = h5.File(f"{name}.vtkhdf", "w")
    root = f.create_group("VTKHDF")

    root.attrs["Version"] = (2, 4)
    ascii_type = "HyperTreeGrid".encode("ascii")
    root.attrs.create("Type", ascii_type, dtype=h5.string_dtype("ascii", len(ascii_type)))

    # Global attributes
    root.attrs.create("TransposedRootIndexing", data=(0,), dtype=idType)
    root.attrs.create("Dimensions", data=(3,3,2), dtype=idType)
    root.attrs.create("BranchFactor", data=(2,), dtype=idType)
    
    # Coordinates of the grid cells
    root.create_dataset("XCoordinates", data=(0, 10, 20), dtype=fType)
    root.create_dataset("YCoordinates", data=(0, 10, 20), dtype=fType)
    root.create_dataset("ZCoordinates", data=(0, 10), dtype=fType)

    # Tree descriptions
    descriptors = (
          # Tree 0 : no refinement

          # Tree 1
          1,  # Depth 1
            0, 0, 1, 0, 0, 0, 0, 0, # Depth 2
            # Max depth is 3, so nothing is refined on level 3 : no descriptor

          # Tree 2
          1, # Depth 1
            0, 1, 0, 0, 0, 0, 0, 0, # Depth 2

          # Tree 3 : refined at level 1
          1, # Max depth is 2, so nothing is refined on level 2
    )
    packed_descriptors = np.packbits(descriptors)
    root.create_dataset("Descriptors", data=packed_descriptors, dtype=charType)
    root.create_dataset("DescriptorsSize", data=(len(descriptors),), dtype=idType) # 19 packed bits => 3 bytes to read

    depths = (1, 3, 3, 2)
    root.create_dataset("DepthPerTree", data=depths, dtype=idType)
    root.create_dataset("NumberOfDepths", data=(sum(depths),), dtype=idType)
    root.create_dataset("NumberOfCellsPerTreeDepth", data=(
        # Tree 0 : 1 depth
        1,
        # Tree 1 : 3 depth
        1, 8, 8,
        # Tree 2 : 3 depth
        1, 8, 8,
        # Tree 3 : 2 depth
        1, 8), dtype=idType)
    
    treeIds = (0, 1, 2, 3)
    root.create_dataset("TreeIds", data=treeIds, dtype=idType)
    root.create_dataset("NumberOfTrees", data=(len(treeIds),), dtype=idType)

    # Size of mask : total number of cells (sum of NumberOfCellsPerTreeDepth)
    mask = (
          1, 0, 0, 0, 0, 0,
          0, 0, 0, 0, 0, 0,
          0, 0, 0, 0, 0, 0,
          0, 0, 0, 0, 0, 0,
          0, 0, 0, 0, 0, 0,
          0, 0, 0, 0, 0, 0,
          0, 0, 0, 0, 0, 0,
          0, 0
    )
    packed_mask = np.packbits(mask)
    root.create_dataset("Mask", data=packed_mask, dtype=charType)    


    # Cell & Field data
    depth = (
          0, 0, 1, 1, 1, 1,
          1, 1, 1, 1, 2, 2,
          2, 2, 2, 2, 2, 2,
          0, 1, 1, 1, 1, 1,
          1, 1, 1, 2, 2, 2,
          2, 2, 2, 2, 2, 0,
          1, 1, 1, 1, 1, 1,
          1, 1
    )
    root.create_dataset("CellData/Depth", data=depth, dtype=idType)
    root.create_dataset("NumberOfCells", data=(len(depth),), dtype=idType)

    fData = root.create_group('FieldData')
    fData.create_dataset("MyFieldData", data=(1,2), dtype=idType)




# -----------------------------------------------------------------
if __name__ == "__main__":
    generate_simple_htg("simple_htg")
