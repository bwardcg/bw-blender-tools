# bw-blender-tools

Personal Blender addon with small studio utilities, added to the *BW Tools* panel in the 3D viewport sidebar (`N` panel).

## Tools

- **Playblast** — renders an OpenGL viewport playblast to `Playblast/<blend_name>.mp4`, one folder up from the `.blend` file. Restores your original render output settings afterward.
- **Match Transforms** — copies location, rotation, and scale from the active object to all other selected objects (select targets, then shift-select the source last so it's active).

## Install

1. Zip the `bw_tools/` folder (or point Blender at it directly).
2. In Blender: `Edit > Preferences > Add-ons > Install...`, select the zip (or the folder's `__init__.py`).
3. Enable "BW Tools".
4. Open the sidebar in the 3D viewport (`N`) and find the "BW Tools" tab.
