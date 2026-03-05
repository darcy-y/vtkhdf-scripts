import argparse
import numpy as np
import h5py as h5

# -----------------------------------------------------------------
# Global metadata
fType = 'f'
idType = 'i8'
charType = 'uint8'

# -----------------------------------------------------------------
def generate_simple_overlapping_amr(output_name):
  f = h5.File(output_name + '.vtkhdf', 'w')

  # Attributes
  root = f.create_group('VTKHDF', track_order=True)
  root.attrs['Version'] = (2,2)

  type = b'OverlappingAMR'
  root.attrs.create('Type', type, dtype=h5.string_dtype('ascii', len(type)))

  description = b'XYZ'
  root.attrs.create('GridDescription', description, dtype=h5.string_dtype('ascii', len(description)))

  origin = [-2,-2,0]
  root.attrs.create('Origin', origin, dtype=fType)

  # Levels definitions
  level0 = root.create_group("Level0")
  spacing = [0.5, 0.5, 0.5]
  level0.attrs.create('Spacing', spacing, dtype=fType)

  amrbox0_values = [[0,4,0,4,0,4]]
  amrbox0 = level0.create_dataset('AMRBox', data=amrbox0_values)

  level0_celldata = level0.create_group("CellData")
  level0_celldata_constant = np.full(shape=(5**3,3), fill_value=(1), dtype=fType)
  level0_celldata.create_dataset("Constant", data=level0_celldata_constant)

  level0.create_group("PointData")
  level0.create_group("FieldData")

  level1 = root.create_group("Level1")
  spacing = [0.25, 0.25, 0.25]
  level1.attrs.create('Spacing', spacing, dtype=fType)

  amrbox1_values = [
    [0,3,0,5,0,9],
    [6,9,4,9,0,9]
  ]
  amrbox1 = level1.create_dataset('AMRBox', data=amrbox1_values)

  level1_celldata = level1.create_group("CellData")
  level1_celldata_constant = np.full(shape=(480,3), fill_value=(2), dtype=fType)
  level1_celldata.create_dataset("Constant", data=level1_celldata_constant)
  level1.create_group("PointData")
  level1.create_group("FieldData")

  f.close()

# -----------------------------------------------------------------
def generate_temporal_overlapping_amr(output_name):
  f = h5.File(output_name + '.vtkhdf', 'w')

  # Attributes
  root = f.create_group('VTKHDF', track_order=True)
  root.attrs['Version'] = (2,2)

  type = b'OverlappingAMR'
  root.attrs.create('Type', type, dtype=h5.string_dtype('ascii', len(type)))

  description = b'XYZ'
  root.attrs.create('GridDescription', description, dtype=h5.string_dtype('ascii', len(description)))

  origin = [-2,-2,0]
  root.attrs.create('Origin', origin, dtype=fType)

  # LEVEL 0
  level0 = root.create_group("Level0")
  spacing = [0.5, 0.5, 0.5]
  level0.attrs.create('Spacing', spacing, dtype=fType)

  amrbox0_values = [
    # static mesh
    [0,4,0,4,0,4]
  ]
  amrbox0 = level0.create_dataset('AMRBox', data=amrbox0_values)

  level0_celldata = level0.create_group("CellData")
  level0_celldata_constant = np.full(shape=(375,3), fill_value=(1), dtype=fType)
  level0_celldata_constant[125:250,] = 2
  level0_celldata_constant[250:,] = 3
  level0_celldata.create_dataset("Constant", data=level0_celldata_constant)

  level0_celldata_random = np.random.rand(125,3)
  level0_celldata.create_dataset("Random", data=level0_celldata_random)

  level0_pointdata = level0.create_group("PointData")
  values = np.linspace(0,1,648)
  level0_pointdata_constant = values
  level0_pointdata.create_dataset("Linear", data=level0_pointdata_constant)

  level0_fielddata = level0.create_group("FieldData")
  timeValues = [0.0, 0.5, 1.0]
  level0_fielddata.create_dataset("TimeValues", data=timeValues)
  dummy = [1,2,3,4,5,6]
  level0_fielddata.create_dataset("Dummy", data=dummy)


  # LEVEL 1
  level1 = root.create_group("Level1")
  spacing = [0.25, 0.25, 0.25]
  level1.attrs.create('Spacing', spacing, dtype=fType)

  # varying number of amrbox between timesteps
  amrbox1_values = [
    # t0
    [0,3,0,5,0,9],
    [6,9,4,9,0,9],
    # t1
    [2,7,2,7,0,9],
    # t2
    [4,5,4,5,0,9]
  ]
  amrbox1 = level1.create_dataset('AMRBox', data=amrbox1_values)

  level1_celldata = level1.create_group("CellData")
  level1_celldata_constant = np.full(shape=(880,3), fill_value=(4), dtype=fType)
  level1_celldata_constant[480:840,] = 5
  level1_celldata_constant[840:,] = 6
  level1_celldata.create_dataset("Constant", data=level1_celldata_constant)
  level1_celldata_random = np.random.rand(880,3)
  level1_celldata.create_dataset("Random", data=level1_celldata_random)

  level1_pointdata = level1.create_group("PointData")
  values = np.linspace(0,1,1550)
  level1_pointdata_constant = values
  level1_pointdata.create_dataset("Linear", data=level1_pointdata_constant)

  level1_fielddata = level1.create_group("FieldData")
  level1_fielddata.create_dataset("TimeValues", data=timeValues)
  level1_fielddata.create_dataset("Dummy", data=dummy)

  # STEPS
  steps = root.create_group("Steps")
  nsteps = 3
  steps.attrs.create('NSteps', data=nsteps, dtype=idType)
  steps.create_dataset('Values', data=timeValues)

  # STEP 0
  step_level0 = steps.create_group("Level0")
  AMRBoxOffset0 = [0, 0, 0]
  step_level0.create_dataset('AMRBoxOffset', data=AMRBoxOffset0)
  NumberOfAMRBox0 = [1, 1, 1]
  step_level0.create_dataset('NumberOfAMRBox', data=NumberOfAMRBox0)

  cellDataOffsetGroup = step_level0.create_group("CellDataOffset")
  constant_offset = [0,125,250]
  cellDataOffsetGroup.create_dataset("Constant", data=constant_offset)
  random_offset = [0,0,0]
  cellDataOffsetGroup.create_dataset("Random", data=random_offset)

  pointDataOffsetGroup = step_level0.create_group("PointDataOffset")
  sin_offset = [0,216,432]
  pointDataOffsetGroup.create_dataset("Linear", data=sin_offset)

  fieldDataOffsetGroup0 = step_level0.create_group("FieldDataOffset")
  time_fielddata_offset = [0,1,2]
  fieldDataOffsetGroup0.create_dataset("TimeValues", data=time_fielddata_offset)
  dummy_offset = [0,2,4]
  fieldDataOffsetGroup0.create_dataset("Dummy", data=dummy_offset)

  # STEP 1
  step_level1 = steps.create_group("Level1")
  AMRBoxOffset1 = [0, 2, 3]
  step_level1.create_dataset('AMRBoxOffset', data=AMRBoxOffset1)
  NumberOfAMRBox1 = [2, 1, 1]
  step_level1.create_dataset('NumberOfAMRBox', data=NumberOfAMRBox1)

  cellDataOffsetGroup1 = step_level1.create_group("CellDataOffset")
  constant_offset = [0,480,840]
  cellDataOffsetGroup1.create_dataset("Constant", data=constant_offset)
  random_offset1 = [0,480,840]
  cellDataOffsetGroup1.create_dataset("Random", data=random_offset1)

  pointDataOffsetGroup1 = step_level1.create_group("PointDataOffset")
  value_offset = [0,830,1451]
  pointDataOffsetGroup1.create_dataset("Linear", data=value_offset)

  fieldDataOffsetGroup1 = step_level1.create_group("FieldDataOffset")
  fieldDataOffsetGroup1.create_dataset("TimeValues", data=time_fielddata_offset)
  fieldDataOffsetGroup1.create_dataset("Dummy", data=dummy_offset)

  f.close()

# -----------------------------------------------------------------
if __name__ == "__main__":
  parser = argparse.ArgumentParser(
    description='Generates overlapping amr following the VTKHDF file format.')
  
  parser.add_argument('-t',
                      '--temporal',
                      dest='mode',
                      action='store_const',
                      const=True,
                      default=False,
                      help='generates temporal overlappingAMR.')

  parser.add_argument('-o',
                      '--output',
                      dest='output',
                      default="overlapping_amr",
                      help='specify the output filename.')


  args = parser.parse_args()

  if args.mode:
    generate_temporal_overlapping_amr(args.output)
  else:
    generate_simple_overlapping_amr(args.output)
