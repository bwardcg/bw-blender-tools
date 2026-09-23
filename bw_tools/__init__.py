bl_info = {
    "name": "BW Tools",
    "author": "bwardcg",
    "version": (1, 0, 2),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > BW Tools",
    "description": "Studio tools: Playblast, Match Transforms and Freeze Geo.",
    "category": "Object",
}

import bpy

from .playblast import run_playblast
from .match_transforms import match_transforms
from .freeze_geo import freeze_geo


class BWTOOLS_OT_playblast(bpy.types.Operator):
    """Render an OpenGL viewport playblast to an .mp4 next to the .blend file"""
    bl_idname = "bwtools.playblast"
    bl_label = "Playblast"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            run_playblast()
        except Exception as e:
            self.report({'ERROR'}, f"Playblast error: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


class BWTOOLS_OT_match_transforms(bpy.types.Operator):
    """Copy location, rotation, and scale from the active object to the other selected objects"""
    bl_idname = "bwtools.match_transforms"
    bl_label = "Match Transforms"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            match_transforms()
        except Exception as e:
            self.report({'ERROR'}, f"Match Transforms error: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


class BWTOOLS_OT_freeze_geo(bpy.types.Operator):
    """Bake transforms, deltas and parent inverses of selected meshes (and meshes inside selected groups) into their geometry"""
    bl_idname = "bwtools.freeze_geo"
    bl_label = "Freeze Geo"
    bl_options = {'REGISTER', 'UNDO'}

    apply_modifiers: bpy.props.BoolProperty(
        name="Apply Modifiers",
        description="Bake the viewport modifier result into the mesh and clear the modifier stack "
                    "(viewport-disabled modifiers are dropped)",
        default=True,
    )

    def execute(self, context):
        try:
            lines, has_warnings = freeze_geo(apply_modifiers=self.apply_modifiers)
        except Exception as e:
            self.report({'ERROR'}, f"Freeze Geo error: {e}")
            return {'CANCELLED'}

        # Full report lands in the Info editor; the popup shows it right away.
        self.report({'WARNING'} if has_warnings else {'INFO'}, "Freeze Geo:\n" + "\n".join(lines))
        if not bpy.app.background:
            def draw(menu, _context):
                for line in lines:
                    menu.layout.label(text=line, icon='ERROR' if "WARNING" in line else 'NONE')
            context.window_manager.popup_menu(draw, title="Freeze Geo", icon='FREEZE')

        return {'FINISHED'}


class BWTOOLS_PT_panel(bpy.types.Panel):
    bl_label = "BW Tools"
    bl_idname = "BWTOOLS_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BW Tools"

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        col.scale_y = 1.8
        col.operator("bwtools.playblast", icon='RENDER_ANIMATION')

        layout.separator()

        col2 = layout.column(align=True)
        col2.scale_y = 1.5
        col2.operator("bwtools.match_transforms", icon='CON_TRANSLIKE')
        col2.operator("bwtools.freeze_geo", icon='FREEZE')


classes = (
    BWTOOLS_OT_playblast,
    BWTOOLS_OT_match_transforms,
    BWTOOLS_OT_freeze_geo,
    BWTOOLS_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
