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
    if vector.length_squared > 1e-8:
        vector.normalize()
    return vector


def _required_modal_context_members(context: bpy.types.Context) -> tuple[object | None, ...]:
    return (
        context.window_manager,
        context.window,
        context.screen,
        context.area,
    )


def _has_window_region(context: bpy.types.Context) -> bool:
    return context.region is not None and context.region.type == 'WINDOW'


def _can_add_modal_handler(context: bpy.types.Context) -> bool:
    return all(member is not None for member in _required_modal_context_members(context)) and _has_window_region(context)


def add_modal_handler(context: bpy.types.Context, operator: bpy.types.Operator) -> bool:
    """Add a modal handler to the context"""
    if not _can_add_modal_handler(context):
        return False

    try:
        context.window_manager.modal_handler_add(operator)
    except (ReferenceError, RuntimeError, TypeError):
        return False

    return True
