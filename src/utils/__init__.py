"""
Utility functions for the addon
"""

import math
import typing
import bpy
import mathutils


def get_region_view3d(context: bpy.types.Context) -> bpy.types.RegionView3D:
    """Get the current RegionView3D"""
    space_data: typing.Any = context.space_data
    region_3d: bpy.types.RegionView3D = space_data.region_3d
    return region_3d


def get_current_view_rotation(context: bpy.types.Context) -> mathutils.Quaternion:
    """Get the current view rotation"""
    return get_region_view3d(context).view_rotation


def get_current_roll_angle(context: bpy.types.Context) -> float:
    """Calculate the roll angle of the current view.

    Determines roll as rotation around the view direction vector,
    measured relative to a "zero roll" reference orientation.
    Works for ANY view orientation including upside-down views.
    """
    rv3d = get_region_view3d(context)

    # Get view axes in world space
    view_matrix_inv = rv3d.view_matrix.inverted()
    view_up = view_matrix_inv.col[1].xyz.normalized()
    view_dir = -view_matrix_inv.col[2].xyz.normalized()  # View looks along -Z

    # Choose reference up vector (usually world Z)
    ref_up = mathutils.Vector((0, 0, 1))

    # If view is nearly aligned with Z axis, use Y as reference
    if abs(view_dir.dot(ref_up)) > 0.999:
        ref_up = mathutils.Vector((0, 1, 0))

    # Calculate the zero-roll up vector
    # (perpendicular to view_dir, in the plane containing view_dir and ref_up)
    zero_roll_up = ref_up - view_dir * ref_up.dot(view_dir)

    # Guard against numerical instability
    if zero_roll_up.length_squared < 1e-8:
        # Extremely rare case, try another reference
        ref_up = mathutils.Vector((1, 0, 0))
        zero_roll_up = ref_up - view_dir * ref_up.dot(view_dir)

    zero_roll_up.normalize()

    # Zero-roll right vector
    zero_roll_right = view_dir.cross(zero_roll_up)
    zero_roll_right.normalize()

    # Project actual view up onto the view plane
    view_up_proj = view_up - view_dir * view_up.dot(view_dir)

    # Guard against degenerate cases
    if view_up_proj.length_squared < 1e-8:
        return 0.0  # No meaningful roll if view up aligns with view dir

    view_up_proj.normalize()

    # Calculate angle between actual up and zero-roll up
    dot_product = view_up_proj.dot(zero_roll_up)
    # Clamp dot to avoid numerical errors
    dot_product = max(min(dot_product, 1.0), -1.0)
    angle = math.acos(dot_product)

    # Determine sign (positive if view_up is to the right of zero_roll_up)
    if view_up_proj.dot(zero_roll_right) > 0:
        angle = -angle

    return angle


def get_current_mouse_position(event: bpy.types.Event) -> mathutils.Vector:
    """Get the current mouse coordinates in the viewport"""
    return mathutils.Vector((event.mouse_region_x, event.mouse_region_y))


def get_viewport_center(context: bpy.types.Context) -> mathutils.Vector:
    """Get the center of the viewport"""
    region = context.region
    if region is None:
        return mathutils.Vector((0, 0))
    # context.area.width
    return mathutils.Vector((region.width / 2, region.height / 2))


def snap_to_nearest_angle(angle: float, initial_angle: float, snap_angle: float) -> float:
    """Snap an angle to the nearest specified angle increment."""
    return (round((angle + initial_angle) / snap_angle) * snap_angle) - initial_angle


def apply_view_roll(context: bpy.types.Context, rotation: mathutils.Quaternion,
                    angle: float) -> None:
    """Roll view by the angle
    Args:
        context: The Blender context.
        rotation: The initial view rotation as a quaternion.
        angle: The angle to roll the view by (in radians).
    """
    region_3d = get_region_view3d(context)

    rot = rotation.to_euler()
    rot.rotate_axis("Z", angle)
    region_3d.view_rotation = rot.to_quaternion()


def step_value(value: float, step: float) -> float:
    '''return the step closer to the passed value'''

    abs_angle = abs(value)
    diff = abs_angle % step
    lower_step = abs_angle - diff
    higher_step = lower_step + step
    if abs_angle - lower_step < higher_step - abs_angle:
        return math.copysign(lower_step, value)
    else:
        return math.copysign(higher_step, value)


def get_mouse_vector_to_center(context: bpy.types.Context, event: bpy.types.Event) -> mathutils.Vector:
    """Get the mouse position relative to the center of the viewport"""

    mouse_position = get_current_mouse_position(event)
    viewport_center = get_viewport_center(context)
    vector = mouse_position - viewport_center
    vector.normalize()
    return vector
