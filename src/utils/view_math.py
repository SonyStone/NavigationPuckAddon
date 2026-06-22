import mathutils
import bpy


def get_current_mouse_position(event: bpy.types.Event) -> mathutils.Vector:
    """Get the current mouse coordinates in the viewport."""
    return mathutils.Vector((event.mouse_region_x, event.mouse_region_y))


def event_drag_delta(event: bpy.types.Event) -> mathutils.Vector:
    """Return Blender drag delta using the add-on's view-operation convention."""
    return mathutils.Vector((event.mouse_prev_x - event.mouse_x, event.mouse_prev_y - event.mouse_y))


def get_viewport_center(context: bpy.types.Context) -> mathutils.Vector:
    """Get the center of the viewport."""
    region = context.region
    if region is None:
        return mathutils.Vector((0, 0))
    return mathutils.Vector((region.width / 2, region.height / 2))


def snap_to_nearest_angle(angle: float, initial_angle: float, snap_angle: float) -> float:
    """Snap an angle to the nearest specified angle increment."""
    return (round((angle + initial_angle) / snap_angle) * snap_angle) - initial_angle


def get_mouse_vector_to_center(
    context: bpy.types.Context,
    pointer_position: mathutils.Vector,
) -> mathutils.Vector:
    """Get the mouse position relative to the center of the viewport."""
    vector = pointer_position - get_viewport_center(context)
    if vector.length_squared > 1e-8:
        vector.normalize()
    return vector
