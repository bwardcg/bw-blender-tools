import bpy
from mathutils import Matrix


def _collect_hierarchy(roots):
    """Selected objects plus every descendant, so freezing a parent never drags its children."""
    result = []
    seen = set()
    stack = list(roots)
    while stack:
        obj = stack.pop()
        if obj in seen:
            continue
        seen.add(obj)
        result.append(obj)
        stack.extend(obj.children)
    return result


def _is_identity_node(obj):
    """
    Should this object collapse to an identity world matrix?

    Meshes always do (their transform gets baked into the vertices).
    Everything else either collapses too (and loses its placement) or keeps
    its world transform and simply gets re-expressed under a cleaned-up parent.
    """
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


def _clear_deltas(obj):
    obj.delta_location = (0.0, 0.0, 0.0)
    obj.delta_rotation_euler = (0.0, 0.0, 0.0)
    obj.delta_rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    obj.delta_scale = (1.0, 1.0, 1.0)


def _bake_mesh(obj, world):
    """Push the world matrix into the mesh data so local space == world space."""
    if obj.data.users > 1:
        # Linked duplicates / instances: bake into a private copy, not the shared mesh.
        obj.data = obj.data.copy()

    me = obj.data
    me.transform(world, shape_keys=True)
    if world.is_negative:
        # Mesh.transform doesn't fix winding for mirrored matrices; the viewport
        # was compensating for it, so do the same to keep normals facing out.
        me.flip_normals()
    me.update()


def freeze_geo():
    """
    Freezes transforms on the selected objects and everything under them:
    mesh transforms, deltas and parent inverses are baked into the geometry
    so each mesh sits at an identity matrix, i.e. what you see is what
    Geometry Nodes (Object Info, Original space, etc.) gets.
    """
    context = bpy.context
    selected = list(context.selected_objects)
    roots = _valid_roots(selected)
    if not roots:
        raise RuntimeError("Select a mesh, or a group (empty) containing meshes.")
    skipped = [o.name for o in selected if o not in roots]
    if skipped:
        print(f"Freeze Geo: skipping non-mesh selection: {', '.join(skipped)}")

    objects = [o for o in _collect_hierarchy(roots)
               if o.library is None and o.override_library is None]
    if not objects:
        raise RuntimeError("Selection is linked library data; nothing to freeze.")

    # Snapshot everything before touching anything; parent chains go stale mid-edit.
    world = {o: o.matrix_world.copy() for o in objects}
    identity = {o for o in objects if _is_identity_node(o)}

    warnings = []
    for obj in objects:
        if obj.constraints or (obj.animation_data and
                               (obj.animation_data.action or obj.animation_data.drivers)):
            warnings.append(obj.name)

    # Pass 1: bake meshes and collapse identity nodes.
    frozen_meshes = 0
    for obj in objects:
        if obj not in identity:
            continue

        if obj.type == 'MESH' and obj.data.library is None:
            _bake_mesh(obj, world[obj])
            frozen_meshes += 1

        # Only stay parented if the parent also ends up at identity via a plain
        # object parent; otherwise the local matrix couldn't be identity.
        if obj.parent and not (obj.parent in identity and obj.parent_type == 'OBJECT'):
            obj.parent = None

        _clear_deltas(obj)
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_basis = Matrix.Identity(4)

    context.view_layer.update()

    # Pass 2: everything else keeps its world placement under the new parents.
    for obj in objects:
        if obj in identity:
            continue
        if obj.parent in identity:
            obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_world = world[obj]

    context.view_layer.update()

    print(f"Freeze Geo: baked {frozen_meshes} mesh(es), "
          f"{len(identity)} object(s) set to identity, "
          f"{len(objects) - len(identity)} object(s) kept in place.")
    if warnings:
        print("Freeze Geo: these have constraints/animation/drivers that may re-apply "
              f"transforms: {', '.join(warnings)}")

    return frozen_meshes, skipped, warnings
