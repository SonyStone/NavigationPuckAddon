
import enum
import dataclasses
import math
import typing
import bpy
import blf
import gpu
import gpu_extras

from ..utils.operator_return import OperatorReturnType

@dataclasses.dataclass
class WidgetRect:
    """Simple rectangle class for any widget bounds"""
    rect: typing.Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)  # x, y, width, height
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
        position (Tuple[float, float]): The (x, y) position of the button.
        size (Tuple[float, float]): The (width, height) dimensions of the button.
        data (Dict[str, Any]): Additional data associated with the button.
    """

    label: str
    icon: str = ''
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

    spacing = 0.0
    layout_type = LayoutType.GRID

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
        origin: typing.Tuple[float, float],
        button_size: typing.Tuple[float, float] = (60.0, 60.0)
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
                button.rect.rect = (x + i * (width + spacing), y, width, height)

        elif self.layout_type == LayoutType.VERTICAL:
            for i, button in enumerate(buttons):
                button.rect.rect = (x, y + i * (height + spacing), width, height)

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

    def hovered(self) -> bool:
        """Check if any button is hovered (placeholder)"""
        return False


class WidgetDrawer:
    """Handles drawing of widget buttons"""

    background_color = (0.2, 0.2, 0.2, 0.9)
    button_color = (0.3, 0.3, 0.3, 1.0)
    button_hover_color = (0.4, 0.4, 0.6, 1.0)
    text_color = (1.0, 1.0, 1.0, 1.0)
    font_size = 14
    text_offset = (5, 15)

    def draw_button(self, button: Button, is_hovered: bool = False) -> None:
        """Draw a single button with background and text"""
        x, y, width, height = button.rect.rect

        # Set up shader
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')

        # Determine button color (hover effect)
        color = self.button_hover_color if is_hovered else self.button_color

        # Draw button background
        batch = gpu_extras.batch.batch_for_shader(  # type: ignore
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
        batch.draw(shader)  # type: ignore

        # Draw button text
        font_id = 0  # Default font
        blf.position(
            font_id, x + self.text_offset[0], y + self.text_offset[1], 0)
        blf.size(font_id, self.font_size)
        blf.color(font_id, *self.text_color)
        blf.draw(font_id, button.label)

    def draw_widget(self, buttons: typing.List[Button], hovered_index: typing.Optional[int] = None) -> None:
        """Draw all buttons in the widget"""
        for i, button in enumerate(buttons):
            self.draw_button(button, is_hovered=(i == hovered_index))
