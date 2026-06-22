import typing
import bpy
import mathutils

from ..utils.view_math import event_drag_delta, get_current_mouse_position, get_mouse_vector_to_center
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

    def update_from_event(self, event: bpy.types.Event) -> bool:
        """Update active state and return whether the operation should keep handling input."""
        if not self.is_active:
            return False

        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.is_active = False

        return self.is_active


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

        if not self.view_op.update_from_event(event):
            return False

        apply_view_pan(context, event_drag_delta(event))
        return True


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

        if not self.view_op.update_from_event(event):
            return False

        apply_view_orbit(context, event_drag_delta(event), shift=event.shift)
        return True


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

        if not self.view_op.update_from_event(event):
            return False

        zoom_delta = event_drag_delta(event).y * 0.02
        apply_view_zoom(context, zoom_delta)
        return True


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
        if not self.view_op.update_from_event(event):
            return False

        self._apply_pan(context, event_drag_delta(event))
        return True

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
        if not self.view_op.update_from_event(event):
            return False

        self._apply_zoom(context, event_drag_delta(event))
        return True

    def _image_zoom_factor(self, delta_y: float) -> float:
        return 1.0 + min(
            abs(float(delta_y)) * self.zoom_factor_scale * UV_IMAGE_ZOOM_SPEED_FACTOR,
            0.035 * UV_IMAGE_ZOOM_SPEED_FACTOR,
        )

    def _view2d_zoom_factor(self, delta_y: float) -> float:
        return 1.0 + min(abs(float(delta_y)) * self.zoom_factor_scale, 0.035)

    def _apply_image_zoom(self, delta_y: float) -> None:
        factor = self._image_zoom_factor(delta_y)
        if delta_y < 0.0:
            bpy.ops.image.view_zoom(factor=factor, use_cursor_init=False)
        elif delta_y > 0.0:
            bpy.ops.image.view_zoom(factor=1.0 / factor, use_cursor_init=False)

    def _apply_view2d_zoom(self, delta_y: float) -> None:
        factor = self._view2d_zoom_factor(delta_y)
        if delta_y < 0.0:
            bpy.ops.view2d.zoom_in(zoomfacx=factor, zoomfacy=factor)
        elif delta_y > 0.0:
            bpy.ops.view2d.zoom_out(zoomfacx=factor, zoomfacy=factor)

    def _apply_zoom(self, context: bpy.types.Context, delta: mathutils.Vector) -> None:
        try:
            if is_image_editor(context):
                self._apply_image_zoom(delta.y)
                return

            self._apply_view2d_zoom(delta.y)
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

    def _current_roll_vector(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> mathutils.Vector | None:
        pointer_position = get_current_mouse_position(event)
        current_vector = get_mouse_vector_to_center(context, pointer_position)
        if current_vector.length_squared <= 1e-8:
            return None
        return current_vector

    def _roll_delta_angle(self, current_vector: mathutils.Vector, shift: bool) -> float:
        delta_angle = self.initial_vector.angle_signed(current_vector)
        return apply_angle_snapping(delta_angle, self.initial_angle, shift)

    def _apply_roll_delta(self, context: bpy.types.Context, delta_angle: float) -> bool:
        if CameraHandler.is_camera_view_locked(context):
            if self.camera_rotation is None:
                return False
            apply_camera_roll(context, self.camera_rotation, delta_angle)
            return True

        if self.rotation is None:
            return False
        apply_view_roll(context, self.rotation, delta_angle)
        return True

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> bool:
        """Handle roll events"""
        if not self.view_op.update_from_event(event):
            return False

        if self.initial_vector is None or self.initial_vector.length_squared <= 1e-8:
            return False

        current_vector = self._current_roll_vector(context, event)
        if current_vector is None:
            return False

        delta_angle = self._roll_delta_angle(current_vector, event.shift)
        return self._apply_roll_delta(context, delta_angle)


class ViewOperationSet:
    """Owns the 3D and 2D view operation handlers for a puck instance."""

    def __init__(self) -> None:
        self.view_pan = ViewPan()
        self.view_orbit = ViewOrbit()
        self.view_zoom = ViewZoom()
        self.view_roll = ViewRoll()
        self.view2d_pan = View2DPan()
        self.view2d_zoom = View2DZoom()

    def handlers(self, is_view2d_editor: bool) -> tuple[typing.Any, ...]:
        if is_view2d_editor:
            return (self.view2d_pan, self.view2d_zoom)
        return self.view_3d_handlers()

    def view_3d_handlers(self) -> tuple[typing.Any, ...]:
        return (self.view_pan, self.view_orbit, self.view_zoom, self.view_roll)

    def pan(self, is_view2d_editor: bool) -> typing.Any:
        return self.view2d_pan if is_view2d_editor else self.view_pan

    def zoom(self, is_view2d_editor: bool) -> typing.Any:
        return self.view2d_zoom if is_view2d_editor else self.view_zoom

    def action_handler(self, action: str, is_view2d_editor: bool) -> typing.Any | None:
        if action == "pan":
            return self.pan(is_view2d_editor)
        if action == "orbit":
            return self.view_orbit
        if action == "zoom":
            return self.zoom(is_view2d_editor)
        if action == "roll":
            return self.view_roll
        return None

    def action_start_mouse_pos(self, action: str, is_view2d_editor: bool) -> mathutils.Vector | None:
        handler = self.action_handler(action, is_view2d_editor)
        if handler is None:
            return None
        return handler.view_op.start_mouse_pos

    def apply_action(
        self,
        context: bpy.types.Context,
        action: str,
        delta: mathutils.Vector,
        pointer_position: mathutils.Vector,
        pointer_offset: mathutils.Vector,
        is_view2d_editor: bool,
        *,
        shift: bool = False,
    ) -> bool:
        if action == "roll":
            self.view_roll.apply(context, pointer_position, pointer_offset)
            return True

        handler = self.action_handler(action, is_view2d_editor)
        if handler is None:
            return False

        if action == "orbit":
            handler.apply(context, delta, pointer_offset, shift)
        else:
            handler.apply(context, delta, pointer_offset)
        return True

    def any_active(self, is_view2d_editor: bool) -> bool:
        return any(handler.view_op.is_active for handler in self.handlers(is_view2d_editor))

    def cancel(self, is_view2d_editor: bool) -> None:
        for handler in self.handlers(is_view2d_editor):
            handler.view_op.is_active = False
