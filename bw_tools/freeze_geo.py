import math

import bpy
from mathutils import Matrix, Quaternion, Vector

EPS = 1e-6
L1 = "..  "
L2 = "..  ..  "
L3 = "..  ..  ..  "


def _is_identity(m):
    return all(abs(m[i][j] - (1.0 if i == j else 0.0)) < EPS for i in range(4) for j in range(4))


def _fmt(values):
    return "(" + ", ".join(f"{0.0 if abs(v) < 1e-4 else v:.4g}" for v in values) + ")"


def _rotation_quat(obj, delta=False):
    if delta:
        if obj.rotation_mode == 'QUATERNION':
            return obj.delta_rotation_quaternion.copy()
        return obj.delta_rotation_euler.to_quaternion()
    if obj.rotation_mode == 'QUATERNION':
        return obj.rotation_quaternion.copy()
    if obj.rotation_mode == 'AXIS_ANGLE':
        angle, *axis = obj.rotation_axis_angle
        return Quaternion(axis, angle)
    return obj.rotation_euler.to_quaternion()


def _degrees(quat):
    return [math.degrees(a) for a in quat.to_euler()]


# Object-level operations are (done, todo) pairs: "location applied" for the report
# of a frozen object, "apply location" for the would-be list of a skipped one.

def _describe_object(obj, will_unparent):
    ops = []
    if obj.location.length > EPS:
        v = _fmt(obj.location)
        ops.append((f"location applied {v}", f"apply location {v}"))
    rot = _rotation_quat(obj)
    if rot.angle > EPS:
        v = _fmt(_degrees(rot))
        ops.append((f"rotation applied {v} deg", f"apply rotation {v} deg"))
    if (Vector(obj.scale) - Vector((1, 1, 1))).length > EPS:
        v = _fmt(obj.scale)
        ops.append((f"scale applied {v}", f"apply scale {v}"))

    if obj.delta_location.length > EPS:
        v = _fmt(obj.delta_location)
        ops.append((f"delta location removed {v}", f"remove delta location {v}"))
    rot = _rotation_quat(obj, delta=True)
    if rot.angle > EPS:
        v = _fmt(_degrees(rot))
        ops.append((f"delta rotation removed {v} deg", f"remove delta rotation {v} deg"))
    if (Vector(obj.delta_scale) - Vector((1, 1, 1))).length > EPS:
        v = _fmt(obj.delta_scale)
        ops.append((f"delta scale removed {v}", f"remove delta scale {v}"))

    if not _is_identity(obj.matrix_parent_inverse):
        ops.append(("parent inverse removed", "remove parent inverse"))
    if will_unparent:
        name = obj.parent.name
        ops.append((f"unparented from {name} (world placement baked in)",
                    f"unparent from {name} (world placement baked in)"))
    return ops


def _clear_deltas(obj):
    obj.delta_location = (0.0, 0.0, 0.0)
    obj.delta_rotation_euler = (0.0, 0.0, 0.0)
    obj.delta_rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    obj.delta_scale = (1.0, 1.0, 1.0)


def _unappliable_reason(obj, apply_modifiers, gn_instancers):
    """Why this mesh's modifiers would stay on the stack, or None if they won't."""
    if not obj.modifiers:
        return None
    names = ", ".join(m.name for m in obj.modifiers)
    if not apply_modifiers:
        return f"modifiers NOT applied, Apply Modifiers is off: {names}"
    if obj.data.shape_keys:
        return f"modifiers NOT applied, mesh has shape keys: {names}"
    if obj in gn_instancers and obj.instance_type == 'NONE':
        # new_from_object only keeps real mesh; instances would silently vanish.
        return f"modifiers NOT applied, Geometry Nodes output has instances (add Realize Instances): {names}"
    return None


def _apply_modifiers(objects, depsgraph, data_ops):
    """
    Replace each object's mesh with its viewport-evaluated result and clear the stack.
    All results are evaluated up front so modifiers that reference other objects
    (booleans, mirror targets...) see the scene as it was before anything changed.
    """
    evaluated = {obj: bpy.data.meshes.new_from_object(
                     obj.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph)
                 for obj in objects}

    for obj, new_mesh in evaluated.items():
        applied = [m.name for m in obj.modifiers if m.show_viewport]
        dropped = [m.name for m in obj.modifiers if not m.show_viewport]

        old_mesh = obj.data
        name = old_mesh.name
        obj.data = new_mesh
        obj.modifiers.clear()
        if old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)
        new_mesh.name = name  # gets a .001 suffix if the old mesh is still used elsewhere

        if applied:
            data_ops[obj].append(f"modifiers applied: {', '.join(applied)}")
        if dropped:
            data_ops[obj].append(f"viewport-disabled modifiers dropped: {', '.join(dropped)}")


def _bake_mesh(obj, world):
    """Push the world matrix into the mesh data so local space == world space."""
    ops = []
    if _is_identity(world):
        return ops

    users = obj.data.users
    if users > 1:
        # Linked duplicates / instances: bake into a private copy, not the shared mesh.
        obj.data = obj.data.copy()
        ops.append(f"made single-user copy (was shared by {users} users)")

    me = obj.data
    me.transform(world, shape_keys=True)
    ops.append("object transform baked into vertices"
               + (f" (incl. {len(me.shape_keys.key_blocks)} shape key(s))" if me.shape_keys else ""))
    if world.is_negative:
        # Mesh.transform doesn't fix winding for mirrored matrices; the viewport
        # was compensating for it, so do the same to keep normals facing out.
        me.flip_normals()
        ops.append("normals flipped (mirrored transform)")
    me.update()
    return ops


def freeze_geo(apply_modifiers=True, force=False):
    """
    Freezes transforms on the selected mesh objects: transforms, deltas and
    parent inverses are baked into the geometry so each mesh sits at an
    identity matrix, i.e. what you see is what Geometry Nodes gets.

    Only selected meshes are changed. A mesh is skipped entirely if modifiers
    would stay on its stack and freezing would change how they evaluate,
    unless force is set (the modifiers then stay on the stack, with a warning).
    Unselected children of frozen meshes keep their placement via their
    parent inverse, so their own transforms and animation are untouched.

    Returns (report_lines, has_warnings).
    """
    context = bpy.context
    selected = sorted(context.selected_objects, key=lambda o: o.name)
    if not selected:
        raise RuntimeError("Select one or more mesh objects.")

    lines_skipped = []
    candidates = []
    for obj in selected:
        if obj.type != 'MESH':
            lines_skipped.append(f"SKIPPED {obj.name}: not a mesh")
        elif obj.library or obj.override_library or obj.data.library:
            lines_skipped.append(f"SKIPPED {obj.name}: linked from a library")
        else:
            candidates.append(obj)

    depsgraph = context.evaluated_depsgraph_get()
    gn_instancers = {inst.parent.original for inst in depsgraph.object_instances
                     if inst.is_instance and inst.parent}

    # Modifiers never move objects, so world matrices can be snapshotted up front.
    world = {o: o.matrix_world.copy() for o in context.scene.objects}

    # Decide the frozen set: skip meshes whose leftover modifiers would evaluate differently.
    frozen = []
    skipped = {}
    forced = set()
    for obj in candidates:
        reason = _unappliable_reason(obj, apply_modifiers, gn_instancers)
        if reason and not _is_identity(world[obj]):
            if force:
                forced.add(obj)
                frozen.append(obj)
            else:
                skipped[obj] = reason
        else:
            frozen.append(obj)
    frozen_set = set(frozen)

    def keeps_parent(obj):
        return obj.parent in frozen_set and obj.parent_type == 'OBJECT'

    has_warnings = bool(skipped or forced)
    obj_ops = {o: [] for o in candidates}
    data_ops = {o: [] for o in candidates}

    for obj in frozen:
        anim = obj.animation_data
        if obj.constraints or (anim and (anim.action or anim.drivers)):
            obj_ops[obj].append("WARNING: constraints/animation/drivers may re-apply transforms")
            has_warnings = True
        obj_ops[obj] += [done for done, _ in
                         _describe_object(obj, will_unparent=obj.parent and not keeps_parent(obj))]

    for obj, reason in skipped.items():
        obj_ops[obj] = [f"SKIPPED {todo}" for _, todo in
                        _describe_object(obj, will_unparent=obj.parent and not keeps_parent(obj))]
        data_ops[obj] = [reason, "WARNING: modifiers still on the stack now evaluate in world space "
                                 f"and may look different: {', '.join(m.name for m in obj.modifiers)}"]

    # Unselected children of frozen meshes (and skipped meshes under them) must not move.
    adjusted = [c for o in frozen for c in o.children
                if c not in frozen_set and c.parent_type == 'OBJECT']

    if apply_modifiers:
        _apply_modifiers([o for o in frozen if o.modifiers and
                          not _unappliable_reason(o, apply_modifiers, gn_instancers)],
                         depsgraph, data_ops)

    for obj in frozen:
        if obj.modifiers:  # leftovers; unchanged unless forced (identity world otherwise)
            data_ops[obj].append(_unappliable_reason(obj, apply_modifiers, gn_instancers))
            if obj in forced:
                data_ops[obj].append("WARNING (Force): modifiers still on the stack now evaluate in "
                                     f"world space and may look different: "
                                     f"{', '.join(m.name for m in obj.modifiers)}")
        data_ops[obj] += _bake_mesh(obj, world[obj])

        if obj.parent and not keeps_parent(obj):
            obj.parent = None
        _clear_deltas(obj)
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_basis = Matrix.Identity(4)

    # The frozen parent's world is now identity; folding its old world into the child's
    # parent inverse keeps the child in place without touching its own transforms.
    for child in adjusted:
        child.matrix_parent_inverse = world[child.parent] @ child.matrix_parent_inverse

    context.view_layer.update()

    lines = []
    for obj in frozen:
        lines.append(f"Froze {obj.name}:")
        lines += [L1 + op for op in obj_ops[obj] or ["transforms already frozen"]]
        if data_ops[obj]:
            lines.append(f"{L2}Froze {obj.data.name} (mesh data):")
            lines += [L3 + op for op in data_ops[obj]]
    for obj in skipped:
        lines.append(f"SKIPPED {obj.name}:")
        lines += [L1 + op for op in obj_ops[obj]]
        lines.append(f"{L2}SKIPPED {obj.data.name} (mesh data):")
        lines += [L3 + op for op in data_ops[obj]]
    for child in adjusted:
        lines.append(f"Adjusted {child.name} ({child.type.lower()}, child of {child.parent.name}):")
        lines.append(f"{L1}parent inverse updated so it stays in place (own transforms untouched)")
    lines += lines_skipped

    print("\n".join(["Freeze Geo:"] + lines))
    return lines, has_warnings
