"""
View manipulation handlers for panning, rolling, zooming, and orbiting the view.
Handles both regular view and camera view modes.
"""

import math
import typing
import bpy
import mathutils

from ..utils import get_current_mouse_position, get_mouse_vector_to_center, snap_to_nearest_angle

# Common utility functions


def apply_angle_snapping(delta_angle: float, initial_angle: float, shift: bool, snap_angle: float = math.radians(15.0)) -> float:
    """Apply angle snapping if shift is pressed"""
    if shift:
        return snap_to_nearest_angle(delta_angle, initial_angle, snap_angle)
    return delta_angle


def get_pan_vectors_and_factor(context: bpy.types.Context):
    """Get common pan calculation vectors and factor"""
    rv3d = ViewHandler.get_region_view3d(context)
    view_matrix_inv = rv3d.view_matrix.inverted()

    right = view_matrix_inv.col[0].xyz
    up = view_matrix_inv.col[1].xyz
    region_width = context.region.width if context.region is not None else 0
    pan_factor = rv3d.view_distance / region_width

    return right, up, pan_factor


class CameraHandler:
    """Handler for camera operations"""

    @staticmethod
    def get_camera_object(context: bpy.types.Context) -> bpy.types.Object:
        """Get the active camera object"""
        return context.scene.camera  # type: ignore

    @staticmethod
    def is_camera_view_locked(context: bpy.types.Context) -> bool:
        """Check if we're in camera view and camera is locked to view"""
        rv3d = ViewHandler.get_region_view3d(context)
        return rv3d.view_perspective == 'CAMERA' and context.space_data.lock_camera  # type: ignore

    @staticmethod
    def is_camera_view(context: bpy.types.Context) -> bool:
        """Check if the 3D View is currently looking through the camera."""
        return ViewHandler.get_region_view3d(context).view_perspective == 'CAMERA'


class ViewHandler:
    """Handler for view operations"""
    @staticmethod
    def get_region_view3d(context: bpy.types.Context) -> bpy.types.RegionView3D:
        """Get the current RegionView3D"""
        region_data = getattr(context, "region_data", None)
        if region_data is not None and hasattr(region_data, "view_matrix"):
            return region_data

        space_data: typing.Any = context.space_data
        region_3d: bpy.types.RegionView3D = space_data.region_3d
        return region_3d

    @staticmethod
    def get_current_view_rotation(context: bpy.types.Context) -> mathutils.Quaternion:
        """Get the current view rotation"""
        return ViewHandler.get_region_view3d(context).view_rotation

    @staticmethod
    def _view_up_and_direction(rv3d: bpy.types.RegionView3D) -> tuple[mathutils.Vector, mathutils.Vector]:
        view_matrix_inv = rv3d.view_matrix.inverted()
        view_up = view_matrix_inv.col[1].xyz.normalized()
        view_dir = -view_matrix_inv.col[2].xyz.normalized()
        return view_up, view_dir

    @staticmethod
    def _reference_up_for_direction(view_dir: mathutils.Vector) -> mathutils.Vector:
        ref_up = mathutils.Vector((0, 0, 1))
        if abs(view_dir.dot(ref_up)) > 0.999:
            return mathutils.Vector((0, 1, 0))
        return ref_up

    @staticmethod
    def _project_onto_view_plane(ref_up: mathutils.Vector, view_dir: mathutils.Vector) -> mathutils.Vector:
        return ref_up - view_dir * ref_up.dot(view_dir)

    @staticmethod
    def _zero_roll_basis(view_dir: mathutils.Vector) -> tuple[mathutils.Vector, mathutils.Vector]:
        ref_up = ViewHandler._reference_up_for_direction(view_dir)
        zero_roll_up = ref_up - view_dir * ref_up.dot(view_dir)

        if zero_roll_up.length_squared < 1e-8:
            ref_up = mathutils.Vector((1, 0, 0))
            zero_roll_up = ref_up - view_dir * ref_up.dot(view_dir)

        zero_roll_up.normalize()
        zero_roll_right = view_dir.cross(zero_roll_up)
        zero_roll_right.normalize()
        return zero_roll_up, zero_roll_right

    @staticmethod
    def _projected_view_up(view_up: mathutils.Vector, view_dir: mathutils.Vector) -> mathutils.Vector | None:
        view_up_proj = ViewHandler._project_onto_view_plane(view_up, view_dir)
        if view_up_proj.length_squared < 1e-8:
            return None

        view_up_proj.normalize()
        return view_up_proj

    @staticmethod
    def _signed_roll_angle(
        view_up_proj: mathutils.Vector,
        zero_roll_up: mathutils.Vector,
        zero_roll_right: mathutils.Vector,
    ) -> float:
        dot_product = max(min(view_up_proj.dot(zero_roll_up), 1.0), -1.0)
        angle = math.acos(dot_product)
        if view_up_proj.dot(zero_roll_right) > 0:
            angle = -angle
        return angle

    @staticmethod
    def get_current_roll_angle(context: bpy.types.Context) -> float:
        """Calculate the roll angle of the current view."""
        rv3d = ViewHandler.get_region_view3d(context)
        view_up, view_dir = ViewHandler._view_up_and_direction(rv3d)
        zero_roll_up, zero_roll_right = ViewHandler._zero_roll_basis(view_dir)
        view_up_proj = ViewHandler._projected_view_up(view_up, view_dir)
        if view_up_proj is None:
            return 0.0
        return ViewHandler._signed_roll_angle(view_up_proj, zero_roll_up, zero_roll_right)

# Roll handler functions


def apply_view_roll(context: bpy.types.Context, initial_rotation: mathutils.Quaternion, delta_angle: float) -> None:
    """Apply roll to the view"""
    region_3d = ViewHandler.get_region_view3d(context)
    rot = initial_rotation.to_euler()
    rot.rotate_axis("Z", delta_angle)  # type: ignore
    region_3d.view_rotation = rot.to_quaternion()


def apply_camera_roll(context: bpy.types.Context, initial_rotation: mathutils.Euler, delta_angle: float) -> None:
    """Apply roll to the camera"""
    camera = CameraHandler.get_camera_object(context)
    if camera:
        initial_quat = initial_rotation.to_quaternion()
        initial_matrix = initial_quat.to_matrix().to_4x4()
        local_z = initial_matrix.col[2].xyz.normalized()
        roll_quat = mathutils.Quaternion(local_z, delta_angle)
        new_rotation = roll_quat @ initial_quat
        camera.rotation_euler = new_rotation.to_euler()


def _roll_delta_from_event(
    context: bpy.types.Context,
    event: bpy.types.Event,
    initial_vector: mathutils.Vector | None,
    initial_angle: float,
) -> float | None:
    if initial_vector is None or initial_vector.length_squared <= 1e-8:
        return None

    pointer_position = get_current_mouse_position(event)
    current_vector = get_mouse_vector_to_center(context, pointer_position)
    if current_vector.length_squared <= 1e-8:
        return None

    delta_angle = initial_vector.angle_signed(current_vector)
    return apply_angle_snapping(delta_angle, initial_angle, event.shift)


class ViewRollHandler:
    """Handler for rolling the view (non-camera mode)"""

    def __init__(self):
        self.rotation: mathutils.Quaternion | None = None
        self.initial_angle: float = 0.0
        self.initial_vector: mathutils.Vector | None = None

    def pointer_down(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Initialize the view roll handler."""
        self.rotation = ViewHandler.get_current_view_rotation(context).copy()
        self.initial_angle = ViewHandler.get_current_roll_angle(context)
        pointer_position = get_current_mouse_position(event)
        self.initial_vector = get_mouse_vector_to_center(context, pointer_position)

    def pointer_move(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Update the view roll based on mouse movement."""
        if self.rotation is None:
            return

        delta_angle = _roll_delta_from_event(context, event, self.initial_vector, self.initial_angle)
        if delta_angle is None:
            return

        apply_view_roll(context, self.rotation, delta_angle)


class CameraRollHandler:
    """Handler for rolling the camera (camera view mode)"""

    def __init__(self):
        self.initial_rotation: mathutils.Euler | None = None
        self.initial_angle: float = 0.0
        self.initial_vector: mathutils.Vector | None = None
        self.camera: bpy.types.Object | None = None

    def pointer_down(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Initialize the camera roll handler."""
        self.camera = CameraHandler.get_camera_object(context)
        if self.camera:
            self.initial_rotation = self.camera.rotation_euler.copy()
            self.initial_angle = ViewHandler.get_current_roll_angle(context)
            pointer_position = get_current_mouse_position(event)
            self.initial_vector = get_mouse_vector_to_center(context, pointer_position)

    def pointer_move(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Update the camera roll based on mouse movement."""
        if self.initial_rotation is None:
            return

        delta_angle = _roll_delta_from_event(context, event, self.initial_vector, self.initial_angle)
        if delta_angle is None:
            return

        if self.camera:
            apply_camera_roll(context, self.initial_rotation, delta_angle)

# Pan handler functions


def apply_view_pan(context: bpy.types.Context, delta_pos: mathutils.Vector) -> None:
    """Apply pan to the view"""
    if CameraHandler.is_camera_view(context):
        if CameraHandler.is_camera_view_locked(context):
            apply_camera_pan(context, delta_pos)
        else:
            apply_camera_view_pan(context, delta_pos)
        return

    rv3d = ViewHandler.get_region_view3d(context)
    right, up, pan_factor = get_pan_vectors_and_factor(context)

    pan = mathutils.Vector()
    pan += mathutils.Vector(right) * delta_pos.x * pan_factor
    pan += mathutils.Vector(up) * delta_pos.y * pan_factor

    rv3d.view_location += pan


def apply_camera_view_pan(context: bpy.types.Context, delta_pos: mathutils.Vector) -> None:
    """Pan the camera frame display without moving the camera object."""
    rv3d = ViewHandler.get_region_view3d(context)
    region = context.region
    if region is None:
        return

    width = max(float(region.width), 1.0)
    height = max(float(region.height), 1.0)
    rv3d.view_camera_offset[0] += delta_pos.x / width
    rv3d.view_camera_offset[1] += delta_pos.y / height


def apply_camera_pan(context: bpy.types.Context, delta_pos: mathutils.Vector) -> None:
    """Apply pan to the camera"""
    camera = CameraHandler.get_camera_object(context)
    if camera:
        right, up, pan_factor = get_pan_vectors_and_factor(context)

        pan_vector = mathutils.Vector()
        pan_vector += right * delta_pos.x * pan_factor
        pan_vector += up * delta_pos.y * pan_factor

        camera.location += pan_vector


class ViewPanHandler:
    """Handler for panning the view (non-camera mode)"""

    def __init__(self):
        self.prev_pos: mathutils.Vector | None = None

    def pointer_down(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Initialize the pan handler."""
        self.prev_pos = get_current_mouse_position(event)

    def pointer_move(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Update the view pan based on mouse movement."""
        if self.prev_pos is None:
            return

        current_pos = get_current_mouse_position(event)
        delta_pos = self.prev_pos - current_pos

        apply_view_pan(context, delta_pos)
        self.prev_pos = current_pos

    def pan_view(self, context: bpy.types.Context, delta: mathutils.Vector) -> None:
        """Pan the view by a given delta vector"""
        apply_view_pan(context, delta)


class CameraPanHandler:
    """Handler for panning the camera (camera view mode)"""

    def __init__(self):
        self.prev_pos: mathutils.Vector | None = None

    def pointer_down(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Initialize the camera pan handler."""
        self.prev_pos = get_current_mouse_position(event)

    def pointer_move(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Update the camera pan based on mouse movement."""
        if self.prev_pos is None:
            return

        current_pos = get_current_mouse_position(event)
        delta_pos = self.prev_pos - current_pos

        apply_camera_pan(context, delta_pos)
        self.prev_pos = current_pos

# Zoom handler functions


def apply_view_zoom(context: bpy.types.Context, zoom_delta: float) -> None:
    """Apply zoom to the view"""
    if CameraHandler.is_camera_view(context):
        if CameraHandler.is_camera_view_locked(context):
            apply_camera_zoom(context, zoom_delta)
        else:
            apply_camera_view_zoom(context, zoom_delta)
        return

    rv3d = ViewHandler.get_region_view3d(context)
    rv3d.view_distance += zoom_delta * rv3d.view_distance * 0.1
    rv3d.view_distance = max(0.1, rv3d.view_distance)


def apply_camera_view_zoom(context: bpy.types.Context, zoom_delta: float) -> None:
    """Zoom the camera frame display without moving the camera object."""
    rv3d = ViewHandler.get_region_view3d(context)
    rv3d.view_camera_zoom -= zoom_delta * 50.0
    rv3d.view_camera_zoom = min(max(rv3d.view_camera_zoom, -30.0), 600.0)


def apply_camera_zoom(context: bpy.types.Context, zoom_delta: float) -> None:
    """Apply zoom to the camera by moving it forward/backward"""
    camera = CameraHandler.get_camera_object(context)
    if camera:
        camera_matrix = camera.matrix_world
        forward = -camera_matrix.col[2].xyz.normalized()

        rv3d = ViewHandler.get_region_view3d(context)
        move_distance = zoom_delta * rv3d.view_distance * 0.1

        camera.location += forward * move_distance


class ViewZoomHandler:
    """Handler for zooming the view (non-camera mode)"""

    def __init__(self):
        self.zoom_factor: float = 0.02
        self.prev_pos: mathutils.Vector | None = None

    def pointer_down(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        self.prev_pos = mathutils.Vector((event.mouse_x, event.mouse_y))

    def pointer_move(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Update the view zoom based on mouse movement."""
        if self.prev_pos is None:
            return

        current_pos = mathutils.Vector((event.mouse_x, event.mouse_y))
        delta = self.prev_pos - current_pos
        zoom_delta = delta.y * self.zoom_factor

        apply_view_zoom(context, zoom_delta)
        self.prev_pos = current_pos


class CameraZoomHandler:
    """Handler for zooming the camera (camera view mode)"""

    def __init__(self):
        self.zoom_factor: float = 0.02
        self.prev_pos: mathutils.Vector | None = None

    def pointer_down(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        self.prev_pos = mathutils.Vector((event.mouse_x, event.mouse_y))

    def pointer_move(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Update the camera zoom based on mouse movement."""
        if self.prev_pos is None:
            return

        current_pos = mathutils.Vector((event.mouse_x, event.mouse_y))
        delta = self.prev_pos - current_pos
        zoom_delta = delta.y * self.zoom_factor

        apply_camera_zoom(context, zoom_delta)
        self.prev_pos = current_pos

# Orbit handler functions


def _apply_camera_view_orbit_if_needed(
    context: bpy.types.Context,
    delta: mathutils.Vector,
    shift: bool,
    sensitivity: float,
) -> bool:
    if not CameraHandler.is_camera_view(context):
        return False

    if CameraHandler.is_camera_view_locked(context):
        apply_camera_orbit(context, delta, shift, sensitivity)
    return True


def _apply_snapped_view_orbit(euler: mathutils.Euler, delta: mathutils.Vector, sensitivity: float) -> None:
    snap_angle = math.radians(15.0)
    rot_z = delta.x * sensitivity
    rot_x = -delta.y * sensitivity

    temp_euler = euler.copy()
    temp_euler.z += rot_z
    temp_euler.x += rot_x

    euler.z = round(temp_euler.z / snap_angle) * snap_angle
    euler.x = round(temp_euler.x / snap_angle) * snap_angle


def _apply_free_view_orbit(euler: mathutils.Euler, delta: mathutils.Vector, sensitivity: float) -> None:
    euler.z += delta.x * sensitivity
    euler.x += -delta.y * sensitivity


def apply_view_orbit(context: bpy.types.Context, delta: mathutils.Vector, shift: bool = False, sensitivity: float = 0.005) -> None:
    """Apply orbit to the view"""
    if _apply_camera_view_orbit_if_needed(context, delta, shift, sensitivity):
        return

    rv3d = ViewHandler.get_region_view3d(context)
    euler = rv3d.view_rotation.to_euler('XYZ')

    if shift:
        _apply_snapped_view_orbit(euler, delta, sensitivity)
    else:
        _apply_free_view_orbit(euler, delta, sensitivity)

    rv3d.view_rotation = euler.to_quaternion()


def _orbit_delta_angles(delta: mathutils.Vector, shift: bool, sensitivity: float) -> tuple[float, float]:
    snap_angle = math.radians(15.0)
    rot_z = delta.x * sensitivity
    rot_x = -delta.y * sensitivity
    if shift:
        rot_z = round(rot_z / snap_angle) * snap_angle
        rot_x = round(rot_x / snap_angle) * snap_angle
    return rot_z, rot_x


def _rotated_camera_position(
    current_location: mathutils.Vector,
    pivot: mathutils.Vector,
    current_rotation: mathutils.Euler,
    rot_z: float,
    rot_x: float,
) -> tuple[mathutils.Vector, mathutils.Vector]:
    camera_pos = current_location - pivot
    rot_matrix_z = mathutils.Matrix.Rotation(rot_z, 4, 'Z')
    camera_pos = rot_matrix_z @ camera_pos

    current_matrix = current_rotation.to_matrix().to_4x4()
    local_x = current_matrix.col[0].xyz.normalized()
    rot_matrix_x = mathutils.Matrix.Rotation(rot_x, 4, local_x)
    camera_pos = rot_matrix_x @ camera_pos
    return camera_pos, local_x


def _camera_orbit_rotation(
    current_rotation: mathutils.Euler,
    local_x: mathutils.Vector,
    rot_z: float,
    rot_x: float,
) -> mathutils.Euler:
    current_quat = current_rotation.to_quaternion()
    z_rot_quat = mathutils.Quaternion((0, 0, 1), rot_z)
    x_rot_quat = mathutils.Quaternion(local_x, rot_x)
    new_rotation = x_rot_quat @ z_rot_quat @ current_quat
    return new_rotation.to_euler()


def apply_camera_orbit(context: bpy.types.Context, delta: mathutils.Vector, shift: bool = False, sensitivity: float = 0.005) -> None:
    """Apply orbit to the camera around the scene cursor while preserving current camera state"""
    camera = CameraHandler.get_camera_object(context)
    if not camera:
        return

    pivot = context.scene.cursor.location.copy()
    rot_z, rot_x = _orbit_delta_angles(delta, shift, sensitivity)
    current_location = camera.location.copy()
    current_rotation = camera.rotation_euler.copy()
    camera_pos, local_x = _rotated_camera_position(current_location, pivot, current_rotation, rot_z, rot_x)
    camera.location = pivot + camera_pos
    camera.rotation_euler = _camera_orbit_rotation(current_rotation, local_x, rot_z, rot_x)


class ViewOrbitHandler:
    """Handler for orbiting the view (non-camera mode)"""

    def __init__(self):
        self.prev_pos: mathutils.Vector | None = None
        self.sensitivity: float = 0.005

    def pointer_down(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Initialize the orbit handler."""
        self.prev_pos = get_current_mouse_position(event)

    def pointer_move(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Update the view orbit based on mouse movement."""
        if self.prev_pos is None:
            return

        current_pos = get_current_mouse_position(event)
        delta = self.prev_pos - current_pos

        apply_view_orbit(context, delta, event.shift, self.sensitivity)
        self.prev_pos = current_pos


class CameraOrbitHandler:
    """Handler for orbiting the camera (camera view mode)"""

    def __init__(self):
        self.prev_pos: mathutils.Vector | None = None
        self.sensitivity: float = 0.005

    def pointer_down(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Initialize the camera orbit handler."""
        self.prev_pos = get_current_mouse_position(event)

    def pointer_move(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Update the camera orbit based on mouse movement."""
        if self.prev_pos is None:
            return

        current_pos = get_current_mouse_position(event)
        delta = self.prev_pos - current_pos

        apply_camera_orbit(context, delta, event.shift, self.sensitivity)
        self.prev_pos = current_pos

# Composite handlers using composition


class RollHandler:
    """Composite handler for rolling the view or camera"""

    def __init__(self):
        self.view_handler = ViewRollHandler()
        self.camera_handler = CameraRollHandler()
        self.active_handler = None

    def pointer_down(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Initialize the appropriate roll handler based on current view mode."""
        if CameraHandler.is_camera_view_locked(context):
            self.active_handler = self.camera_handler
        else:
            self.active_handler = self.view_handler

        self.active_handler.pointer_down(context, event)

    def pointer_move(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Update the roll based on mouse movement using the active handler."""
        if self.active_handler:
            self.active_handler.pointer_move(context, event)


class PanHandler:
    """Composite handler for panning the view or camera"""

    def __init__(self):
        self.view_handler = ViewPanHandler()
        self.camera_handler = CameraPanHandler()
        self.active_handler = None

    def pointer_down(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Initialize the appropriate pan handler based on current view mode."""
        if CameraHandler.is_camera_view_locked(context):
            self.active_handler = self.camera_handler
        else:
            self.active_handler = self.view_handler

        self.active_handler.pointer_down(context, event)

    def pointer_move(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Update the pan based on mouse movement using the active handler."""
        if self.active_handler:
            self.active_handler.pointer_move(context, event)


class ZoomHandler:
    """Composite handler for zooming the view or camera"""

    def __init__(self):
        self.view_handler = ViewZoomHandler()
        self.camera_handler = CameraZoomHandler()
        self.active_handler = None

    def pointer_down(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Initialize the appropriate zoom handler based on current view mode."""
        if CameraHandler.is_camera_view_locked(context):
            self.active_handler = self.camera_handler
        else:
            self.active_handler = self.view_handler

        self.active_handler.pointer_down(context, event)

    def pointer_move(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Update the zoom based on mouse movement using the active handler."""
        if self.active_handler:
            self.active_handler.pointer_move(context, event)


class OrbitHandler:
    """Composite handler for orbiting the view or camera"""

    def __init__(self):
        self.view_handler = ViewOrbitHandler()
        self.camera_handler = CameraOrbitHandler()
        self.active_handler = None

    def pointer_down(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Initialize the appropriate orbit handler based on current view mode."""
        if CameraHandler.is_camera_view_locked(context):
            self.active_handler = self.camera_handler
        else:
            self.active_handler = self.view_handler

        self.active_handler.pointer_down(context, event)

    def pointer_move(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Update the orbit based on mouse movement using the active handler."""

        if self.active_handler:
            self.active_handler.pointer_move(context, event)
