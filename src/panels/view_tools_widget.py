import bpy
import gpu
import blf
import mathutils
import math
from gpu_extras.batch import batch_for_shader
from typing import List, Tuple, Dict, Optional, ClassVar, Set, Literal

ModalReturnType = Set[Literal['RUNNING_MODAL',
                              'CANCELLED', 'FINISHED', 'PASS_THROUGH', 'INTERFACE']]


class HEAVYPOLY_OT_view_tools_widget(bpy.types.Operator):
    """Display floating view tools widget at mouse position"""
    bl_idname = "heavypoly.view_tools_widget"
    bl_label = "View Tools Widget"
    bl_options = {'REGISTER'}

    # Button configuration
    buttons: ClassVar[List[Dict]] = [
        {"label": "Pan", "icon": 'VIEW_PAN',
            "operator": "heavypoly.view_pan_modal", "position": (0, 0)},
        {"label": "Orbit", "icon": 'SPHERE',
            "operator": "heavypoly.view_orbit_modal", "position": (0, 0)},
        {"label": "Zoom", "icon": 'VIEW_ZOOM',
            "operator": "heavypoly.view_zoom_modal", "position": (0, 0)},
        {"label": "Roll", "icon": 'MESH_CIRCLE',
            "operator": "heavypoly.view_roll_modal", "position": (0, 0)}
    ]

    # Widget appearance
    button_size: ClassVar[float] = 40.0
    button_spacing: ClassVar[float] = 2.0
    background_color: ClassVar[Tuple[float, float, float, float]] = (
        0.2, 0.2, 0.2, 0.9)
    button_color: ClassVar[Tuple[float, float, float, float]] = (
        0.3, 0.3, 0.3, 1.0)
    button_hover_color: ClassVar[Tuple[float, float, float, float]] = (
        0.4, 0.4, 0.6, 1.0)
    text_color: ClassVar[Tuple[float, float, float, float]] = (
        1.0, 1.0, 1.0, 1.0)

    # Runtime state
    mouse_pos: Tuple[int, int] = (0, 0)
    hovered_button: Optional[int] = None
    active: bool = False
    handler = None

    def invoke(self, context, event):
        """Start the modal operator and initialize widget position"""
        # Store initial mouse position
        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)
        self._initial_mouse_pos = self.mouse_pos

        # Calculate button positions
        self._calculate_button_positions()

        # Add draw handler
        args = (self, context)
        self.handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback, args, 'WINDOW', 'POST_PIXEL')

        self.active = True
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _calculate_button_positions(self):
        """Calculate positions for each button based on mouse position"""
        x, y = self.mouse_pos

        # 2×2 Grid layout
        positions = [
            (x - self.button_size - self.button_spacing/2, y -
             self.button_size - self.button_spacing/2),  # Bottom left
            (x + self.button_spacing/2, y - self.button_size -
             self.button_spacing/2),  # Bottom right
            (x - self.button_size - self.button_spacing /
             2, y + self.button_spacing/2),  # Top left
            (x + self.button_spacing/2, y + self.button_spacing/2)  # Top right
        ]

        # Update button positions
        for i, pos in enumerate(positions):
            if i < len(self.buttons):
                self.buttons[i]["position"] = pos

    def modal(self, context, event):
        """Handle events for the widget"""
        # Update mouse position
        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)

        # Update hover state
        self.hovered_button = self._get_hovered_button()

        # Force redraw
        context.area.tag_redraw()

        # Handle mouse click
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if self.hovered_button is not None:
                # Get the clicked button
                button = self.buttons[self.hovered_button]

                # Clean up
                self._remove_handler()

                # Execute the corresponding operator
                operator_id = button["operator"]
                category, name = operator_id.split('.')
                op = getattr(bpy.ops, category)
                getattr(op, name)('INVOKE_DEFAULT')

                return {'FINISHED'}

        # Cancel on right click or ESC
        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self._remove_handler()
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def _get_hovered_button(self) -> Optional[int]:
        """Determine which button the mouse is hovering over"""
        x, y = self.mouse_pos

        for i, button in enumerate(self.buttons):
            btn_x, btn_y = button["position"]

            # Check if mouse is inside button bounds
            if (btn_x <= x <= btn_x + self.button_size and
                    btn_y <= y <= btn_y + self.button_size):
                return i

        # If we're here, mouse isn't hovering any button
        # Consider auto-dismissing if mouse moves too far from original position
        orig_x, orig_y = self._initial_mouse_pos  # Store this in invoke()
        dist = math.sqrt((orig_x - x)**2 + (orig_y - y)**2)
        if dist > 100:  # Arbitrary threshold
            self._remove_handler()
            return None

        return None

    def _remove_handler(self):
        """Remove the draw handler"""
        if self.handler:
            bpy.types.SpaceView3D.draw_handler_remove(self.handler, 'WINDOW')
            self.handler = None
        self.active = False

    def draw_callback(self, op, context):
        """Draw the custom widget"""
        if not self.active:
            return

        # Set up shader
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')

        # Draw buttons
        for i, button in enumerate(self.buttons):
            x, y = button["position"]

            # Determine button color (hover effect)
            color = self.button_hover_color if i == self.hovered_button else self.button_color

            # Draw button background
            batch = batch_for_shader(
                shader, 'TRI_FAN',
                {
                    "pos": [(x, y), (x + self.button_size, y),
                            (x + self.button_size, y + self.button_size), (x, y + self.button_size)]
                }
            )
            shader.bind()
            shader.uniform_float("color", color)
            batch.draw(shader)

            # Draw button text
            font_id = 0  # Default font
            blf.position(font_id, x + 5, y + 15, 0)
            blf.size(font_id, 14)
            blf.color(font_id, *self.text_color)
            blf.draw(font_id, button["label"])

    def cancel(self, context):
        """Handle cleanup when operator is cancelled"""
        self._remove_handler()


classes = (
    HEAVYPOLY_OT_view_tools_widget,
)
