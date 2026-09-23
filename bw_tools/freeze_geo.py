import math

import bpy
from mathutils import Matrix, Quaternion, Vector

EPS = 1e-6
L1 = "..  "
L2 = "..  ..  "
L3 = "..  ..  ..  "


def _collect_hierarchy(roots):
    """Selected objects plus every descendant (depth-first), so freezing a parent never drags its children."""
    result = []
    seen = set()

    def visit(obj):
        if obj in seen:
            return
        seen.add(obj)
        result.append(obj)
        for child in obj.children:
            visit(child)

    for root in roots:
        visit(root)
    return result


def _is_identity_node(obj):
    """Objects that collapse to an identity world matrix; everything else keeps its world placement."""
    if obj.type == 'MESH':
        return True
    # Plain empties are Maya-style group transforms: zero them so the hierarchy
    # survives. Collection-instance empties ARE their visible geometry, so they stay put.
    return obj.type == 'EMPTY' and obj.instance_type == 'NONE'


def _contains_mesh(obj):
    return obj.type == 'MESH' or any(c.type == 'MESH' for c in obj.children_recursive)


def _valid_roots(selected):
    """Mesh objects, or group empties with at least one mesh somewhere beneath them."""
    return [o for o in selected
            if (o.type == 'MESH' or (o.type == 'EMPTY' and o.instance_type == 'NONE'))
            and _contains_mesh(o)]


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


def _describe_transforms(obj):
    ops = []
    if obj.location.length > EPS:
        ops.append(f"location applied {_fmt(obj.location)}")
    rot = _rotation_quat(obj)
    if rot.angle > EPS:
        ops.append(f"rotation applied {_fmt(_degrees(rot))} deg")
    if (Vector(obj.scale) - Vector((1, 1, 1))).length > EPS:
        ops.append(f"scale applied {_fmt(obj.scale)}")
    return ops


def _describe_deltas(obj):
    ops = []
    if obj.delta_location.length > EPS:
        ops.append(f"delta location removed {_fmt(obj.delta_location)}")
    rot = _rotation_quat(obj, delta=True)
    if rot.angle > EPS:
        ops.append(f"delta rotation removed {_fmt(_degrees(rot))} deg")
    if (Vector(obj.delta_scale) - Vector((1, 1, 1))).length > EPS:
        ops.append(f"delta scale removed {_fmt(obj.delta_scale)}")
    return ops


def _clear_deltas(obj):
    obj.delta_location = (0.0, 0.0, 0.0)
    obj.delta_rotation_euler = (0.0, 0.0, 0.0)
    obj.delta_rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    obj.delta_scale = (1.0, 1.0, 1.0)


def _apply_modifiers(objects, context, data_ops):
    """
    Replace each object's mesh with its viewport-evaluated result and clear the stack.
    All results are evaluated up front so modifiers that reference other objects
    (booleans, mirror targets...) see the scene as it was before anything changed.
    """
    depsgraph = context.evaluated_depsgraph_get()
    gn_instancers = {inst.parent.original for inst in depsgraph.object_instances
                     if inst.is_instance and inst.parent}

    evaluated = {}
    for obj in objects:
        names = ", ".join(m.name for m in obj.modifiers)
        if obj.data.shape_keys:
            data_ops[obj].append(f"modifiers NOT applied, mesh has shape keys: {names}")
            continue
        if obj in gn_instancers and obj.instance_type == 'NONE':
            # new_from_object only keeps real mesh; instances would silently vanish.
            data_ops[obj].append(f"modifiers NOT applied, Geometry Nodes output has instances "
                                 f"(add Realize Instances): {names}")
            continue
        evaluated[obj] = bpy.data.meshes.new_from_object(
            obj.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph)

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


def freeze_geo(apply_modifiers=True):
    """
    Freezes transforms on the selected objects and everything under them:
    mesh transforms, deltas and parent inverses are baked into the geometry
    so each mesh sits at an identity matrix, i.e. what you see is what
    Geometry Nodes (Object Info, Original space, etc.) gets.

    Returns (report_lines, has_warnings).
    """
    context = bpy.context
    selected = list(context.selected_objects)
    roots = _valid_roots(selected)
    if not roots:
        raise RuntimeError("Select a mesh, or a group (empty) containing meshes.")
    skipped = [o.name for o in selected if o not in roots]

    objects = [o for o in _collect_hierarchy(roots)
               if o.library is None and o.override_library is None]
    if not objects:
        raise RuntimeError("Selection is linked library data; nothing to freeze.")

    obj_ops = {o: [] for o in objects}
    data_ops = {o: [] for o in objects}

    has_warnings = False
    for obj in objects:
        anim = obj.animation_data
        if obj.constraints or (anim and (anim.action or anim.drivers)):
            obj_ops[obj].append("WARNING: constraints/animation/drivers may re-apply transforms")
            has_warnings = True

    if apply_modifiers:
        _apply_modifiers([o for o in objects if o.type == 'MESH' and o.modifiers], context, data_ops)

    # Snapshot after modifiers (they don't move objects) but before any transform edits;
    # parent chains go stale mid-edit.
    world = {o: o.matrix_world.copy() for o in objects}
    identity = {o for o in objects if _is_identity_node(o)}

    # Pass 1: bake meshes and collapse identity nodes.
    for obj in objects:
        if obj not in identity:
            continue
        ops = obj_ops[obj]
        ops += _describe_transforms(obj)
        ops += _describe_deltas(obj)
        if not _is_identity(obj.matrix_parent_inverse):
            ops.append("parent inverse removed")

        if obj.type == 'MESH' and obj.data.library is None:
            data_ops[obj] += _bake_mesh(obj, world[obj])
            if obj.modifiers and not _is_identity(world[obj]):
                # Modifier settings (bevel width, solidify thickness, mirror axis...) are
                # in object space, which just changed under them.
                data_ops[obj].append("WARNING: modifiers still on the stack now evaluate in world "
                                     f"space and may look different: "
                                     f"{', '.join(m.name for m in obj.modifiers)}")
                has_warnings = True

        # Only stay parented if the parent also ends up at identity via a plain
        # object parent; otherwise the local matrix couldn't be identity.
        if obj.parent and not (obj.parent in identity and obj.parent_type == 'OBJECT'):
            ops.append(f"unparented from {obj.parent.name} (world placement baked in)")
            obj.parent = None

        _clear_deltas(obj)
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_basis = Matrix.Identity(4)

    context.view_layer.update()

    # Pass 2: everything else keeps its world placement under the new parents.
    for obj in objects:
        if obj in identity:
            continue
        before = obj.matrix_basis.copy()
        if obj.parent in identity and not _is_identity(obj.matrix_parent_inverse):
            obj.matrix_parent_inverse = Matrix.Identity(4)
            obj_ops[obj].append("parent inverse removed")
        obj.matrix_world = world[obj]
        if any(abs(a - b) > EPS for ra, rb in zip(before, obj.matrix_basis) for a, b in zip(ra, rb)):
            obj_ops[obj].append("local transform recomputed to keep world placement")

    context.view_layer.update()

    lines = []
    for obj in objects:
        if obj in identity:
            lines.append(f"Froze {obj.name}:")
            lines += [L1 + op for op in obj_ops[obj] or ["transforms already frozen"]]
        elif obj_ops[obj]:
            lines.append(f"Kept {obj.name} ({obj.type.lower()}, world placement preserved):")
            lines += [L1 + op for op in obj_ops[obj]]
        if data_ops[obj]:
            lines.append(f"{L2}Froze {obj.data.name} (mesh data):")
            lines += [L3 + op for op in data_ops[obj]]
    for name in skipped:
        lines.append(f"Skipped {name}: not a mesh or a group containing meshes")

    print("\n".join(["Freeze Geo:"] + lines))
    return lines, has_warnings
