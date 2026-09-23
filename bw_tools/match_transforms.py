import bpy


def match_transforms():
    """
    Copies location, rotation, and scale from the active object
    to all other selected objects (Selection to Active).
    """
    active = bpy.context.active_object

    if active is None:
        print("Error: No active object.")
        return

    selected = [obj for obj in bpy.context.selected_objects if obj != active]

    if not selected:
        print("Error: No other objects selected. Select target objects and make the source object active.")
        return

    for obj in selected:
        obj.location = active.location.copy()
        obj.rotation_euler = active.rotation_euler.copy()
        obj.rotation_quaternion = active.rotation_quaternion.copy()
        obj.rotation_axis_angle = active.rotation_axis_angle[:]
        obj.scale = active.scale.copy()

    print(f"Matched transforms from '{active.name}' to {len(selected)} object(s): "
          f"{', '.join(obj.name for obj in selected)}")
