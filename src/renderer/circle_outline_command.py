"""
Creates a command to draw a circle outline using triangle segments.
"""

import dataclasses
import math

from .draw_protocol import DrawProtocol, UnwrapProtocol
from .flat_color_shader_command import FlatColorShaderCommand


@dataclasses.dataclass
class CircleOutlineCommand(DrawProtocol, UnwrapProtocol):
    """Command to draw a circular outline as a thin ring."""
    center: tuple[float, float]
    radius: float
    color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    width: float = 2.0
    segments: int = 48

    def unwrap(self) -> FlatColorShaderCommand:
        cx, cy = self.center
        radius = max(self.radius, self.width)
        inner_radius = max(radius - self.width, 0.0)
        segment_count = max(self.segments, 12)

        positions: list[tuple[float, float]] = []
        indices: list[tuple[int, int, int]] = []

        for index in range(segment_count):
            angle = (index / segment_count) * math.tau
            cos_angle = math.cos(angle)
            sin_angle = math.sin(angle)
            positions.append((cx + cos_angle * radius, cy + sin_angle * radius))
            positions.append((cx + cos_angle * inner_radius, cy + sin_angle * inner_radius))

        for index in range(segment_count):
            outer_current = index * 2
            inner_current = outer_current + 1 
            outer_next = ((index + 1) % segment_count) * 2
            inner_next = outer_next + 1
            indices.append((outer_current, outer_next, inner_next))
            indices.append((inner_next, inner_current, outer_current))

        return FlatColorShaderCommand(
            pos=positions,
            color=[self.color] * len(positions),
            indices=indices,
        )

    def draw(self):
        self.unwrap().draw()
