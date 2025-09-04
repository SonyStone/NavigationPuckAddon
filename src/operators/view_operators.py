"""
View manipulation modal operators for panning, rolling, zooming, and orbiting the view.
"""

import bpy

from ..utils.operator_return import OperatorReturn, OperatorReturnType

from .view_handlers import PanHandler, RollHandler, OrbitHandler, ZoomHandler

class ViewPanOperator(bpy.types.Operator):
    """Pan the view while mouse button is held down"""
    bl_idname = "navigation_puck.view_pan_modal"
    bl_label = "Pan View (Hold)"
    bl_options = {'REGISTER', 'UNDO'}

    handler = PanHandler()
    is_pressed: bool

    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Handle the modal event for panning the view."""

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.is_pressed = True
            # context.window.cursor_modal_set('NONE')  # ! Hide cursor
            self.handler.pointer_down(context, event)
            return OperatorReturn.RUNNING_MODAL

        elif event.type == 'MOUSEMOVE' and self.is_pressed:
            self.handler.pointer_move(context, event)
            return OperatorReturn.RUNNING_MODAL

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self.is_pressed:
            if self.is_pressed:
                self.is_pressed = False
                # context.window.cursor_modal_restore()  # Restore cursor
                # bpy.ops.navigation_puck.view_pan_modal('INVOKE_DEFAULT')

                return OperatorReturn.FINISHED

        elif event.type == 'ESC':
            self.is_pressed = False
            # context.window.cursor_modal_restore()  # Restore cursor
            return OperatorReturn.CANCELLED

        elif not self.is_pressed and event.type in {'RIGHTMOUSE'} and event.value == 'PRESS':
            # context.window.cursor_modal_restore()  # Restore cursor
            return OperatorReturn.CANCELLED

        return OperatorReturn.RUNNING_MODAL

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Invoke the modal operator."""

        self.is_pressed = False
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.is_pressed = True
            # context.window.cursor_modal_set('NONE')  # ! Hide cursor
            self.handler.pointer_down(context, event)

        context.window_manager.modal_handler_add(self)
        return OperatorReturn.RUNNING_MODAL


class ViewRollOperator(bpy.types.Operator):
    """Roll the view while mouse button is held down"""
    bl_idname = "navigation_puck.view_roll_modal"
    bl_label = "Roll View (Hold)"
    bl_options = {'REGISTER', 'UNDO'}

    handler = RollHandler()
    is_pressed: bool

    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Handle the modal event for rolling the view."""
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.is_pressed = True
            self.handler.pointer_down(context, event)
            return OperatorReturn.RUNNING_MODAL

        elif event.type == 'MOUSEMOVE' and self.is_pressed:
            self.handler.pointer_move(context, event)
            return OperatorReturn.RUNNING_MODAL

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self.is_pressed:
            self.is_pressed = False
            return OperatorReturn.FINISHED

        elif event.type == 'ESC':
            self.is_pressed = False
            return OperatorReturn.CANCELLED

        elif not self.is_pressed and event.type in {'RIGHTMOUSE'} and event.value == 'PRESS':
            return OperatorReturn.CANCELLED

        return OperatorReturn.RUNNING_MODAL

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Invoke the modal operator."""

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.is_pressed = True
            self.handler.pointer_down(context, event)
        else:
            self.is_pressed = False
        context.window_manager.modal_handler_add(self)  # type: ignore
        return OperatorReturn.RUNNING_MODAL


class ViewZoomOperator(bpy.types.Operator):
    """Zoom the view while mouse button is held down"""
    bl_idname = "navigation_puck.view_zoom_modal"
    bl_label = "Zoom View (Hold)"
    bl_options = {'REGISTER', 'UNDO'}

    handler = ZoomHandler()
    is_pressed: bool

    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Handle the modal event for zooming the view."""

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.is_pressed = True
            self.handler.pointer_down(context, event)
            return OperatorReturn.RUNNING_MODAL

        elif event.type == 'MOUSEMOVE' and self.is_pressed:
            self.handler.pointer_move(context, event)
            return OperatorReturn.RUNNING_MODAL

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self.is_pressed:
            self.is_pressed = False
            return OperatorReturn.FINISHED

        elif event.type == 'ESC':
            self.is_pressed = False
            return OperatorReturn.CANCELLED

        elif not self.is_pressed and event.type in {'RIGHTMOUSE'} and event.value == 'PRESS':
            return OperatorReturn.CANCELLED

        return OperatorReturn.RUNNING_MODAL

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Invoke the modal operator."""

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.is_pressed = True
            self.handler.pointer_down(context, event)
        else:
            self.is_pressed = False
        context.window_manager.modal_handler_add(self)  # type: ignore
        return OperatorReturn.RUNNING_MODAL


class ViewOrbitOperator(bpy.types.Operator):
    """Orbit the view vertically while mouse button is held down"""
    bl_idname = "navigation_puck.view_orbit_modal"
    bl_label = "Orbit Vertical (Hold)"
    bl_options = {'REGISTER', 'UNDO'}

    handler = OrbitHandler()
    is_pressed: bool

    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Handle the modal event for orbiting the view."""

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.is_pressed = True
            self.handler.pointer_down(context, event)
            return OperatorReturn.RUNNING_MODAL

        elif event.type == 'MOUSEMOVE' and self.is_pressed:
            self.handler.pointer_move(context, event)
            return OperatorReturn.RUNNING_MODAL

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self.is_pressed:
            self.is_pressed = False
            return OperatorReturn.FINISHED

        elif event.type == 'ESC':
            self.is_pressed = False
            return OperatorReturn.CANCELLED

        elif not self.is_pressed and event.type in {'RIGHTMOUSE'} and event.value == 'PRESS':
            return OperatorReturn.CANCELLED

        return OperatorReturn.RUNNING_MODAL

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Invoke the modal operator."""

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.is_pressed = True
            self.handler.pointer_down(context, event)
        else:
            self.is_pressed = False

        context.window_manager.modal_handler_add(self)  # type: ignore
        return OperatorReturn.RUNNING_MODAL


# Add to __init__.py classes tuple
classes = (
    ViewRollOperator,
    ViewPanOperator,
    ViewZoomOperator,
    ViewOrbitOperator,
)
