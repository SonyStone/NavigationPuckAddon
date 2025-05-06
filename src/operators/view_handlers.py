import math
import bpy
import mathutils

from ..utils import apply_view_roll, get_current_mouse_position, get_current_roll_angle, get_current_view_rotation, get_mouse_vector_to_center, get_region_view3d, snap_to_nearest_angle


class RollHandler:
    """Handler for rolling the view"""
    rotation: mathutils.Quaternion
    initial_angle: float
    initial_vector: mathutils.Vector
    snap_angle: float = math.radians(15.0)

    def pointer_down(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Initialize the roll handler."""
        self.rotation = get_current_view_rotation(context).copy()
        self.initial_angle = get_current_roll_angle(context)
        self.initial_vector = get_mouse_vector_to_center(context, event)

    def pointer_move(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Update the view roll based on mouse movement."""
        snap = False
        if event.shift:
            snap = True

        current_vector = get_mouse_vector_to_center(context, event)
        delta_angle = self.initial_vector.angle_signed(current_vector)

        if snap:
            delta_angle = snap_to_nearest_angle(
                delta_angle,
                self.initial_angle,
                self.snap_angle
            )

        apply_view_roll(context, self.rotation, delta_angle)


class PanHandler:
    """Handler for panning the view"""
    prev_pos: mathutils.Vector

    def pointer_down(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Initialize the pan handler."""
        self.prev_pos = get_current_mouse_position(event)

    def pointer_move(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Update the view pan based on mouse movement."""
        current_pos = get_current_mouse_position(event)
        delta_pos = self.prev_pos - current_pos

        rv3d = get_region_view3d(context)
        # Get the view matrix inverse to determine view orientation
        view_matrix_inv = rv3d.view_matrix.inverted()

        # Get the view vectors (right and up in view space)
        right = view_matrix_inv.col[0].xyz
        up = view_matrix_inv.col[1].xyz

        region_width = context.region.width

        # Calculate a consistent pan factor based on zoom and view type
        pan_factor = rv3d.view_distance / region_width

        # Calculate pan vector
        pan = mathutils.Vector()
        pan += mathutils.Vector(right) * delta_pos.x * pan_factor
        pan += mathutils.Vector(up) * delta_pos.y * pan_factor

        # Apply pan
        rv3d.view_location += pan

        self.prev_pos = current_pos


class ZoomHandler:
    """Handler for zooming the view"""
    zoom_factor: float = 0.02
    prev_pos = mathutils.Vector((0.0, 0.0))

    def pointer_down(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        self.prev_pos = mathutils.Vector((event.mouse_x, event.mouse_y))

    def pointer_move(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Update the view zoom based on mouse movement."""

        rv3d = get_region_view3d(context)

        # Calculate delta movement (mainly interested in vertical)
        current_pos = mathutils.Vector((event.mouse_x, event.mouse_y))
        delta = self.prev_pos - current_pos

        # Use the Y movement for zooming
        zoom_delta = delta.y * self.zoom_factor

        # Handle different view types
        if rv3d.is_perspective:
            # For perspective view, adjust view distance
            rv3d.view_distance += zoom_delta * rv3d.view_distance * 0.1

            # Clamp to reasonable values to prevent extreme zoom
            rv3d.view_distance = max(0.1, rv3d.view_distance)
        else:
            # For orthographic view, adjust orthographic scale
            rv3d.view_distance += zoom_delta * rv3d.view_distance * 0.1

            # Clamp to reasonable values
            rv3d.view_distance = max(0.1, rv3d.view_distance)

        self.prev_pos = current_pos


class ViewOrbitHandler:
    """Handler for orbiting the view"""
    prev_pos = mathutils.Vector((0.0, 0.0))
    sensitivity: float = 0.005
    snap_angle: float = math.radians(15.0)

    def pointer_down(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Initialize the orbit handler."""
        self.prev_pos = get_current_mouse_position(event)

    def pointer_move(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Update the view orbit based on mouse movement."""

        rv3d = get_region_view3d(context)

        # Calculate delta movement
        current_pos = get_current_mouse_position(event)
        delta = self.prev_pos - current_pos

        # Get current Euler rotation
        euler = rv3d.view_rotation.to_euler('XYZ')

        # Check if shift is pressed for angle snapping
        if event.shift:
            # Calculate rotation increments
            rot_z = delta.x * self.sensitivity
            rot_x = -delta.y * self.sensitivity

            # Global angle snapping
            # First apply the current mouse movement
            temp_euler = euler.copy()
            temp_euler.z += rot_z
            temp_euler.x += rot_x

            # Now calculate the nearest global angle
            # Snap each angle to the nearest 90 degrees
            snapped_z = round(
                temp_euler.z / self.snap_angle) * self.snap_angle
            snapped_x = round(
                temp_euler.x / self.snap_angle) * self.snap_angle

            # Apply snapped global angles
            euler.z = snapped_z
            euler.x = snapped_x
        else:
            # Calculate rotation increments
            rot_z = delta.x * self.sensitivity
            rot_x = -delta.y * self.sensitivity

            # Apply normal rotation
            euler.z += rot_z
            euler.x += rot_x

        rv3d.view_rotation = euler.to_quaternion()

        self.prev_pos = current_pos
