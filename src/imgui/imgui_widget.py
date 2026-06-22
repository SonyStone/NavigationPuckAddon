"""
Enhanced UI Tools with ImGui-style event handling
This provides reusable widget helpers on top of the immediate-mode UI system.
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

    def _calculate_grid_positions(
        self,
        origin: tuple[float, float],
        button_size: tuple[float, float],
    ) -> tuple[tuple[float, float], ...]:
        x, y = origin
        width, height = button_size
        half_spacing = self.spacing / 2
        return (
            (x - width - half_spacing, y - height - half_spacing),
            (x + half_spacing, y - height - half_spacing),
            (x - width - half_spacing, y + half_spacing),
            (x + half_spacing, y + half_spacing),
        )

    def _apply_grid_layout(
        self,
        buttons: typing.List[Button],
        origin: tuple[float, float],
        button_size: tuple[float, float],
    ) -> None:
        width, height = button_size
        for button, position in zip(buttons, self._calculate_grid_positions(origin, button_size)):
            button.rect.rect = (position[0], position[1], width, height)

    def _apply_horizontal_layout(
        self,
        buttons: typing.List[Button],
        origin: tuple[float, float],
        button_size: tuple[float, float],
    ) -> None:
        x, y = origin
        width, height = button_size
        for index, button in enumerate(buttons):
            button.rect.rect = (x + index * (width + self.spacing), y, width, height)

    def _apply_vertical_layout(
        self,
        buttons: typing.List[Button],
        origin: tuple[float, float],
        button_size: tuple[float, float],
    ) -> None:
        x, y = origin
        width, height = button_size
        for index, button in enumerate(buttons):
            button.rect.rect = (x, y + index * (height + self.spacing), width, height)

    def _apply_circle_layout(
        self,
        buttons: typing.List[Button],
        origin: tuple[float, float],
        button_size: tuple[float, float],
    ) -> None:
        x, y = origin
        width, height = button_size
        count = len(buttons)
        radius = max(width, height) * 1.5
        angle_step = 2 * math.pi / count

        for index, button in enumerate(buttons):
            angle = index * angle_step
            button.rect.rect = (
                x + radius * math.cos(angle) - width / 2,
                y + radius * math.sin(angle) - height / 2,
                width,
                height,
            )

    def _layout_handlers(
        self,
    ) -> dict[LayoutType, typing.Callable[[typing.List[Button], tuple[float, float], tuple[float, float]], None]]:
        return {
            LayoutType.GRID: self._apply_grid_layout,
            LayoutType.HORIZONTAL: self._apply_horizontal_layout,
            LayoutType.VERTICAL: self._apply_vertical_layout,
            LayoutType.CIRCLE: self._apply_circle_layout,
        }

    def calculate_positions(
        self,
        buttons: typing.List[Button],
        origin: tuple[float, float],
        button_size: tuple[float, float] = (60.0, 60.0)
    ) -> None:
        """Calculate positions for buttons based on the layout type and origin"""
        handler = self._layout_handlers().get(self.layout_type)
        if handler is not None:
            handler(buttons, origin, button_size)

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
        self.ui.begin_frame(mouse_pos)
        self.responses.clear()

    def end_frame(self):
        """End drawing frame - call after drawing all widgets"""
        self.ui.end_frame()

    @staticmethod
    def _button_widget_id(button: Button, widget_id: typing.Optional[str]) -> str:
        if widget_id is not None:
            return widget_id
        return f"btn_{button.label}_{id(button)}"

    @staticmethod
    def _button_rect_args(button: Button) -> tuple[tuple[float, float], tuple[float, float]]:
        return (
            (button.rect.x, button.rect.y),
            (button.rect.width, button.rect.height),
        )

    def _draw_button_control(self, button: Button, widget_id: str) -> WidgetResponse:
        pos, size = self._button_rect_args(button)
        if button.icon:
            return self.ui.icon_button(button.icon, pos, size, widget_id)
        return self.ui.button(button.label, pos, size, widget_id)

    @staticmethod
    def _run_button_callback(button: Button) -> None:
        if not button.callback:
            return

        try:
            result = button.callback(bpy.context, button)
            button.data['last_result'] = result
        except (TypeError, AttributeError) as e:
            print(f"Error executing button callback: {e}")

    def draw_button(self, button: Button, widget_id: typing.Optional[str] = None) -> WidgetResponse:
        """Draw a single button using ImGui system"""
        widget_id = self._button_widget_id(button, widget_id)
        response = self._draw_button_control(button, widget_id)
        self.responses[widget_id] = response

        if response.clicked:
            self._run_button_callback(button)

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

    def _button_for_widget_id(self, widget_id: str) -> Button | None:
        for index, button in enumerate(self.buttons):
            if widget_id.endswith(f"{index}_{button.label}"):
                return button
        return None

    def get_clicked_buttons(self) -> typing.List[tuple[Button, WidgetResponse]]:
        """Get list of buttons that were clicked this frame"""
        clicked: typing.List[tuple[Button, WidgetResponse]] = []
        for widget_id, response in self.drawer.responses.items():
            if not response.clicked:
                continue

            button = self._button_for_widget_id(widget_id)
            if button is not None:
                clicked.append((button, response))
        return clicked

    def set_visible(self, visible: bool) -> None:
        """Set widget visibility"""
        self.visible = visible

    def clear_buttons(self) -> None:
        """Clear all buttons"""
        self.buttons.clear()
