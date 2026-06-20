import typing
import bpy
import mathutils

from ..utils import get_current_mouse_position, get_mouse_vector_to_center
from .view_handlers import (
    CameraHandler,
    ViewHandler,
    apply_angle_snapping,
    apply_camera_roll,
    apply_view_orbit,
    apply_view_pan,
    apply_view_roll,
    apply_view_zoom,
)


def ui_pixel_scale(context: bpy.types.Context) -> float:
    """Return the UI-to-framebuffer pixel scale used by View2D operators."""
    system_preferences = getattr(context.preferences, "system", None)
    if system_preferences is None:
        return 1.0

    return max(
        float(getattr(system_preferences, "pixel_size", 1.0)),
        float(getattr(system_preferences, "ui_scale", 1.0)),
        1.0,
    )


UV_IMAGE_PAN_SPEED_FACTOR = 100.0
UV_IMAGE_ZOOM_SPEED_FACTOR = 2.75


def is_image_editor(context: bpy.types.Context) -> bool:
    return bool(context.area and context.area.type == 'IMAGE_EDITOR')


def image_editor_pan_offset(context: bpy.types.Context, delta: mathutils.Vector) -> tuple[float, float]:
    space_data = getattr(context, "space_data", None)
    zoom_percent = max(float(getattr(space_data, "zoom_percentage", 100.0)), 1.0)
    zoom = zoom_percent / 100.0
    scale = ui_pixel_scale(context)
    pixels_per_pan_unit = 100.0 * zoom

    return (
        float(delta.x) * scale * UV_IMAGE_PAN_SPEED_FACTOR / pixels_per_pan_unit,
        float(delta.y) * scale * UV_IMAGE_PAN_SPEED_FACTOR / pixels_per_pan_unit,
    )


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


class View2DPan:
    """Handles panning View2D-based editors such as Image, UV, and Node editors."""

    def __init__(self):
        self.view_op = ViewOperationHandler()
        self.pan_remainder = mathutils.Vector((0.0, 0.0))
        self.pan_scale = 1.0

    def apply(self, context: bpy.types.Context, delta: mathutils.Vector, mouse_pos: mathutils.Vector | None = None):
        """Apply the 2D pan delta to the editor view."""
        self.view_op.apply(mouse_pos)
        self._apply_pan(context, delta)

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> bool:
        """Handle 2D pan events."""
        self.view_op.event_handler(event)

        if self.view_op.is_active:
            self._apply_pan(context, mathutils.Vector((event.mouse_prev_x - event.mouse_x, event.mouse_prev_y - event.mouse_y)))
            return True

        return False

    def _apply_pan(self, context: bpy.types.Context, delta: mathutils.Vector) -> None:
        try:
            if is_image_editor(context):
                bpy.ops.image.view_pan(offset=image_editor_pan_offset(context, delta))
                return

            pan_delta = (delta * self.pan_scale * ui_pixel_scale(context)) + self.pan_remainder
            deltax = int(pan_delta.x)
            deltay = int(pan_delta.y)
            self.pan_remainder[:] = (pan_delta.x - deltax, pan_delta.y - deltay)
            if deltax == 0 and deltay == 0:
                return
            bpy.ops.view2d.pan(deltax=deltax, deltay=deltay)
        except (TypeError, RuntimeError):
            self.view_op.is_active = False


class View2DZoom:
    """Handles zooming View2D-based editors such as Image, UV, and Node editors."""

    def __init__(self):
        self.view_op = ViewOperationHandler()
        self.zoom_factor_scale = 0.0025

    def apply(self, context: bpy.types.Context, delta: mathutils.Vector, mouse_pos: mathutils.Vector | None = None):
        """Apply the 2D zoom delta to the editor view."""
        self.view_op.apply(mouse_pos)
        self._apply_zoom(context, delta)

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> bool:
        """Handle 2D zoom events."""
        self.view_op.event_handler(event)

        if self.view_op.is_active:
            self._apply_zoom(context, mathutils.Vector((event.mouse_prev_x - event.mouse_x, event.mouse_prev_y - event.mouse_y)))
            return True

        return False

    def _apply_zoom(self, context: bpy.types.Context, delta: mathutils.Vector) -> None:
        try:
            if is_image_editor(context):
                factor = 1.0 + min(
                    abs(float(delta.y)) * self.zoom_factor_scale * UV_IMAGE_ZOOM_SPEED_FACTOR,
                    0.035 * UV_IMAGE_ZOOM_SPEED_FACTOR,
                )
                if delta.y < 0.0:
                    bpy.ops.image.view_zoom(factor=factor, use_cursor_init=False)
                elif delta.y > 0.0:
                    bpy.ops.image.view_zoom(factor=1.0 / factor, use_cursor_init=False)
                return

            factor = 1.0 + min(abs(float(delta.y)) * self.zoom_factor_scale, 0.035)
            if delta.y < 0.0:
                bpy.ops.view2d.zoom_in(zoomfacx=factor, zoomfacy=factor)
            elif delta.y > 0.0:
                bpy.ops.view2d.zoom_out(zoomfacx=factor, zoomfacy=factor)
        except (TypeError, RuntimeError):
            self.view_op.is_active = False


class ViewRoll:
    """Handles rolling the view"""

    def __init__(self):
        self.view_op = ViewOperationHandler()
        self.rotation: typing.Optional[mathutils.Quaternion] = None
        self.camera_rotation: typing.Optional[mathutils.Euler] = None
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

        self.rotation = None
        self.camera_rotation = None
        if CameraHandler.is_camera_view_locked(context):
            camera = CameraHandler.get_camera_object(context)
            if camera:
                self.camera_rotation = camera.rotation_euler.copy()
        else:
            self.rotation = ViewHandler.get_current_view_rotation(context).copy()
        self.initial_angle = ViewHandler.get_current_roll_angle(context)
        self.initial_vector = get_mouse_vector_to_center(context, mouse_pos)

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> bool:
        """Handle roll events"""

        self.view_op.event_handler(event)

        if self.view_op.is_active:
            if self.initial_vector is None or self.initial_vector.length_squared <= 1e-8:
                return False
            pointer_position = get_current_mouse_position(event)
            current_vector = get_mouse_vector_to_center(
                context, pointer_position)
            if current_vector.length_squared <= 1e-8:
                return False

            delta_angle = self.initial_vector.angle_signed(current_vector)
            delta_angle = apply_angle_snapping(
                delta_angle, self.initial_angle, event.shift)
            if CameraHandler.is_camera_view_locked(context):
                if self.camera_rotation is None:
                    return False
                apply_camera_roll(context, self.camera_rotation, delta_angle)
            else:
                if self.rotation is None:
                    return False
                apply_view_roll(context, self.rotation, delta_angle)
            return True

        return False
