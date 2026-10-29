# bw-blender-tools

## Panel checkboxes beside buttons

Every tool here puts its option checkboxes in the button's row: the checkbox shows a scene setting (`context.scene.bwtools_<tool>`), and `draw()` copies that setting onto the operator button (`op.prop = settings.prop`) so the click runs with it.

- `draw()` runs on every redraw, so it must have no side effects.
- **Operator properties that `draw()` writes to must have no `update=` callback.** Put mutual exclusion and any other update callbacks on the scene PropertyGroup the checkbox shows (see `_exclusive` on `BWTOOLS_SnapLocatorsSettings`), and enforce the same rule again in the operator's `execute()`.
- Why: in Oct 2026, Snap Locators operator properties had `update=_exclusive(...)` and were set from `draw()`. While the BW Tools sidebar tab was visible, viewport gizmos became unclickable in every viewport: arrows highlighted on hover, but a click box-selected instead; G still worked. Switching to another sidebar tab fixed it. It looked like Playblast broke the gizmos, because the panel was clicked before each playblast. Fixed in `34ecb25`.

## Installed copy

Blender loads the add-on from its own copy in `%APPDATA%\Blender Foundation\Blender\<ver>\scripts\addons\bw_tools`, not from this repo. After changing code, run `python install.py`, then restart Blender or untick and re-tick BW Tools. `install.py` copies the working tree, uncommitted changes included, so check with other sessions working here before running it.
