import typing
import bpy
import mathutils

from ..utils import get_current_mouse_position, get_mouse_vector_to_center
from .view_handlers import ViewHandler, apply_angle_snapping, apply_view_orbit, apply_view_pan, apply_view_roll, apply_view_zoom

class ViewOperationHandler:
    """Tracks active pan, orbit, zoom, and roll gestures."""

    def __init__(self):
        self.is_active = False
        self.start_mouse_pos = mathutils.Vector((0, 0))

    def apply(self, mouse_pos: mathutils.Vector | None = None):
        """Apply the operation delta to the view"""
        self.is_active = True
        if mouse_pos is None:
            mouse_pos = mathutils.Vector((0, 0))
        self.start_mouse_pos[:] = mouse_pos

    def event_handler(self, event: bpy.types.Event) -> bool | typing.Literal["DO_SOMETHING"]:
        """Handle operation events"""
        if self.is_active:
            if event.type == 'MOUSEMOVE':
                self.is_active = True
            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                self.is_active = False
            return True
        return False


class ViewPan:
    """Handles panning the view"""

    def __init__(self):
        self.view_op = ViewOperationHandler()

    def apply(self, context: bpy.types.Context, delta: mathutils.Vector, mouse_pos: mathutils.Vector | None = None):
        """Apply the pan delta to the view"""
        self.view_op.apply(mouse_pos)
        apply_view_pan(context, delta)

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> bool:
        """Handle pan events"""

        self.view_op.event_handler(event)

        if self.view_op.is_active:
            apply_view_pan(context, mathutils.Vector(
                (event.mouse_prev_x - event.mouse_x, event.mouse_prev_y - event.mouse_y)))
            return True

        return False


class ViewOrbit:
    """Handles orbiting the view"""

    def __init__(self):
        self.view_op = ViewOperationHandler()

    def apply(self, context: bpy.types.Context, delta: mathutils.Vector, mouse_pos: mathutils.Vector | None = None, shift: bool = False):
        """Apply the orbit delta to the view"""
        self.view_op.apply(mouse_pos)
        apply_view_orbit(context, delta, shift)

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> bool:
        """Handle orbit events"""

        self.view_op.event_handler(event)

        if self.view_op.is_active:
            apply_view_orbit(context, mathutils.Vector(
                (event.mouse_prev_x - event.mouse_x, event.mouse_prev_y - event.mouse_y)), shift=event.shift)
            return True

        return False


class ViewZoom:
    """Handles zooming the view"""

    def __init__(self):
        self.view_op = ViewOperationHandler()

    def apply(self, context: bpy.types.Context, delta: mathutils.Vector, mouse_pos: mathutils.Vector | None = None):
        """Apply the zoom delta to the view"""
        self.view_op.apply(mouse_pos)
        zoom_delta = delta.y * 0.02
        apply_view_zoom(context, zoom_delta)

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> bool:
        """Handle zoom events"""

        self.view_op.event_handler(event)

        if self.view_op.is_active:
            zoom_delta = (event.mouse_prev_y - event.mouse_y) * 0.02
            apply_view_zoom(context, zoom_delta)
            return True

        return False


class ViewRoll:
    """Handles rolling the view"""

    def __init__(self):
        self.view_op = ViewOperationHandler()
        self.rotation: typing.Optional[mathutils.Quaternion] = None
        self.initial_angle: float = 0.0
        self.initial_vector: mathutils.Vector | None = None

    def apply(
        self,
        context: bpy.types.Context,
        mouse_pos: mathutils.Vector | None = None,
        pointer_offset: mathutils.Vector | None = None
    ):
        """Apply the roll delta to the view"""
        if mouse_pos is None:
            mouse_pos = mathutils.Vector((0, 0))
        if pointer_offset is None:
            pointer_offset = mathutils.Vector((0, 0))

        self.view_op.apply(pointer_offset)

        self.rotation = ViewHandler.get_current_view_rotation(context).copy()
        self.initial_angle = ViewHandler.get_current_roll_angle(context)
        self.initial_vector = get_mouse_vector_to_center(context, mouse_pos)

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> bool:
        """Handle roll events"""

        self.view_op.event_handler(event)

        if self.view_op.is_active:
            if self.initial_vector is None or self.rotation is None:
                return False
            pointer_position = get_current_mouse_position(event)
            current_vector = get_mouse_vector_to_center(
                context, pointer_position)
            delta_angle = self.initial_vector.angle_signed(current_vector)
            delta_angle = apply_angle_snapping(
                delta_angle, self.initial_angle, event.shift)
            apply_view_roll(context, self.rotation, delta_angle)
            return True

        return False
