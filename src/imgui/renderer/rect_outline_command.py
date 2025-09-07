"""
Creates a command to draw a rectangle outline using four rectangles.
"""

import dataclasses

from .draw_protocol import DrawProtocol, UnwrapProtocol
from .flat_color_shader_command import FlatColorShaderCommand
from .buildin_vertices import RectangleVertices, OutlineVertices, RectangleIndices, OutlineIndices

@dataclasses.dataclass
class RectOutlineCommand(DrawProtocol, UnwrapProtocol):
    """Command to draw a rectangle outline using four rectangles"""
    rect: tuple[float, float, float, float] = (0, 0, 100, 100)
    outline_color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    fill_color: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    outline_width: float = 1.0

    def unwrap(self) -> FlatColorShaderCommand:
        """Convert to FlatColorShaderCommand"""

        rect, outline_color, fill_color, outline_width = self.rect, self.outline_color, self.fill_color, self.outline_width

        return FlatColorShaderCommand(
            pos=RectangleVertices(rect, outline_width) + OutlineVertices(rect, outline_width),
            color=[fill_color] * RectangleIndices.offset_size() + [outline_color] * OutlineIndices.offset_size(),
            indices=RectangleIndices(0) + OutlineIndices(4)
        )

    def draw(self):
        self.unwrap().draw()
