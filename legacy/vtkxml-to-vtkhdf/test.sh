#!/usr/bin/env bash
VTK_PYTHONPATH=/path/to/vtkpython
VTKHDF_DATA_SAMPLES_LOCATION=vtkhdf-data-samples

echo "Testing mandelbrot.vti"
echo "======================================================================"
PYTHONPATH=${VTK_PYTHONPATH} python3 vtkxml-to-vtkhdf.py ${VTKHDF_DATA_SAMPLES_LOCATION}/mandelbrot.vti --output output/mandelbrot-vti.hdf
h5dump output/mandelbrot-vti.hdf > output/mandelbrot-vti.txt
diff ${VTKHDF_DATA_SAMPLES_LOCATION}/mandelbrot-vti.txt.baseline output/mandelbrot-vti.txt 1>&1
echo
echo "Testing mandelbrot.pvti"
echo "======================================================================"
PYTHONPATH=${VTK_PYTHONPATH} python3 vtkxml-to-vtkhdf.py ${VTKHDF_DATA_SAMPLES_LOCATION}/mandelbrot.pvti --output output/mandelbrot-pvti.hdf
h5dump output/mandelbrot-pvti.hdf > output/mandelbrot-pvti.txt
diff ${VTKHDF_DATA_SAMPLES_LOCATION}/mandelbrot-pvti.txt.baseline output/mandelbrot-pvti.txt 1>&2
echo
echo "Testing can_0_0.vtu"
echo "======================================================================"
PYTHONPATH=${VTK_PYTHONPATH} python3 vtkxml-to-vtkhdf.py ${VTKHDF_DATA_SAMPLES_LOCATION}/can_0_0.vtu --output output/can-vtu.hdf
h5dump output/can-vtu.hdf > output/can-vtu.txt
diff ${VTKHDF_DATA_SAMPLES_LOCATION}/can-vtu.txt.baseline output/can-vtu.txt 1>&2
echo
echo "Testing can_0_0.pvtu"
echo "======================================================================"
PYTHONPATH=${VTK_PYTHONPATH} python3 vtkxml-to-vtkhdf.py ${VTKHDF_DATA_SAMPLES_LOCATION}/can_0_0.pvtu --output output/can-pvtu.hdf
h5dump output/can-pvtu.hdf > output/can-pvtu.txt
diff ${VTKHDF_DATA_SAMPLES_LOCATION}/can-pvtu.txt.baseline output/can-pvtu.txt 1>&2
echo "======================================================================"
PYTHONPATH=${VTK_PYTHONPATH} python3 vtkxml-to-vtkhdf.py ${VTKHDF_DATA_SAMPLES_LOCATION}/TextureMaptoPlane1_000000.pvtu --output output/TextureMaptoPlane1_000000-pvtu.hdf
h5dump output/TextureMaptoPlane1_000000-pvtu.hdf > output/output/TextureMaptoPlane1_000000-pvtu.txt

