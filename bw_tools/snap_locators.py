import bpy

PREFIX = "loc_"


def snap_locators():
    """
    Creates a plain-axes Empty named "loc_<name>" for each selected object,
    linked to the scene's root collection, unparented, and matching the
    object's world transform. Returns the created empties.
    """
    context = bpy.context
    sources = list(context.selected_objects)

    if not sources:
        raise RuntimeError("No objects selected.")

    # Make sure matrix_world reflects constraints, drivers and parenting.
    context.view_layer.update()

    root = context.scene.collection
    created = []
    for src in sources:
        empty = bpy.data.objects.new(PREFIX + src.name, None)
        empty.empty_display_type = 'PLAIN_AXES'
        empty.rotation_mode = src.rotation_mode
        root.objects.link(empty)
        empty.matrix_world = src.matrix_world.copy()
        created.append(empty)

    # Select the new locators so the result is easy to see.
    for obj in sources:
        obj.select_set(False)
    for empty in created:
        empty.select_set(True)
    context.view_layer.objects.active = created[-1]

    print(f"Snapped {len(created)} locator(s): {', '.join(e.name for e in created)}")
    return created
