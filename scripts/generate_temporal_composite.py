import h5py as h5
import generate_poly_data as gpd
import generate_unstructured_grid as gud
import generate_image_data as gid

# -----------------------------------------------------------------
def generate_temporal_composite_dataset():
  f = h5.File('composite_temporal.vtkhdf', 'w')

  # Generate the root content which will have the Version and Type attributes
  root = f.create_group('VTKHDF', track_order=True)
  root.attrs['Version'] = (2,1)
  ascii_type = 'PartitionedDataSetCollection'.encode('ascii')
  root.attrs.create('Type', ascii_type, dtype=h5.string_dtype('ascii', len(ascii_type)))

  # Poly data
  blockPD = root.create_group('blockName0')
  gpd.generate_data(blockPD)

  # Unstructured Grid
  blockUG = root.create_group('blockName1')
  gud.generate_data(blockUG)

  # Image Data
  blockUG = root.create_group('blockName2')
  gid.generate_data(blockUG)

  # Assembly
  assembly = root.create_group('Assembly', track_order=True)
  assembly["blockName0"] = h5.SoftLink("/VTKHDF/blockName0")
  assembly["blockName0"].attrs['Index'] = 0

  group0 = assembly.create_group('groupName0', track_order=True)
  group0.attrs['Index'] = 1
  group0["blockName1"] = h5.SoftLink("/VTKHDF/blockName1")
  group0["blockName1"].attrs['Index'] = 1

  assembly["blockName2"] = h5.SoftLink("/VTKHDF/blockName2")
  assembly["blockName2"].attrs['Index'] = 2
  f.close()


# -----------------------------------------------------------------
if __name__ == "__main__":
  generate_temporal_composite_dataset()
