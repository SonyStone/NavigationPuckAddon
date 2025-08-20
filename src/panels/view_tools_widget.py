from enum import Enum, auto
from dataclasses import dataclass, field
import math
from bpy.types import Context, Operator, Event, SpaceView3D
from gpu.shader import from_builtin
from gpu_extras.batch import batch_for_shader
from typing import List, Tuple, Dict, Optional, Set, Literal, Callable, Any, TypeVar
import bpy
import blf

# ---------------------------------------------------------------------------- #
#                                  DATA MODELS                                  #
# ---------------------------------------------------------------------------- #

ModalReturnType = Set[Literal['RUNNING_MODAL',
                              'CANCELLED', 'FINISHED', 'PASS_THROUGH', 'INTERFACE']]
T = TypeVar('T', bound='BaseWidgetOperator')


@dataclass
class Button:
    """Represents a clickable button in a widget"""
    label: str
    icon: str = ''
    callback: Optional[Callable[[Context,
                                 'Button'], ModalReturnType]] = None
    icon_value: int = 0
    position: Tuple[float, float] = (0, 0)
    size: Tuple[float, float] = (60.0, 60.0)
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def x(self) -> float:
        return self.position[0]

    @property
    def y(self) -> float:
        return self.position[1]

    @property
    def width(self) -> float:
        return self.size[0]

    @property
    def height(self) -> float:
        return self.size[1]

    def contains_point(self, x: float, y: float) -> bool:
        """Check if this button contains the given point"""
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)


class LayoutType(Enum):
    """Different layout types for widget buttons"""
    GRID = auto()
    HORIZONTAL = auto()
    VERTICAL = auto()
    CIRCLE = auto()
    CUSTOM = auto()


class WidgetLayout:
    """Handles layout calculations for widget buttons"""

    def __init__(self, layout_type: LayoutType = LayoutType.GRID):
        self.layout_type = layout_type
        self.spacing = 8.0

    def calculate_positions(self, buttons: List[Button],
                            origin: Tuple[float, float],
                            button_size: Tuple[float, float] = (60.0, 60.0)) -> None:
        """Calculate positions for buttons based on the layout type and origin"""
        x, y = origin
        width, height = button_size
        spacing = self.spacing

        if self.layout_type == LayoutType.GRID:
            # Calculate a grid layout (2x2 in this case)
            positions = [
                (x - width - spacing/2, y - height - spacing/2),  # Bottom left
                (x + spacing/2, y - height - spacing/2),          # Bottom right
                (x - width - spacing/2, y + spacing/2),           # Top left
                (x + spacing/2, y + spacing/2)                    # Top right
            ]

            for i, pos in enumerate(positions):
                if i < len(buttons):
                    buttons[i].position = pos
                    buttons[i].size = (width, height)

        elif self.layout_type == LayoutType.HORIZONTAL:
            for i, button in enumerate(buttons):
                button.position = (x + i * (width + spacing), y)
                button.size = (width, height)

        elif self.layout_type == LayoutType.VERTICAL:
            for i, button in enumerate(buttons):
                button.position = (x, y + i * (height + spacing))
                button.size = (width, height)

        elif self.layout_type == LayoutType.CIRCLE:
            count = len(buttons)
            radius = max(width, height) * 1.5
            angle_step = 2 * math.pi / count

            for i, button in enumerate(buttons):
                angle = i * angle_step
                button.position = (
                    x + radius * math.cos(angle) - width/2,
                    y + radius * math.sin(angle) - height/2
                )
                button.size = (width, height)


class WidgetDrawer:
    """Handles drawing of widget buttons"""

    def __init__(self):
        self.background_color = (0.2, 0.2, 0.2, 0.9)
        self.button_color = (0.3, 0.3, 0.3, 1.0)
        self.button_hover_color = (0.4, 0.4, 0.6, 1.0)
        self.text_color = (1.0, 1.0, 1.0, 1.0)
        self.font_size = 14
        self.text_offset = (5, 15)

    def draw_button(self, button: Button, is_hovered: bool = False) -> None:
        """Draw a single button with background and text"""
        x, y = button.position
        width, height = button.size

        # Set up shader
        shader = from_builtin('UNIFORM_COLOR')

        # Determine button color (hover effect)
        color = self.button_hover_color if is_hovered else self.button_color

        # Draw button background
        batch = batch_for_shader(
            shader, 'TRI_FAN',
            {
                "pos": [
                    (x, y), (x + width, y),
                    (x + width, y + height), (x, y + height)
                ]
            }
        )
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)

        # Draw button text
        font_id = 0  # Default font
        blf.position(
            font_id, x + self.text_offset[0], y + self.text_offset[1], 0)
        blf.size(font_id, self.font_size)
        blf.color(font_id, *self.text_color)
        blf.draw(font_id, button.label)

    def draw_widget(self, buttons: List[Button], hovered_index: Optional[int] = None) -> None:
        """Draw all buttons in the widget"""
        for i, button in enumerate(buttons):
            self.draw_button(button, is_hovered=(i == hovered_index))


# ---------------------------------------------------------------------------- #
#                         BASE WIDGET OPERATOR FRAMEWORK                        #
# ---------------------------------------------------------------------------- #


class BaseWidgetOperator(Operator):
    """Base class for custom widget operators"""
    bl_idname = "view3d.base_widget"  # Will be overridden
    bl_label = "Base Widget"          # Will be overridden
    bl_options = {'REGISTER'}

    # Framework state
    active: bool = False
    mouse_pos: Tuple[float, float] = (0, 0)
    initial_mouse_pos: Tuple[float, float] = (0, 0)
    hovered_button: Optional[int] = None
    auto_dismiss_distance: float = 100.0
    handler = None

    # Customizable components
    widget_layout = WidgetLayout(LayoutType.GRID)
    drawer = WidgetDrawer()
    buttons: List[Button] = []

    @classmethod
    def setup_buttons(cls: type[T]) -> None:
        """Set up the buttons for this widget.
        Override in subclasses to define specific buttons."""
        pass

    def setup(self, context: Context, event: Event) -> None:
        """Set up the widget. Override in subclasses to customize."""
        pass

    def on_button_clicked(self, button: Button, context: Context) -> ModalReturnType:
        """Handle button click. Override in subclasses to customize behavior."""
        if button.callback:
            return button.callback(context, button)
        return {'FINISHED'}

    def on_cancel(self, context: Context) -> None:
        """Handle cancellation. Override in subclasses to customize."""
        pass

    def invoke(self, context: Context, event: Event) -> ModalReturnType:
        """Start the modal operator and initialize widget"""
        # Initialize class buttons if needed
        if not self.__class__.buttons:
            self.__class__.setup_buttons()

        # Initialize instance variables
        self.buttons = [Button(**b.__dict__) for b in self.__class__.buttons]
        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)
        self.initial_mouse_pos = self.mouse_pos

        # Call custom setup
        self.setup(context, event)

        # Calculate button positions
        self.widget_layout.calculate_positions(
            self.buttons,
            self.mouse_pos,
            (60.0, 60.0)  # Default button size
        )

        # Add draw handler
        args = (self, context)
        self.handler = SpaceView3D.draw_handler_add(
            self.draw_callback, args, 'WINDOW', 'POST_PIXEL')

        self.active = True
        context.window_manager.modal_handler_add(self)


        # Force an immediate redraw of the area
        if context.area:
            context.area.tag_redraw()

        return {'RUNNING_MODAL'}

    def modal(self, context: Context, event: Event) -> ModalReturnType:
        """Handle widget events"""
        # Update mouse position
        self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)

        # Update hover state
        if self._update_hovered_button(context) is not None:
            self._remove_handler()
            context.area.tag_redraw()
            return {'CANCELLED'}

        # Force redraw
        context.area.tag_redraw()

        # Handle mouse click
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if self.hovered_button is not None:
                button = self.buttons[self.hovered_button]
                self._remove_handler()
                return self.on_button_clicked(button, context)
            else:
                # If no button is clicked, we can auto-dismiss
                self._remove_handler()
                self.on_cancel(context)
                return {'CANCELLED'}

        # Cancel on right click or ESC
        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self._remove_handler()
            self.on_cancel(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def _update_hovered_button(self, context: Context) -> None | ModalReturnType:
        """Update which button is currently hovered"""
        x, y = self.mouse_pos

        for i, button in enumerate(self.buttons):
            if button.contains_point(x, y):
                self.hovered_button = i
                return

        # Check if we should auto-dismiss
        orig_x, orig_y = self.initial_mouse_pos
        distance = math.sqrt((x - orig_x)**2 + (y - orig_y)**2)
        if distance > self.auto_dismiss_distance:
            self._remove_handler()
            self.on_cancel(context)
            return {'CANCELLED'}

        self.hovered_button = None

    def _remove_handler(self) -> None:
        """Remove the draw handler"""
        if self.handler:
            SpaceView3D.draw_handler_remove(self.handler, 'WINDOW')
            self.handler = None
        self.active = False

    def draw_callback(self, op, context: Context) -> None:
        """Draw the widget"""
        if not self.active:
            return

        self.drawer.draw_widget(self.buttons, self.hovered_button)

    def cancel(self, context: Context) -> None:
        """Clean up when cancelled"""
        self._remove_handler()
        self.on_cancel(context)


# ---------------------------------------------------------------------------- #
#                         NAVIGATION PUCK VIEW TOOLS WIDGET                    #
# ---------------------------------------------------------------------------- #

def execute_view_pan(context: Context, button: Button) -> ModalReturnType:
    bpy.ops.navigation_puck.view_pan_modal('INVOKE_DEFAULT')
    return {'FINISHED'}


def execute_view_orbit(context: Context, button: Button) -> ModalReturnType:
    bpy.ops.navigation_puck.view_orbit_modal('INVOKE_DEFAULT')
    return {'FINISHED'}


def execute_view_zoom(context: Context, button: Button) -> ModalReturnType:
    bpy.ops.navigation_puck.view_zoom_modal('INVOKE_DEFAULT')
    return {'FINISHED'}


def execute_view_roll(context: Context, button: Button) -> ModalReturnType:
    bpy.ops.navigation_puck.view_roll_modal('INVOKE_DEFAULT')
    return {'FINISHED'}


class NAVIGATION_PUCK_OT_view_tools_widget(BaseWidgetOperator):
    """Display floating view tools widget at mouse position"""
    bl_idname = "navigation_puck.view_tools_widget"
    bl_label = "View Tools Widget"

    @classmethod
    def setup_buttons(cls) -> None:
        """Set up the view tool buttons"""
        cls.buttons = [
            Button(label="Pan", icon='VIEW_PAN', callback=execute_view_pan),
            Button(label="Orbit", icon='SPHERE', callback=execute_view_orbit),
            Button(label="Zoom", icon='VIEW_ZOOM', callback=execute_view_zoom),
            Button(label="Roll", icon='MESH_CIRCLE', callback=execute_view_roll)
        ]

    def setup(self, context: Context, event: Event) -> None:
        """Customize the widget appearance"""
        # Use a grid layout for the view tools
        self.widget_layout = WidgetLayout(LayoutType.GRID)
        self.widget_layout.spacing = 0.0
        self.widget_layout.layout_type = LayoutType.GRID

        # Customize the drawer appearance
        self.drawer.button_color = (0.3, 0.3, 0.3, 1.0)
        self.drawer.button_hover_color = (0.4, 0.4, 0.6, 1.0)


# Registration
classes = (
    NAVIGATION_PUCK_OT_view_tools_widget,
)
