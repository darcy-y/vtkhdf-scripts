#!/usr/bin/env bash

# mkdir output

VTKHDF_DATA_SAMPLES_LOCATION=input/case_000001/dump/particle/dump_257139.vtu

# by default will use same name as input file
python3 vtkxml-to-vtkhdf/vtkxml-to-vtkhdf.py ${VTKHDF_DATA_SAMPLES_LOCATION} # --output output/dump_drum.hdf 

