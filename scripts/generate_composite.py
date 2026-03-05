import numpy as np
import h5py as h5
import generate_unstructured_grid as guc
import generate_image_data as gid

import vtkhdf_utilities as util

# -----------------------------------------------------------------
def generate_composite_dataset():
  f = h5.File('composite.vtkhdf', 'w')

  # Generate the root content which will have the Version and Type attributes
  root = f.create_group('VTKHDF', track_order=True)
  root.attrs['Version'] = (2,1)
  ascii_type = 'PartitionedDataSetCollection'.encode('ascii')
  root.attrs.create('Type', ascii_type, dtype=h5.string_dtype('ascii', len(ascii_type))) 

  # All data
  blockNumber = 2
  allBlock = []
  allBlockName = []

  # Create  a group
  assembly = root.create_group('Assembly', track_order=True)

  # Poly data
  centers = [[5,0,0], [10,0,0]]
  resolutions = [20, 5]
  for i in range(0, blockNumber):
    blockName = 'blockName' + str(i)
    block = root.create_group(blockName)
    allBlock.append(block)
    allBlockName.append(blockName)

    util.generate_geometry_structure(block)
    pds = util.generate_static_spheres(centers[i], resolutions[i])
    for pd in pds:
      util.append_data(block, pd)

  # Unstructured Grid
  blockUG = root.create_group('blockName2')
  guc.generate_data(blockUG)

  # Image Data
  blockUG = root.create_group('blockName3')
  gid.generate_data(blockUG)

  # Assembly
  assembly["blockName0"] = h5.SoftLink("/VTKHDF/blockName0")
  assembly["blockName0"].attrs['Index'] = 0

  group0 = assembly.create_group('groupName0', track_order=True)
  group0.attrs['Index'] = 1
  group0["blockName1"] = h5.SoftLink("/VTKHDF/blockName1")
  group0["blockName1"].attrs['Index'] = 1

  assembly["blockName2"] = h5.SoftLink("/VTKHDF/blockName2")
  assembly["blockName2"].attrs['Index'] = 2

  assembly["blockName3"] = h5.SoftLink("/VTKHDF/blockName3")
  assembly["blockName3"].attrs['Index'] = 3


# -----------------------------------------------------------------
if __name__ == "__main__":
  generate_composite_dataset()
