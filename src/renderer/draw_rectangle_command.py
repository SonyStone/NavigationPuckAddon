"""
Defines a command to draw rectangles using flat color shader
"""

import dataclasses

from .buildin_vertices import RectangleVertices

from .draw_protocol import DrawProtocol, UnwrapProtocol
from .flat_color_shader_command import FlatColorShaderCommand


@dataclasses.dataclass
class DrawRectangleCommand(DrawProtocol, UnwrapProtocol):
    """Represents a rectangle draw operation"""
    rect: tuple[float, float, float, float]
    color: tuple[float, float, float, float]

    def unwrap(self) -> FlatColorShaderCommand:
        """Convert to FlatColorShaderCommand"""
        rect, color = self.rect, self.color

        return FlatColorShaderCommand(
            pos=RectangleVertices(rect),
            color=[color] * 4,
        )

    def draw(self):
        """Draw a single rectangle immediately"""
        self.unwrap().draw()
