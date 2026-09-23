# Changelog

## [1.0.2] - 2026-09-23

### Added
- **Freeze Geo: Apply Modifiers** option (default on) bakes the viewport modifier result before freezing. Skips meshes with shape keys and Geometry Nodes output containing instances.
- **Freeze Geo: verbose report** listing each object's operations (transforms/deltas/parent inverse removed, unparenting) and its mesh data's operations (modifiers applied/dropped, transform baked, normals flipped, single-user copy), shown as a popup and in the Info editor.
- Warning when modifiers left on the stack will evaluate differently after freezing.

## [1.0.1] - 2026-09-23

### Added
- **Freeze Geo**: bakes object transforms, deltas and parent inverses into mesh data so meshes sit at identity (Maya-style Freeze Transformations for Geometry Nodes workflows).
- `install.py`: copies `bw_tools/` into Blender's user addons folder.

## [1.0.0] - 2026-09-23

### Added
- Initial release: **Playblast** and **Match Transforms** in the *BW Tools* sidebar panel.
