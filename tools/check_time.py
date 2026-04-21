import argparse

import vtk


parser = argparse.ArgumentParser(description="Print time steps detected by vtkHDFReader.")
parser.add_argument("vtkhdf_path", nargs="?", default="output/case_000001.vtkhdf")
args = parser.parse_args()

reader = vtk.vtkHDFReader()
reader.SetFileName(args.vtkhdf_path)
reader.UpdateInformation()

info = reader.GetOutputInformation(0)
execu = reader.GetExecutive()

if info.Has(execu.TIME_STEPS()):
    n = info.Length(execu.TIME_STEPS())
    times = [info.Get(execu.TIME_STEPS(), i) for i in range(n)]
    print("Detected time steps:", n)
    print(times)
else:
    print("No time steps detected")
