import typing
import bpy
import gpu
import gpu_extras

from ..utils.draw_handler import DrawHandler


from ..utils.operator_return import OperatorReturn, OperatorReturnType


class TestWidget(bpy.types.Operator):
    """The smallest possible test widget drawing a simple square"""
    bl_idname = "navigation_puck.test_widget"
    bl_label = "Test Widget"
    bl_options = {'REGISTER'}

    draw_handler = DrawHandler()
    mouse_pos = (0, 0)
    is_active = False

    @staticmethod
    def force_redraw(context: bpy.types.Context) -> None:
        """Force redraw of the 3D view"""
        if context.area:
            context.area.tag_redraw()

    # Override Operator method
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Start the modal operator and initialize widget"""

        if context.window_manager is None:
            return OperatorReturn.CANCELLED

        # ❗important
        context.window_manager.modal_handler_add(self)

        self.draw_handler.add(context, self.draw_callback)

        # setup
        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)
        self.initial_mouse_pos = self.mouse_pos

        self.is_active = True
        
        TestWidget.force_redraw(context)

        return OperatorReturn.RUNNING_MODAL

    # Override Operator method
    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Handle widget events"""
        print("💫 event.type", event.type, event.value)

        if event.type == 'Q':
            self.is_active = not self.is_active
            TestWidget.force_redraw(context)

        if event.type == 'LEFTMOUSE':
            self.draw_handler.remove()
            self.is_active = False
            TestWidget.force_redraw(context)

            return OperatorReturn.CANCELLED

        # TestWidget.force_redraw(context)
        return OperatorReturn.RUNNING_MODAL

    def draw_callback(self, op: typing.Any, context: bpy.types.Context) -> None:

        if not self.is_active:
            return

        # Shader to draw a simple square
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')

        x, y = self.mouse_pos
        width, height = 200, 200

        batch = gpu_extras.batch.batch_for_shader(  # type: ignore
            shader,
            'TRI_FAN',
            {
                "pos": [
                    (x, y), (x + width, y),
                    (x + width, y + height), (x, y + height)
                ]
            }
        )

        shader.bind()
        color =  (0.3, 0.3, 0.3, 1.0)
        shader.uniform_float("color", color)

        print("🫤 TestWidget::draw_callback")
        batch.draw(shader)  # type: ignore

