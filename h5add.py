import h5py

hdf5_file_path = "series.vtkhdf"

with h5py.File(hdf5_file_path, "a") as hdf_file:
        group_path = "/meta"
        if group_path not in hdf_file:
            result_group = hdf_file.create_group(group_path)

        ds1_name = "author"
        if ds1_name not in result_group:
            result_group.create_dataset(
                name=ds1_name,
                data="Darcy Yao",
                dtype=h5py.string_dtype(encoding="utf-8")
            )

