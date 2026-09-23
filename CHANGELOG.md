# Changelog

## [1.0.2] - 2026-09-23

### Added
- **Freeze Geo: Apply Modifiers** option (default on) bakes the viewport modifier result before freezing. Skips meshes with shape keys and Geometry Nodes output containing instances.
- **Freeze Geo: verbose report** listing each object's operations (transforms/deltas/parent inverse removed, unparenting) and its mesh data's operations (modifiers applied/dropped, transform baked, normals flipped, single-user copy), shown as a popup and in the Info editor.
- Meshes whose modifiers would stay on the stack and evaluate differently after freezing are skipped entirely, with the would-be operations listed in the report.

### Changed
- **Freeze Geo only operates on the selected mesh objects.** Group empties and other non-mesh objects are skipped, and descendants are no longer collected.
- Unselected children of a frozen mesh keep their placement through their parent inverse instead of a recomputed local transform, so their own transforms and animation are untouched.

## [1.0.1] - 2026-09-23

### Added
- **Freeze Geo**: bakes object transforms, deltas and parent inverses into mesh data so meshes sit at identity (Maya-style Freeze Transformations for Geometry Nodes workflows).
- `install.py`: copies `bw_tools/` into Blender's user addons folder.

## [1.0.0] - 2026-09-23

### Added
- Initial release: **Playblast** and **Match Transforms** in the *BW Tools* sidebar panel.
