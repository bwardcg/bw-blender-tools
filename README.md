# bw-blender-tools

Personal Blender addon with small studio utilities, added to the *BW Tools* panel in the 3D viewport sidebar (`N` panel).

## Tools

- **Playblast** — renders an OpenGL viewport playblast to `Playblast/<blend_name>.mp4`, one folder up from the `.blend` file. Restores your original render output settings afterward.
- **Match Transforms** — copies location, rotation, and scale from the active object to all other selected objects (select targets, then shift-select the source last so it's active).
- **Freeze Geo** — bakes transforms, delta transforms and parent inverses into mesh data so every mesh sits at an identity matrix (what you see is what Geometry Nodes gets). Only the **selected mesh objects** are changed; everything else (empties, cameras, lights, unselected children) is skipped. A selected mesh whose parent isn't also frozen is unparented, keeping its world placement. Unselected children of a frozen mesh stay in place via their parent inverse, with their own transforms and animation untouched. Linked duplicates get their own mesh copy, and negative scale is handled.
  - Two checkboxes next to the button (hover for tooltips), saved with the scene and also editable afterwards in the *Adjust Last Operation* panel:
    - **Apply Modifiers** (on by default)
    - **Force** (off by default): freeze meshes even when their modifiers would have to stay on the stack; they're kept, with a warning. Never overrides type-based skipping.
  - **Apply Modifiers**: bakes the viewport modifier result into the mesh first and clears the stack; viewport-disabled modifiers are dropped.
  - If modifiers would have to stay on the stack (mesh has shape keys, Geometry Nodes output contains instances, or Apply Modifiers is off) and freezing would change how they evaluate, the **whole object is skipped**.
  - Shows a per-object report of every operation performed, or what would have been done for skipped objects (popup, Info editor, and system console).

## Install

From the repo, copy `bw_tools/` into the newest Blender's user addons folder (replacing any old copy):

```
python install.py        # or: python install.py 5.1
```

Then restart Blender, or untick/tick "BW Tools" in Preferences. Re-run after pulling or switching versions to keep the installed copy in sync with the repo.

Or install manually:

1. Zip the `bw_tools/` folder (or point Blender at it directly).
2. In Blender: `Edit > Preferences > Add-ons > Install...`, select the zip (or the folder's `__init__.py`).
3. Enable "BW Tools".
4. Open the sidebar in the 3D viewport (`N`) and find the "BW Tools" tab.

## Versioning

Releases follow `MAJOR.MINOR.PATCH`, tagged in git as `vX.Y.Z`, and match `bl_info["version"]` in `bw_tools/__init__.py`. See [CHANGELOG.md](CHANGELOG.md).
