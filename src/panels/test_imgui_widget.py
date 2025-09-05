import typing
import bpy
import mathutils

from ..operators.view_handlers import ViewPanHandler, apply_view_orbit, apply_view_pan, apply_view_zoom

from ..imgui.ui import UI

from ..utils.draw_handler import DrawHandler


from ..utils.operator_return import OperatorReturn, OperatorReturnType


class TestImguiWidget(bpy.types.Operator):
    """The smallest possible test widget drawing a simple square"""
    bl_idname = "navigation_puck.test_imgui_widget"
    bl_label = "Test Widget"
    bl_options = {'REGISTER'}

    draw_handler = DrawHandler()
    mouse_pos = (0, 0)
    initial_mouse_pos = (0, 0)

    ui = UI()

    is_active = False


    @staticmethod
    def force_redraw(context: bpy.types.Context) -> None:
        """Force redraw of the 3D view"""
        if context.area:
            context.area.tag_redraw()

    # Override Operator method
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """
        Start the modal operator and initialize widget
        
        Called once when the operator is invoked
        """

        if context.window_manager is None:
            return OperatorReturn.CANCELLED

        context.window_manager.modal_handler_add(self) # ❗important

        self.draw_handler.add(context, self.draw_callback)

        # setup
        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)
        self.initial_mouse_pos = self.mouse_pos

        TestImguiWidget.force_redraw(context)

        return OperatorReturn.RUNNING_MODAL

    # Override Operator method
    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """
        Handle widget events
        
        Called on any mouse move or click event, as well as every frame
        """

        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)

        if self.is_active:
            if event.type == 'MOUSEMOVE':
                apply_view_pan(context, mathutils.Vector((event.mouse_prev_x - event.mouse_x, event.mouse_prev_y - event.mouse_y)))
            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                self.is_active = False

            TestImguiWidget.force_redraw(context)
            return OperatorReturn.RUNNING_MODAL
        
        if self.ui.ctx.handle_event(event):
            # Event was consumed by the widget, redraw
            TestImguiWidget.force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        if event.type == 'ESC':
            self.draw_handler.remove()
            TestImguiWidget.force_redraw(context)

            return OperatorReturn.CANCELLED

        TestImguiWidget.force_redraw(context)
        return OperatorReturn.RUNNING_MODAL

    def draw_callback(self, op: typing.Any, context: bpy.types.Context) -> None:
        """
        Draw shaders UI for viewport overlay

        registered with a DrawHandler(), called after each `force_redraw` call
        """

        if self.is_active:
            self.ui.ctx.reset_state()
            return

        self.ui.ctx.begin_frame(self.mouse_pos)

        x, y = self.initial_mouse_pos

        response = self.ui.button("Pan", (x -41, y - 41), (40, 40))
        if response.dragged:
            # apply_view_pan(context, response.drag_delta)
            self.is_active = True

        response = self.ui.button("Rotate", (x , y - 41), (40, 40))
        if response.dragged:
            apply_view_orbit(context, response.drag_delta, response.shift)

        response = self.ui.button("Zoom", (x - 41, y), (40, 40))
        if response.dragged:
            zoom_delta = response.drag_delta.y * 0.02
            apply_view_zoom(context, zoom_delta)

        # TODO: Roll

        self.ui.ctx.end_frame()
