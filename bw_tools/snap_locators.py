import bpy
from mathutils import Matrix

PREFIX = "loc_"


def _zero_local_transform(obj):
    """Identity local TRS and deltas, for every rotation mode."""
    obj.location = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    obj.rotation_axis_angle = (0.0, 0.0, 1.0, 0.0)
    obj.scale = (1.0, 1.0, 1.0)
    obj.delta_location = (0.0, 0.0, 0.0)
    obj.delta_rotation_euler = (0.0, 0.0, 0.0)
    obj.delta_rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    obj.delta_scale = (1.0, 1.0, 1.0)


def _has_transform_animation(obj):
    action = obj.animation_data.action if obj.animation_data else None
    if action is None:
        return False
    names = ("location", "rotation_euler", "rotation_quaternion", "rotation_axis_angle", "scale",
             "delta_location", "delta_rotation_euler", "delta_rotation_quaternion", "delta_scale")
    # Layered actions (Blender 4.4+) keep F-curves per channelbag; older actions on the action itself.
    try:
        fcurves = action.fcurves
    except AttributeError:
        fcurves = [fc for layer in action.layers for strip in layer.strips
                   for bag in strip.channelbags for fc in bag.fcurves]
    return any(fc.data_path in names for fc in fcurves)


def snap_locators(as_parent=False, constrain=False):
    """
    Creates a plain-axes Empty named "loc_<name>" for each selected object,
    linked to the scene's root collection, unparented, and matching the
    object's world transform.

    as_parent: parent each selected object under its locator with an identity
               local transform (TRS and deltas zeroed, no parent inverse).
    constrain: give each locator a Copy Transforms constraint targeting its object.

    Returns (created empties, warning lines).
    """
    if as_parent and constrain:
        raise RuntimeError("As Parent and Constrain can't be combined (the locator would follow its own child).")

    context = bpy.context
    sources = list(context.selected_objects)
    if not sources:
        raise RuntimeError("No objects selected.")

    # Make sure matrix_world reflects constraints, drivers and parenting, and snapshot
    # every world matrix before any reparenting can move selected children.
    context.view_layer.update()
    worlds = {src: src.matrix_world.copy() for src in sources}

    root = context.scene.collection
    pairs = []
    for src in sources:
        empty = bpy.data.objects.new(PREFIX + src.name, None)
        empty.empty_display_type = 'PLAIN_AXES'
        empty.rotation_mode = src.rotation_mode
        root.objects.link(empty)
        empty.matrix_world = worlds[src]
        pairs.append((src, empty))

    warnings = []
    for src, empty in pairs:
        if constrain:
            con = empty.constraints.new('COPY_TRANSFORMS')
            con.target = src

        if as_parent:
            if src.constraints:
                warnings.append(f"{src.name}: has constraints, may not stay in place under {empty.name}")
            if _has_transform_animation(src):
                warnings.append(f"{src.name}: transform animation will override the zeroed TRS")
            src.parent = empty
            src.parent_type = 'OBJECT'
            src.matrix_parent_inverse = Matrix.Identity(4)
            _zero_local_transform(src)

    # Select the new locators so the result is easy to see.
    for src in sources:
        src.select_set(False)
    created = [empty for _src, empty in pairs]
    for empty in created:
        empty.select_set(True)
    context.view_layer.objects.active = created[-1]

    mode = " (as parent)" if as_parent else " (constrained)" if constrain else ""
    print(f"Snapped {len(created)} locator(s){mode}: {', '.join(e.name for e in created)}")
    for line in warnings:
        print(f"  WARNING {line}")
    return created, warnings
