import numpy as np
import h5py as h5

# -----------------------------------------------------------------
# Global metadata
fType = 'f'
idType = 'i8'
charType = 'uint8'

# -----------------------------------------------------------------
def generate_structure_for_image_data(root):
  root.attrs['Version'] = (2,0)
  ascii_type = 'ImageData'.encode('ascii')
  root.attrs.create('Type', ascii_type, dtype=h5.string_dtype('ascii', len(ascii_type))) 

  whole_extent = [0,3,0,3,0,3]
  root.attrs.create('WholeExtent', whole_extent, dtype=fType)
  origin = [5,0,0]
  root.attrs.create('Origin', origin, dtype=fType)
  spacing= [0.1, 0.1, 0.1]
  root.attrs.create('Spacing', spacing, dtype=fType)
  direction = [1, 0, 0, 0, 1, 0, 0, 0, 1]
  root.attrs.create('Direction', direction, dtype=fType)


# -----------------------------------------------------------------
def generate_data(root):
  generate_structure_for_image_data(root)

  return root

# -----------------------------------------------------------------
def generate_image_data(name):
  f = h5.File('imagedata.vtkhdf', 'w')

  # check the script on bailey for the next step
  root = f.create_group(name)
  generate_data(root)

# -----------------------------------------------------------------
if __name__ == "__main__":
  generate_image_data('VTKHDF')
