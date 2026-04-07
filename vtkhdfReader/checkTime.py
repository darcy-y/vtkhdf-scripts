import vtk

reader = vtk.vtkHDFReader()
reader.SetFileName("../output/case_000001.vtkhdf")
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
