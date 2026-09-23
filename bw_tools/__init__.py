bl_info = {
    "name": "BW Tools",
    "author": "bwardcg",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > BW Tools",
    "description": "Studio tools: Playblast and Match Transforms.",
    "category": "Object",
}

import bpy

from .playblast import run_playblast
from .match_transforms import match_transforms


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


classes = (
    BWTOOLS_OT_playblast,
    BWTOOLS_OT_match_transforms,
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
