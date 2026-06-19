"""
Utility functions for the addon
"""

import math
import bpy
import mathutils

from .load_image import *
from .draw_handler import *


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


def get_mouse_vector_to_center(context: bpy.types.Context, pointer_position: mathutils.Vector) -> mathutils.Vector:
    """Get the mouse position relative to the center of the viewport"""

    viewport_center = get_viewport_center(context)
    vector = pointer_position - viewport_center
    vector.normalize()
    return vector

def add_modal_handler(context: bpy.types.Context, operator: bpy.types.Operator) -> bool:
    """Add a modal handler to the context"""
    if context.window_manager is not None:
        context.window_manager.modal_handler_add(operator)
        return True
    else:
        return False