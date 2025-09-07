"""
Enhanced UI Tools with ImGui-style event handling
This provides a drop-in replacement for the existing ui_tools with better event handling.
"""

import enum
import dataclasses
import math
import typing
import bpy

from ..imgui.ui import UI, WidgetResponse

from ..utils.operator_return import OperatorReturnType


@dataclasses.dataclass
class WidgetRect:
    """Simple rectangle class for any widget bounds"""
    rect: tuple[float, float, float, float] = (
        0.0, 0.0, 0.0, 0.0)  # x, y, width, height
    enable: bool = True

    @property
    def x(self) -> float:
        """X position of the button."""
        return self.rect[0]

    @property
    def y(self) -> float:
        """Y position of the button."""
        return self.rect[1]

    @property
    def width(self) -> float:
        """Width of the button."""
        return self.rect[2]

    @property
    def height(self) -> float:
        """Height of the button."""
        return self.rect[3]

    def contains_point(self, x: float, y: float) -> bool:
        """Check if this button contains the given point.

        Args:
            x (float): The x-coordinate of the point.
            y (float): The y-coordinate of the point.

        Returns:
            bool: True if the point is within the button's bounds, False otherwise.
        """
        return (self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height)


@dataclasses.dataclass
class Button:
    """Represents a clickable button in a widget.

    Attributes:
        label (str): The text label displayed on the button.
        icon (str): The icon associated with the button.
        callback (Optional[Callable[[Context, 'Button'], OperatorReturnType]]):
            The function to call when the button is clicked.
        icon_value (int): The numeric value of the icon for Blender's UI.
        rect (WidgetRect): The position and size of the button.
        data (Dict[str, Any]): Additional data associated with the button.
    """

    label: str
    icon: typing.Optional[bpy.types.Image] = None
    callback: typing.Optional[typing.Callable[[
        bpy.types.Context, 'Button'], OperatorReturnType]] = None
    icon_value: int = 0
    rect: WidgetRect = dataclasses.field(
        default_factory=lambda: WidgetRect(rect=(0.0, 0.0, 60.0, 60.0))
    )
    data: typing.Dict[str, typing.Any] = dataclasses.field(default_factory=dict)  # type: ignore


class LayoutType(enum.Enum):
    """Different layout types for widget buttons"""
    GRID = enum.auto()
    HORIZONTAL = enum.auto()
    VERTICAL = enum.auto()
    CIRCLE = enum.auto()
    CUSTOM = enum.auto()


class WidgetLayout:
    """Handles layout calculations for widget buttons"""

    def __init__(self, spacing: float = 0.0, layout_type: LayoutType = LayoutType.GRID):
        self.spacing = spacing
        self.layout_type = layout_type

    def set_spacing(self, spacing: float) -> typing.Self:
        """Set spacing between buttons"""
        self.spacing = spacing
        return self

    def set_layout_type(self, layout_type: LayoutType) -> typing.Self:
        """Set the layout type for arranging buttons"""
        self.layout_type = layout_type
        return self

    def calculate_positions(
        self,
        buttons: typing.List[Button],
        origin: tuple[float, float],
        button_size: tuple[float, float] = (60.0, 60.0)
    ) -> None:
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
                    buttons[i].rect.rect = (pos[0], pos[1], width, height)

        elif self.layout_type == LayoutType.HORIZONTAL:
            for i, button in enumerate(buttons):
                button.rect.rect = (
                    x + i * (width + spacing), y, width, height)

        elif self.layout_type == LayoutType.VERTICAL:
            for i, button in enumerate(buttons):
                button.rect.rect = (
                    x, y + i * (height + spacing), width, height)

        elif self.layout_type == LayoutType.CIRCLE:
            count = len(buttons)
            radius = max(width, height) * 1.5
            angle_step = 2 * math.pi / count

            for i, button in enumerate(buttons):
                angle = i * angle_step
                button.rect.rect = (
                    x + radius * math.cos(angle) - width/2,
                    y + radius * math.sin(angle) - height/2,
                    width,
                    height
                )

class EnhancedWidgetDrawer:
    """Enhanced widget drawer using ImGui system for better event handling"""

    def __init__(self):
        self.ui = UI()
        self.mouse_pos = (0.0, 0.0)
        self.responses: typing.Dict[str, WidgetResponse] = {}

    def handle_event(self, event: bpy.types.Event) -> bool:
        """Handle Blender event and return True if consumed by UI"""
        return self.ui.ctx.handle_event(event)

    def begin_frame(self, mouse_pos: tuple[float, float]):
        """Begin drawing frame - call before drawing widgets"""

        self.mouse_pos = mouse_pos
        self.ui.ctx.begin_frame(mouse_pos)
        self.responses.clear()

    def end_frame(self):
        """End drawing frame - call after drawing all widgets"""
        self.ui.ctx.end_frame()

    def draw_button(self, button: Button, widget_id: typing.Optional[str] = None) -> WidgetResponse:
        """Draw a single button using ImGui system"""
        if widget_id is None:
            widget_id = f"btn_{button.label}_{id(button)}"

        pos = (button.rect.x, button.rect.y)
        size = (button.rect.width, button.rect.height)

        if button.icon:
            response = self.ui.icon_button(button.icon, pos, size, widget_id)
        else:
            response = self.ui.button(button.label, pos, size, widget_id)

        self.responses[widget_id] = response

        # Execute callback if button was clicked
        if response.clicked and button.callback:
            try:
                result = button.callback(bpy.context, button)
                # Store result in button data for later use
                button.data['last_result'] = result
            except (TypeError, AttributeError) as e:
                print(f"Error executing button callback: {e}")

        return response

    def draw_widget(self, buttons: typing.List[Button]) -> typing.Dict[str, WidgetResponse]:
        """Draw all buttons in the widget and return responses"""
        responses: typing.Dict[str, WidgetResponse] = {}

        for i, button in enumerate(buttons):
            widget_id = f"widget_btn_{i}_{button.label}"
            response = self.draw_button(button, widget_id)
            responses[widget_id] = response

        return responses

    def get_hovered_button(self, buttons: typing.List[Button]) -> typing.Optional[Button]:
        """Get the currently hovered button, if any"""
        for button in buttons:
            if button.rect.contains_point(*self.mouse_pos):
                return button
        return None

    def get_button_response(self, widget_id: str) -> typing.Optional[WidgetResponse]:
        """Get the response for a specific button"""
        return self.responses.get(widget_id)


class WidgetDrawer(EnhancedWidgetDrawer):
    """Legacy widget drawer for backwards compatibility"""

    def __init__(self):
        super().__init__()
        self.background_color = (0.2, 0.2, 0.2, 0.9)
        self.button_color = (0.3, 0.3, 0.3, 1.0)
        self.button_hover_color = (0.4, 0.4, 0.6, 1.0)
        self.text_color = (1.0, 1.0, 1.0, 1.0)
        self.font_size = 14
        self.text_offset = (5, 15)

    def draw_widget(
        self,
        buttons: typing.List[Button],
        hovered_index: typing.Optional[int] = None
    ) -> typing.Dict[str, WidgetResponse]:
        """Legacy method for backwards compatibility"""
        responses: typing.Dict[str, WidgetResponse] = {}
        for i, button in enumerate(buttons):
            widget_id = f"legacy_btn_{i}_{button.label}"
            response = super().draw_button(button, widget_id)
            responses[widget_id] = response
        return responses


class ImGuiWidget:
    """Complete widget system using ImGui for event handling and rendering"""

    def __init__(
        self,
        origin: tuple[float, float] = (0.0, 0.0)
    ):
        self.layout = WidgetLayout()
        self.drawer = EnhancedWidgetDrawer()
        self.buttons: typing.List[Button] = []
        self.origin = origin
        self.visible = True

    def add_button(
        self,
        label: str,
        icon: bpy.types.Image,
        callback: typing.Optional[typing.Callable[[bpy.types.Context, Button], OperatorReturnType]] = None
    ) -> Button:
        """Add a button to the widget"""
        button = Button(label=label, icon=icon, callback=callback)
        self.buttons.append(button)
        return button

    def set_layout(
        self,
        layout_type: LayoutType,
        spacing: float = 4.0
    ) -> None:
        """Set the layout type and spacing"""
        self.layout.set_layout_type(layout_type).set_spacing(spacing)

    def update_layout(
        self,
        button_size: tuple[float, float] = (60.0, 60.0)
    ) -> None:
        """Update button positions based on current layout"""
        self.layout.calculate_positions(self.buttons, self.origin, button_size)

    def handle_event(
        self,
        event: bpy.types.Event
    ) -> bool:
        """Handle input event"""
        if not self.visible:
            return False
        return self.drawer.handle_event(event)

    def draw(
        self,
        mouse_pos: tuple[float, float]
    ) -> typing.Dict[str, WidgetResponse]:
        """Draw the widget and return button responses"""
        if not self.visible:
            return {}

        self.drawer.begin_frame(mouse_pos)
        responses = self.drawer.draw_widget(self.buttons)
        self.drawer.end_frame()

        return responses

    def get_clicked_buttons(self) -> typing.List[tuple[Button, WidgetResponse]]:
        """Get list of buttons that were clicked this frame"""
        clicked: typing.List[tuple[Button, WidgetResponse]] = []
        for widget_id, response in self.drawer.responses.items():
            if response.clicked:
                # Find the corresponding button
                for i, button in enumerate(self.buttons):
                    if widget_id.endswith(f"{i}_{button.label}"):
                        clicked.append((button, response))
                        break
        return clicked

    def set_visible(self, visible: bool) -> None:
        """Set widget visibility"""
        self.visible = visible

    def clear_buttons(self) -> None:
        """Clear all buttons"""
        self.buttons.clear()
