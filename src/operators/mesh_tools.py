# pyright: reportPrivateImportUsage=none

from typing import final, TYPE_CHECKING, Set, Literal, ClassVar
import bpy

from .view_handlers import PanHandler, RollHandler, ViewOrbitHandler, ZoomHandler

if TYPE_CHECKING:
    from bpy._typing import rna_enums


class HEAVYPOLY_OT_smart_extrude(bpy.types.Operator):
    """Smart extrusion tool"""
    bl_idname = "heavypoly.smart_extrude"
    bl_label = "Smart Extrude"
    bl_options = {'REGISTER', 'UNDO'}

    @final
    def execute(self, context: bpy.types.Context) -> set["rna_enums.OperatorReturnItems"]:

        self.report({"INFO"}, "Smart extrude executed")
        return {"FINISHED"}


ModalReturnType = Set[Literal['RUNNING_MODAL',
                              'CANCELLED', 'FINISHED', 'PASS_THROUGH', 'INTERFACE']]


class ViewPanOperator(bpy.types.Operator):
    """Pan the view while mouse button is held down"""
    bl_idname: ClassVar[str] = "heavypoly.view_pan_modal"
    bl_label: ClassVar[str] = "Pan View (Hold)"
    bl_options: ClassVar[Set[str]] = {'REGISTER', 'UNDO'}

    handler: ClassVar[PanHandler] = PanHandler()
    is_pressed: bool

    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> ModalReturnType:
        """Handle the modal event for panning the view."""

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.is_pressed = True
            self.handler.pointer_down(context, event)
            return {'RUNNING_MODAL'}

        elif event.type == 'MOUSEMOVE' and self.is_pressed:
            self.handler.pointer_move(context, event)
            return {'RUNNING_MODAL'}

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self.is_pressed:
            self.is_pressed = False
            return {'FINISHED'}

        elif event.type == 'ESC':
            self.is_pressed = False
            return {'CANCELLED'}

        elif not self.is_pressed and event.type in {'RIGHTMOUSE'} and event.value == 'PRESS':
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> ModalReturnType:
        """Invoke the modal operator."""

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.is_pressed = True
            self.handler.pointer_down(context, event)
        else:
            self.is_pressed = False
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class ViewRollOperator(bpy.types.Operator):
    """Roll the view while mouse button is held down"""
    bl_idname: ClassVar[str] = "heavypoly.view_roll_modal"
    bl_label: ClassVar[str] = "Roll View (Hold)"
    bl_options: ClassVar[Set[str]] = {'REGISTER', 'UNDO'}

    handler: ClassVar[RollHandler] = RollHandler()
    is_pressed: bool

    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> ModalReturnType:
        """Handle the modal event for rolling the view."""
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.is_pressed = True
            self.handler.pointer_down(context, event)
            return {'RUNNING_MODAL'}

        elif event.type == 'MOUSEMOVE' and self.is_pressed:
            self.handler.pointer_move(context, event)
            return {'RUNNING_MODAL'}

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self.is_pressed:
            self.is_pressed = False
            return {'FINISHED'}

        elif event.type == 'ESC':
            self.is_pressed = False
            return {'CANCELLED'}

        elif not self.is_pressed and event.type in {'RIGHTMOUSE'} and event.value == 'PRESS':
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> ModalReturnType:
        """Invoke the modal operator."""

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.is_pressed = True
            self.handler.pointer_down(context, event)
        else:
            self.is_pressed = False
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class ViewZoomOperator(bpy.types.Operator):
    """Zoom the view while mouse button is held down"""
    bl_idname: ClassVar[str] = "heavypoly.view_zoom_modal"
    bl_label: ClassVar[str] = "Zoom View (Hold)"
    bl_options: ClassVar[Set[str]] = {'REGISTER', 'UNDO'}

    handler: ClassVar[ZoomHandler] = ZoomHandler()
    is_pressed: bool

    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> ModalReturnType:
        """Handle the modal event for zooming the view."""

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.is_pressed = True
            self.handler.pointer_down(context, event)
            return {'RUNNING_MODAL'}

        elif event.type == 'MOUSEMOVE' and self.is_pressed:
            self.handler.pointer_move(context, event)
            return {'RUNNING_MODAL'}

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self.is_pressed:
            self.is_pressed = False
            return {'FINISHED'}

        elif event.type == 'ESC':
            self.is_pressed = False
            return {'CANCELLED'}

        elif not self.is_pressed and event.type in {'RIGHTMOUSE'} and event.value == 'PRESS':
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> ModalReturnType:
        """Invoke the modal operator."""

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.is_pressed = True
            self.handler.pointer_down(context, event)
        else:
            self.is_pressed = False
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class ViewOrbitOperator(bpy.types.Operator):
    """Orbit the view vertically while mouse button is held down"""
    bl_idname: ClassVar[str] = "heavypoly.view_orbit_modal"
    bl_label: ClassVar[str] = "Orbit Vertical (Hold)"
    bl_options: ClassVar[Set[str]] = {'REGISTER', 'UNDO'}

    handler: ClassVar[ViewOrbitHandler] = ViewOrbitHandler()
    is_pressed: bool

    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> ModalReturnType:
        """Handle the modal event for orbiting the view."""

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.is_pressed = True
            self.handler.pointer_down(context, event)
            return {'RUNNING_MODAL'}

        elif event.type == 'MOUSEMOVE' and self.is_pressed:
            self.handler.pointer_move(context, event)
            return {'RUNNING_MODAL'}

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self.is_pressed:
            self.is_pressed = False
            return {'FINISHED'}

        elif event.type == 'ESC':
            self.is_pressed = False
            return {'CANCELLED'}

        elif not self.is_pressed and event.type in {'RIGHTMOUSE'} and event.value == 'PRESS':
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> ModalReturnType:
        """Invoke the modal operator."""

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.is_pressed = True
            self.handler.pointer_down(context, event)
        else:
            self.is_pressed = False

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


# Add to __init__.py classes tuple
classes = (
    HEAVYPOLY_OT_smart_extrude,
    ViewRollOperator,
    ViewPanOperator,
    ViewZoomOperator,
    ViewOrbitOperator,
)
