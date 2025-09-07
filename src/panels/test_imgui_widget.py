import typing
import os
import bpy
import mathutils

from ..imgui.renderer.rect_outline_command import RectOutlineCommand

from ..utils import add_modal_handler
from ..utils.draw_handler import force_redraw
from ..operators.view_handlers import apply_view_orbit, apply_view_pan, apply_view_zoom
from ..imgui.ui import UI
from ..utils.draw_handler import DrawHandler
from ..utils.operator_return import OperatorReturn, OperatorReturnType

def load_image(image_name: str) -> typing.Optional[bpy.types.Image]:
    """Load an image from the given path, or return existing if already loaded"""

    addon_dir = os.path.dirname(os.path.dirname(__file__))
    image_path = os.path.join(addon_dir, image_name)
    try:
        image = bpy.data.images.load(image_path, check_existing=True)  # type: ignore
        return image
    except Exception as e:
        print(f"Error loading image {image_path}: {e}")
        return None

class TestImguiWidget:

    def __init__(self) -> None:
        print("🫤 TestImguiWidget::__init__")
        self.draw_handler = DrawHandler()
        self.mouse_pos = (0, 0)
        self.initial_mouse_pos = (0, 0)

        self.ui = UI()
        
        # Get the path to the move.png icon
        self.image = None

        self.is_active = False
    
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Start the modal operator and initialize widget"""
        print("😄❗❗❗❗❗❗❗ TestImguiWidget::setup")

        self.draw_handler.add(context, self.draw_callback)

        # setup
        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)
        self.initial_mouse_pos = self.mouse_pos
        self.image = load_image("move.png")

        force_redraw(context)

        return OperatorReturn.RUNNING_MODAL

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Handle widget events"""
        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)

        if self.is_active:
            if event.type == 'MOUSEMOVE':
                apply_view_pan(context, mathutils.Vector((event.mouse_prev_x - event.mouse_x, event.mouse_prev_y - event.mouse_y)))
            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                self.is_active = False

            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL
        
        if self.ui.ctx.handle_event(event):
            # Event was consumed by the widget, redraw
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        if event.type == 'ESC':
            self.draw_handler.remove()
            force_redraw(context)

            return OperatorReturn.CANCELLED

        force_redraw(context)
        return OperatorReturn.RUNNING_MODAL

    def draw_callback(self, _op: typing.Any, context: bpy.types.Context):
        """
        Draw shaders UI for viewport overlay

        registered with a DrawHandler(), called after each `force_redraw` call
        """
        if self.is_active:
            self.ui.ctx.reset_state()
            return

        self.ui.begin_frame(self.mouse_pos)

        x, y = self.initial_mouse_pos

        if self.image:
            response = self.ui.image_button(self.image, (x -41, y - 41), (40, 40))
            if response.dragged:
                apply_view_pan(context, response.drag_delta)
                self.is_active = True
                
        self.ui.renderer.add(RectOutlineCommand(rect=(x - 81, y - 81, 42, 42), outline_color=(1, 0, 0, 1), fill_color=(0, 0, 0, 0.5), outline_width=2.0))

        response = self.ui.button("Rotate", (x , y - 41), (40, 40))
        if response.dragged:
            apply_view_orbit(context, response.drag_delta, response.shift)

        response = self.ui.button("Zoom", (x - 41, y), (40, 40))
        if response.dragged:
            zoom_delta = response.drag_delta.y * 0.02
            apply_view_zoom(context, zoom_delta)

        # TODO Roll
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

