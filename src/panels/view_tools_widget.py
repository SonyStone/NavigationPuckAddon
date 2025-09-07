import math
import typing
import bpy

from ..utils.draw_handler import DrawHandler
from ..utils.operator_return import OperatorReturn, OperatorReturnType

from .ui_tools import Button, LayoutType, WidgetDrawer, WidgetLayout


def force_redraw(context: bpy.types.Context) -> None:
    """Force an immediate redraw of the area"""
    if context.area:
        context.area.tag_redraw()


def execute_view_pan(context: bpy.types.Context, button: Button) -> OperatorReturnType:
    """Execute view pan modal operator"""
    ops: typing.Any  = bpy.ops
    ops.navigation_puck.view_pan_modal('INVOKE_DEFAULT')
    return OperatorReturn.FINISHED


def execute_view_orbit(context: bpy.types.Context, button: Button) -> OperatorReturnType:
    """Execute view orbit modal operator"""
    ops: typing.Any  = bpy.ops
    ops.navigation_puck.view_orbit_modal('INVOKE_DEFAULT')
    return OperatorReturn.FINISHED


def execute_view_zoom(context: bpy.types.Context, button: Button) -> OperatorReturnType:
    """Execute view zoom modal operator"""
    ops: typing.Any  = bpy.ops
    ops.navigation_puck.view_zoom_modal('INVOKE_DEFAULT')
    return OperatorReturn.FINISHED


def execute_view_roll(context: bpy.types.Context, button: Button) -> OperatorReturnType:
    """Execute view roll modal operator"""
    ops: typing.Any  = bpy.ops
    ops.navigation_puck.view_roll_modal('INVOKE_DEFAULT')
    return OperatorReturn.FINISHED

class WidgetHandler:
    """Handles the widget state and interaction"""
    
    def __init__(self):
        self.mouse_pos: tuple[float, float] = (0, 0)
        self.initial_mouse_pos: tuple[float, float] = (0, 0)
        self.hovered_button: typing.Optional[int] = None
        self.auto_dismiss_distance: float = 100.0
        self.handler = DrawHandler()

        self.widget_layout = WidgetLayout(spacing=0.0, layout_type=LayoutType.GRID)
        self.widget_drawer = WidgetDrawer()

        self.buttons: typing.List[Button] = [
            Button(label="Pan", icon='VIEW_PAN', callback=execute_view_pan),
            Button(label="Orbit", icon='SPHERE', callback=execute_view_orbit),
            Button(label="Zoom", icon='VIEW_ZOOM', callback=execute_view_zoom),
            Button(label="Roll", icon='MESH_CIRCLE', callback=execute_view_roll)
        ]

    def setup(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """Customize the widget appearance"""

        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)
        self.initial_mouse_pos = self.mouse_pos

        # Calculate button positions
        self.widget_layout.calculate_positions(
            self.buttons,
            self.mouse_pos,
            (60.0, 60.0)  # Default button size
        )

        self.handler.add(context, self.draw_callback)

    def update_hovered_button(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType | None:
        """Update which button is currently hovered"""
        # Update mouse position
        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)

        # Update hover state
        if self._update_hovered_button(context) is not None:
            self.handler.remove()
            force_redraw(context)
            return OperatorReturn.CANCELLED

    def handle_mouse_click(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType | None:
        """Handle mouse click events"""
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if self.hovered_button is not None:
                button = self.buttons[self.hovered_button]
                self.cancel()
                return self.on_button_clicked(button, context)

            # If no button is clicked, we can auto-dismiss
            self.cancel()
            return OperatorReturn.CANCELLED


        # Cancel on right click or ESC
        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self.cancel()
            return OperatorReturn.CANCELLED

        return None


    def cancel(self) -> None:
        """Clean up when cancelled"""
        self.handler.remove()

    def on_button_clicked(self, button: Button, context: bpy.types.Context) -> OperatorReturnType:
        """Handle button click. Override in subclasses to customize behavior."""
        if button.callback:
            return button.callback(context, button)
        return OperatorReturn.FINISHED

    def draw_callback(self, op: typing.Any, context: bpy.types.Context) -> None:
        """Draw callback for the widget."""
        self.widget_drawer.draw_widget(self.buttons, self.hovered_button)

    def _update_hovered_button(self, context: bpy.types.Context) -> None | OperatorReturnType:
        """Update which button is currently hovered"""
        x, y = self.mouse_pos

        for i, button in enumerate(self.buttons):
            if button.rect.contains_point(x, y):
                self.hovered_button = i
                return

        # Check if we should auto-dismiss
        orig_x, orig_y = self.initial_mouse_pos
        distance = math.sqrt((x - orig_x)**2 + (y - orig_y)**2)
        if distance > self.auto_dismiss_distance:
            self.handler.remove()
            # self.on_cancel(context)
            return OperatorReturn.CANCELLED

        self.hovered_button = None

class NavigationPuckViewToolsWidget(bpy.types.Operator):
    """Display floating view tools widget at mouse position"""
    bl_idname = "navigation_puck.navigation_puck_popup"
    bl_label = "Navigation Puck Popup"
    bl_options = {'REGISTER'}

    widget = WidgetHandler()

    # Override Operator method
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Start the modal operator and initialize widget"""
        print("😄 Invoking View Tools Widget Operator")

        self.widget.setup(context, event)

        if context.window_manager is None:
            return OperatorReturn.CANCELLED

        context.window_manager.modal_handler_add(self)

        force_redraw(context)

        return OperatorReturn.RUNNING_MODAL

    # Override Operator method
    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Handle widget events"""
        print("💫 Running View Tools Widget Modal")

        result = self.widget.update_hovered_button(context, event)
        if result is not None:
            return result

        force_redraw(context)

        # Handle mouse click
        result = self.widget.handle_mouse_click(context, event)
        if result is not None:
            return result

        return OperatorReturn.RUNNING_MODAL

    # Override Operator method
    def cancel(self, context: bpy.types.Context) -> None:
        """Clean up when cancelled"""
        print("🛑 Cancelling View Tools Widget Operator")
        self.widget.cancel()
