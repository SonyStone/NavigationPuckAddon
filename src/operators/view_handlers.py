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


class ViewHandler:
    """Handler for view operations"""
    @staticmethod
    def get_region_view3d(context: bpy.types.Context) -> bpy.types.RegionView3D:
        """Get the current RegionView3D"""
        space_data: typing.Any = context.space_data
        region_3d: bpy.types.RegionView3D = space_data.region_3d
        return region_3d

    @staticmethod
    def get_current_view_rotation(context: bpy.types.Context) -> mathutils.Quaternion:
        """Get the current view rotation"""
        return ViewHandler.get_region_view3d(context).view_rotation

    @staticmethod
    def get_current_roll_angle(context: bpy.types.Context) -> float:
        """Calculate the roll angle of the current view."""
        rv3d = ViewHandler.get_region_view3d(context)

        # Get view axes in world space
        view_matrix_inv = rv3d.view_matrix.inverted()
        view_up = view_matrix_inv.col[1].xyz.normalized()
        view_dir = -view_matrix_inv.col[2].xyz.normalized()

        # Choose reference up vector (usually world Z)
        ref_up = mathutils.Vector((0, 0, 1))

        # If view is nearly aligned with Z axis, use Y as reference
        if abs(view_dir.dot(ref_up)) > 0.999:
            ref_up = mathutils.Vector((0, 1, 0))

        # Calculate the zero-roll up vector
        zero_roll_up = ref_up - view_dir * ref_up.dot(view_dir)

        # Guard against numerical instability
        if zero_roll_up.length_squared < 1e-8:
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
            return 0.0

        view_up_proj.normalize()

        # Calculate angle between actual up and zero-roll up
        dot_product = max(min(view_up_proj.dot(zero_roll_up), 1.0), -1.0)
        angle = math.acos(dot_product)

        # Determine sign
        if view_up_proj.dot(zero_roll_right) > 0:
            angle = -angle

        return angle

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
        if self.initial_vector is None or self.rotation is None:
            return

        pointer_position = get_current_mouse_position(event)
        current_vector = get_mouse_vector_to_center(context, pointer_position)
        delta_angle = self.initial_vector.angle_signed(current_vector)
        delta_angle = apply_angle_snapping(
            delta_angle, self.initial_angle, event.shift)

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
        if self.initial_rotation is None or self.initial_vector is None:
            return

        pointer_position = get_current_mouse_position(event)
        current_vector = get_mouse_vector_to_center(context, pointer_position)
        delta_angle = self.initial_vector.angle_signed(current_vector)
        delta_angle = apply_angle_snapping(
            delta_angle, self.initial_angle, event)

        if self.camera:
            apply_camera_roll(context, self.initial_rotation, delta_angle)

# Pan handler functions


def apply_view_pan(context: bpy.types.Context, delta_pos: mathutils.Vector) -> None:
    """Apply pan to the view"""
    rv3d = ViewHandler.get_region_view3d(context)
    right, up, pan_factor = get_pan_vectors_and_factor(context)

    pan = mathutils.Vector()
    pan += mathutils.Vector(right) * delta_pos.x * pan_factor
    pan += mathutils.Vector(up) * delta_pos.y * pan_factor

    rv3d.view_location += pan


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
    rv3d = ViewHandler.get_region_view3d(context)
    rv3d.view_distance += zoom_delta * rv3d.view_distance * 0.1
    rv3d.view_distance = max(0.1, rv3d.view_distance)


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


def apply_view_orbit(context: bpy.types.Context, delta: mathutils.Vector, shift: bool = False, sensitivity: float = 0.005) -> None:
    """Apply orbit to the view"""
    rv3d = ViewHandler.get_region_view3d(context)
    euler = rv3d.view_rotation.to_euler('XYZ')
    snap_angle = math.radians(15.0)

    if shift:
        rot_z = delta.x * sensitivity
        rot_x = -delta.y * sensitivity

        temp_euler = euler.copy()
        temp_euler.z += rot_z
        temp_euler.x += rot_x

        snapped_z = round(temp_euler.z / snap_angle) * snap_angle
        snapped_x = round(temp_euler.x / snap_angle) * snap_angle

        euler.z = snapped_z
        euler.x = snapped_x
    else:
        rot_z = delta.x * sensitivity
        rot_x = -delta.y * sensitivity

        euler.z += rot_z
        euler.x += rot_x

    rv3d.view_rotation = euler.to_quaternion()


def apply_camera_orbit(context: bpy.types.Context, delta: mathutils.Vector, event: bpy.types.Event, sensitivity: float = 0.005) -> None:
    """Apply orbit to the camera around the scene cursor while preserving current camera state"""
    camera = CameraHandler.get_camera_object(context)
    if not camera:
        return

    pivot = context.scene.cursor.location.copy()
    snap_angle = math.radians(15.0)

    rot_z = delta.x * sensitivity
    rot_x = -delta.y * sensitivity

    # Apply snapping if shift is pressed
    if event.shift:
        rot_z = round(rot_z / snap_angle) * snap_angle
        rot_x = round(rot_x / snap_angle) * snap_angle

    # Store current camera transform
    current_location = camera.location.copy()
    current_rotation = camera.rotation_euler.copy()

    # Calculate position relative to pivot
    camera_pos = current_location - pivot

    # Apply horizontal rotation around world Z
    rot_matrix_z = mathutils.Matrix.Rotation(rot_z, 4, 'Z')
    camera_pos = rot_matrix_z @ camera_pos

    # Apply vertical rotation around the camera's current right vector
    # Use current rotation to get the right vector, not the world-space matrix
    current_matrix = current_rotation.to_matrix().to_4x4()
    local_x = current_matrix.col[0].xyz.normalized()
    rot_matrix_x = mathutils.Matrix.Rotation(rot_x, 4, local_x)
    camera_pos = rot_matrix_x @ camera_pos

    # Update camera location
    camera.location = pivot + camera_pos

    # Apply the same rotations to the camera's current orientation
    # Convert current rotation to quaternion for better rotation composition
    current_quat = current_rotation.to_quaternion()

    # Apply rotations in the same order
    z_rot_quat = mathutils.Quaternion((0, 0, 1), rot_z)
    x_rot_quat = mathutils.Quaternion(local_x, rot_x)

    # Compose rotations: apply horizontal rotation first, then vertical
    new_rotation = x_rot_quat @ z_rot_quat @ current_quat

    # Convert back to Euler and apply
    camera.rotation_euler = new_rotation.to_euler()


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

        apply_view_orbit(context, delta, event, self.sensitivity)
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

        apply_camera_orbit(context, delta, event, self.sensitivity)
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
