#!/usr/bin/env bash

# mkdir output

VTKHDF_DATA_SAMPLES_LOCATION=input/*

# by default will use same name as input file
python3 vtkxml-to-vtkhdf/vtkxml-to-vtkhdf.py ${VTKHDF_DATA_SAMPLES_LOCATION} # --output output/dump_drum.hdf 

