"""
Example usage of the Enhanced UI Tools with ImGui-style event handling
This shows how to integrate the new system with your existing Blender addon workflow.
"""

import typing
import bpy

from ..utils.draw_handler import DrawHandler

from .view_tools_widget import force_redraw

from ..imgui.imgui_widget import ImGuiWidget, Button, LayoutType
from ..utils.operator_return import OperatorReturn, OperatorReturnType


class NavigationPuckWidget:
    """Example widget using the enhanced ImGui system for navigation controls"""

    def __init__(self, center_pos: typing.Tuple[float, float] = (100.0, 100.0)):
        self.widget = ImGuiWidget(origin=center_pos)
        self.setup_buttons()

    def setup_buttons(self):
        """Setup navigation buttons"""
        # Pan buttons
        pan_up = self.widget.add_button("↑", "TRIA_UP", self.pan_up_callback)
        pan_down = self.widget.add_button(
            "↓", "TRIA_DOWN", self.pan_down_callback)
        pan_left = self.widget.add_button(
            "←", "TRIA_LEFT", self.pan_left_callback)
        pan_right = self.widget.add_button(
            "→", "TRIA_RIGHT", self.pan_right_callback)

        # Additional controls
        zoom_in = self.widget.add_button("+", "ZOOM_IN", self.zoom_in_callback)
        zoom_out = self.widget.add_button(
            "-", "ZOOM_OUT", self.zoom_out_callback)
        reset_view = self.widget.add_button(
            "○", "HOME", self.reset_view_callback)

        # Set up circular layout for navigation
        self.widget.set_layout(LayoutType.CIRCLE, spacing=10.0)
        self.widget.update_layout(button_size=(40.0, 40.0))

    def pan_up_callback(self, context: bpy.types.Context, button: Button) -> OperatorReturnType:
        """Pan view up"""
        print("Panning up")
        # Your pan up logic here
        return OperatorReturn.FINISHED

    def pan_down_callback(self, context: bpy.types.Context, button: Button) -> OperatorReturnType:
        """Pan view down"""
        print("Panning down")
        # Your pan down logic here
        return OperatorReturn.FINISHED

    def pan_left_callback(self, context: bpy.types.Context, button: Button) -> OperatorReturnType:
        """Pan view left"""
        print("Panning left")
        # Your pan left logic here
        return OperatorReturn.FINISHED

    def pan_right_callback(self, context: bpy.types.Context, button: Button) -> OperatorReturnType:
        """Pan view right"""
        print("Panning right")
        # Your pan right logic here
        return OperatorReturn.FINISHED

    def zoom_in_callback(self, context: bpy.types.Context, button: Button) -> OperatorReturnType:
        """Zoom in"""
        print("Zooming in")
        # Your zoom in logic here
        return OperatorReturn.FINISHED

    def zoom_out_callback(self, context: bpy.types.Context, button: Button) -> OperatorReturnType:
        """Zoom out"""
        print("Zooming out")
        # Your zoom out logic here
        return OperatorReturn.FINISHED

    def reset_view_callback(self, context: bpy.types.Context, button: Button) -> OperatorReturnType:
        """Reset view to default"""
        print("Resetting view")
        # Your reset view logic here
        return OperatorReturn.FINISHED

    def handle_event(self, event: bpy.types.Event) -> bool:
        """Handle input events - returns True if event was consumed"""
        return self.widget.handle_event(event)

    def draw(self, mouse_pos: typing.Tuple[float, float]):
        """Draw the widget"""
        responses = self.widget.draw(mouse_pos)

        # You can check for specific button interactions here
        clicked_buttons = self.widget.get_clicked_buttons()
        for button, response in clicked_buttons:
            print(f"Button '{button.label}' was clicked!")

        return responses


class ToolbarWidget:
    """Example toolbar widget using enhanced UI tools"""

    def __init__(self, pos: typing.Tuple[float, float] = (20.0, 20.0)):
        self.widget = ImGuiWidget(origin=pos)
        self.setup_toolbar()

    def setup_toolbar(self):
        """Setup toolbar buttons"""
        self.widget.add_button(
            "Select", "RESTRICT_SELECT_OFF", self.select_tool_callback)
        self.widget.add_button(
            "Move", "ORIENTATION_GLOBAL", self.move_tool_callback)
        self.widget.add_button(
            "Rotate", "ORIENTATION_GIMBAL", self.rotate_tool_callback)
        self.widget.add_button("Scale", "FULLSCREEN_EXIT",
                               self.scale_tool_callback)

        # Set horizontal layout
        self.widget.set_layout(LayoutType.HORIZONTAL, spacing=5.0)
        self.widget.update_layout(button_size=(50.0, 30.0))

    def select_tool_callback(self, context: bpy.types.Context, button: Button) -> OperatorReturnType:
        """Activate select tool"""
        print("Select tool activated")
        return OperatorReturn.FINISHED

    def move_tool_callback(self, context: bpy.types.Context, button: Button) -> OperatorReturnType:
        """Activate move tool"""
        print("Move tool activated")
        return OperatorReturn.FINISHED

    def rotate_tool_callback(self, context: bpy.types.Context, button: Button) -> OperatorReturnType:
        """Activate rotate tool"""
        print("Rotate tool activated")
        return OperatorReturn.FINISHED

    def scale_tool_callback(self, context: bpy.types.Context, button: Button) -> OperatorReturnType:
        """Activate scale tool"""
        print("Scale tool activated")
        return OperatorReturn.FINISHED

    def handle_event(self, event: bpy.types.Event) -> bool:
        """Handle input events"""
        return self.widget.handle_event(event)

    def draw(self, mouse_pos: typing.Tuple[float, float]):
        """Draw the toolbar"""
        return self.widget.draw(mouse_pos)


class ViewportWidgetManager:
    """Manages multiple widgets in the viewport"""


    def __init__(self):
        self.mouse_pos: typing.Tuple[float, float] = (0.0, 0.0)
        self.navigation_puck = NavigationPuckWidget(self.mouse_pos)
        self.toolbar = ToolbarWidget((100.0, 100.0))
        self.widgets = [self.navigation_puck, self.toolbar]

    def handle_event(self, event: bpy.types.Event) -> bool:
        """Handle events for all widgets"""

        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)
        self.navigation_puck.widget.origin = self.mouse_pos

        for widget in self.widgets:
            if widget.handle_event(event):
                return True  # Event was consumed
        return False

    def draw(self, mouse_pos: typing.Tuple[float, float]):
        """Draw all widgets"""
        all_responses = {}
        for i, widget in enumerate(self.widgets):
            responses = widget.draw(mouse_pos)
            # Prefix with widget index to avoid key collisions
            for key, response in responses.items():
                all_responses[f"widget_{i}_{key}"] = response
        return all_responses

    def set_navigation_puck_position(self, pos: typing.Tuple[float, float]):
        """Update navigation puck position"""
        self.navigation_puck.widget.origin = pos
        self.navigation_puck.widget.update_layout()

    def toggle_widget_visibility(self, widget_name: str, visible: bool):
        """Toggle visibility of specific widgets"""
        if widget_name == "navigation_puck":
            self.navigation_puck.widget.set_visible(visible)
        elif widget_name == "toolbar":
            self.toolbar.widget.set_visible(visible)

    def draw_callback_px(self, op: typing.Any, context: bpy.types.Context):
        """Draw callback for viewport overlay"""
        # Draw all widgets
        self.draw(self.mouse_pos)


# Example operator that integrates the widget system
class NavigationPuckImguiExample(bpy.types.Operator):
    """Test operator for ImGui-style navigation puck"""
    bl_idname = "navigation_puck.imgui_navigation_puck_popup"
    bl_label = "ImGui Navigation Puck"
    bl_description = "Navigation puck with enhanced event handling"
    bl_options = {'REGISTER'}

    widget_manager = ViewportWidgetManager()
    draw_handler = DrawHandler()

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Start the operator"""

        print("😄 Invoking ImGui Navigation Puck Operator")

        if context.window_manager is None:
            self.draw_handler.remove()
            return OperatorReturn.CANCELLED

        if context.area.type == 'VIEW_3D':
            # Add draw handler
            self.draw_handler.add(context, self.widget_manager.draw_callback_px)
            context.window_manager.modal_handler_add(self)
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL
        else:
            self.draw_handler.remove()
            force_redraw(context)
            return OperatorReturn.CANCELLED


    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Modal operator handling"""
        print("💫 Running ImGui Navigation Puck Operator")
        if event.type == 'ESC':
            self.draw_handler.remove()
            force_redraw(context)
            return OperatorReturn.CANCELLED

        # Handle widget events
        if self.widget_manager.handle_event(event):
            # Event was consumed by widgets, redraw
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        # Pass through other events
        return OperatorReturn.RUNNING_MODAL
