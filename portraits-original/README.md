# Original portraits

This directory contains original, project-generated portrait assets covered by
the repository root MIT license. It is deliberately separate from the
third-party `portraits/` and legacy `icons/` trees.

`han-archetypes/source/` is the immutable generated master. The build script
derives three runtime variants from each grid cell:

- `full/`: 148×210, whole composition preserved
- `bust/`: 148×210, head-and-shoulders crop
- `face/`: 96×96, face crop

Run:

```sh
python3 tools/build_original_portraits.py
```
