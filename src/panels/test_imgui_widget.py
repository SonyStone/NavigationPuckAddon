import math
import typing
import os
import bpy
import mathutils


from ..utils import add_modal_handler, get_current_mouse_position, get_mouse_vector_to_center
from ..utils.draw_handler import force_redraw
from ..operators.view_handlers import ViewHandler, apply_angle_snapping, apply_view_orbit, apply_view_pan, apply_view_roll, apply_view_zoom
from ..imgui.ui import UI
from ..utils.draw_handler import DrawHandler
from ..utils.operator_return import OperatorReturn, OperatorReturnType


def load_image(image_name: str) -> typing.Optional[bpy.types.Image]:
    """Load an image from the given path, or return existing if already loaded"""

    addon_dir = os.path.dirname(os.path.dirname(__file__))
    image_path = os.path.join(addon_dir, image_name)
    try:
        image = bpy.data.images.load(
            image_path, check_existing=True)  # type: ignore
        return image
    except Exception as e:
        print(f"Error loading image {image_path}: {e}")
        return None


class ViewOperationHandler:
    """Handles the state of a view operation (pan, orbit, zoom, roll)"""

    def __init__(self):
        self.is_active = False
        self.start_mouse_pos = mathutils.Vector((0, 0))

    def apply(self, mouse_pos: mathutils.Vector = mathutils.Vector((0, 0))):
        """Apply the operation delta to the view"""
        self.is_active = True
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

    def apply(self, context: bpy.types.Context, delta: mathutils.Vector, mouse_pos: mathutils.Vector = mathutils.Vector((0, 0))):
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

    def apply(self, context: bpy.types.Context, delta: mathutils.Vector, mouse_pos: mathutils.Vector = mathutils.Vector((0, 0)), shift: bool = False):
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

    def apply(self, context: bpy.types.Context, delta: mathutils.Vector, mouse_pos: mathutils.Vector = mathutils.Vector((0, 0))):
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

    def apply(self, context: bpy.types.Context, mouse_pos: mathutils.Vector = mathutils.Vector((0, 0)), pointer_offset: mathutils.Vector = mathutils.Vector((0, 0))):
        """Apply the roll delta to the view"""
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


class TestImguiWidget:
    """The smallest possible test widget drawing a simple square"""

    def __init__(self) -> None:
        self.draw_handler = DrawHandler()
        self.mouse_pos = mathutils.Vector((0, 0))
        self.initial_mouse_pos = mathutils.Vector((0, 0))

        self.ui = UI()

        # Get the path to the move.png icon
        self.image = None

        self.view_pan = ViewPan()
        self.view_orbit = ViewOrbit()
        self.view_zoom = ViewZoom()
        self.view_roll = ViewRoll()

        self.is_pressed = False
        self.is_in_radius = False
        self.is_done_operation = False
        self.auto_dismiss_distance = 100.0

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Start the modal operator and initialize widget"""
        self.is_pressed = True
        self.is_in_radius = True
        self.is_done_operation = False

        self.draw_handler.add(context, self.draw_callback)

        # setup
        self.mouse_pos[:] = mathutils.Vector(
            (event.mouse_region_x, event.mouse_region_y))
        self.initial_mouse_pos[:] = self.mouse_pos
        self.image = load_image("move.png")

        force_redraw(context)

        return OperatorReturn.RUNNING_MODAL

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Handle widget events"""
        self.mouse_pos[:] = (event.mouse_region_x, event.mouse_region_y)

        if event.type == 'V' and event.value == 'RELEASE':
            self.is_pressed = False

        if math.dist(self.mouse_pos, self.initial_mouse_pos) > self.auto_dismiss_distance:  # type: ignore
            if self.is_pressed:
                # Move initial_mouse_pos closer to current mouse pos
                direction = (self.mouse_pos -
                             self.initial_mouse_pos).normalized()
                self.initial_mouse_pos += direction * \
                    (math.dist(self.mouse_pos, self.initial_mouse_pos) - # type: ignore
                     self.auto_dismiss_distance)  
            else:
                self.is_in_radius = False

        if self.view_pan.event_handler(context, event) or \
           self.view_orbit.event_handler(context, event) or \
           self.view_zoom.event_handler(context, event) or \
           self.view_roll.event_handler(context, event):
            if self.view_pan.view_op.is_active:
                self.initial_mouse_pos[:] = self.mouse_pos - \
                    self.view_pan.view_op.start_mouse_pos
            if self.view_orbit.view_op.is_active:
                self.initial_mouse_pos[:] = self.mouse_pos - \
                    self.view_orbit.view_op.start_mouse_pos
            if self.view_zoom.view_op.is_active:
                self.initial_mouse_pos[:] = self.mouse_pos - \
                    self.view_zoom.view_op.start_mouse_pos
            if self.view_roll.view_op.is_active:
                self.initial_mouse_pos[:] = self.mouse_pos - \
                    self.view_roll.view_op.start_mouse_pos
            self.is_done_operation = True
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        if not self.is_pressed and not self.is_in_radius:
            self.draw_handler.remove()
            force_redraw(context)
            return OperatorReturn.CANCELLED

        if self.is_done_operation and not self.is_pressed:
            self.draw_handler.remove()
            force_redraw(context)
            return OperatorReturn.FINISHED

        if self.ui.ctx.handle_event(event):
            # Event was consumed by the widget, redraw
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        force_redraw(context)
        return OperatorReturn.RUNNING_MODAL

    def draw_callback(self, _op: typing.Any, context: bpy.types.Context):
        """
        Draw shaders UI for viewport overlay

        registered with a DrawHandler(), called after each `force_redraw` call
        """
        if self.view_pan.view_op.is_active or \
           self.view_orbit.view_op.is_active or \
           self.view_zoom.view_op.is_active or \
           self.view_roll.view_op.is_active:
            self.ui.ctx.reset_state()
            return

        self.ui.begin_frame(self.mouse_pos)

        x, y = self.initial_mouse_pos
        offset = (5, 5)
        size = 60

        if self.image:
            response = self.ui.image_button(
                self.image, (x - size - 0.5 + offset[0], y - size - 0.5 + offset[1]), (size, size))
            if response.clicked:
                self.view_pan.apply(
                    context, response.drag_delta, self.mouse_pos - self.initial_mouse_pos)
                self.initial_mouse_pos[:] = self.mouse_pos - \
                    self.view_pan.view_op.start_mouse_pos

        response = self.ui.button(
            "Rotate", (x + 0.5 + offset[0], y - size - 0.5 + offset[1]), (size, size))
        if response.clicked:
            self.view_orbit.apply(context, response.drag_delta,
                                  self.mouse_pos - self.initial_mouse_pos, response.shift)
            self.initial_mouse_pos[:] = self.mouse_pos - \
                self.view_orbit.view_op.start_mouse_pos

        response = self.ui.button(
            "Zoom", (x - size - 0.5 + offset[0], y + 0.5 + offset[1]), (size, size))
        if response.clicked:
            self.view_zoom.apply(context, response.drag_delta,
                                 self.mouse_pos - self.initial_mouse_pos)
            self.initial_mouse_pos[:] = self.mouse_pos - \
                self.view_zoom.view_op.start_mouse_pos

        # TODO Roll
        response = self.ui.button(
            "Roll", (x + 0.5 + offset[0], y + 0.5 + offset[1]), (size, size))
        if response.clicked:
            self.view_roll.apply(context, self.mouse_pos,
                                 self.mouse_pos - self.initial_mouse_pos)
            self.initial_mouse_pos[:] = self.mouse_pos - \
                self.view_roll.view_op.start_mouse_pos

        self.ui.end_frame()


class TestImguiWidgetOperator(bpy.types.Operator):
    """The smallest possible test widget drawing a simple square"""
    bl_idname = "navigation_puck.test_imgui_widget"
    bl_label = "Test Widget"
    bl_options = {'REGISTER'}

    app = TestImguiWidget()

    # Override Operator method
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """
        Start the modal operator and initialize widget

        Called once when the operator is invoked
        """
        if not add_modal_handler(context, self):
            return OperatorReturn.CANCELLED

        return self.app.invoke(context, event)

    # Override Operator method
    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """
        Handle widget events

        Called on any mouse move or click event, as well as every frame
        """

        return self.app.event_handler(context, event)
