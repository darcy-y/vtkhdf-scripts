#!/usr/bin/env python3
# @ Author      :  darcy-y
# @ Time        :  2026-04-07 18:00:09

# python3 h5add.py --vtkhdf-path output/case_000001.vtkhdf --json-path input/case_000001/case_000001.json

import argparse
import json
import h5py
from pathlib import Path


def _to_attr_value(v):
    if v is None:
        return "null"
    if isinstance(v, (bool, int, float, str)):
        return v
    return json.dumps(v, ensure_ascii=False)


def _write_dict_as_group(h5group, data: dict):
    for k, v in data.items():
        key = str(k)

        if isinstance(v, dict):
            sub = h5group.create_group(key)
            _write_dict_as_group(sub, v)
        else:
            h5group.attrs[key] = _to_attr_value(v)


def add_info_json_to_vtkhdf(vtkhdf_path: str, json_path: str):
    vtkhdf_path = Path(vtkhdf_path)
    json_path = Path(json_path)

    with open(json_path, "r", encoding="utf-8") as f:
        obj = json.load(f)

    raw_json = json.dumps(obj, ensure_ascii=False, indent=2)

    with h5py.File(vtkhdf_path, "a") as h5f:
        if "INFO" in h5f:
            del h5f["INFO"]

        info = h5f.create_group("INFO")

        # store full raw json text
        dt = h5py.string_dtype(encoding="utf-8")
        info.create_dataset("raw_json", data=raw_json, dtype=dt)

        # mirror json hierarchy
        if isinstance(obj, dict):
            _write_dict_as_group(info, obj)
        else:
            info.attrs["value"] = _to_attr_value(obj)


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Add info from JSON file to VTKHDF file"
    )
    parser.add_argument("--vtkhdf-path", type=str, help="Path to the VTKHDF file")
    parser.add_argument(
        "--json-path", type=str, help="Path to the JSON file containing info"
    )

    args = parser.parse_args()

    add_info_json_to_vtkhdf(args.vtkhdf_path, args.json_path)


if __name__ == "__main__":
    main()
