"""
Defines a command to render flat colored shapes using Blender's GPU module.
"""
import typing
import dataclasses
import gpu
import gpu_extras

from .buildin_vertices import RectangleIndices, RectangleVertices
from .draw_protocol import DrawProtocol


@dataclasses.dataclass
class FlatColorShaderCommand(DrawProtocol):
    """Wrapper for FLAT_COLOR shader"""

    pos: typing.Sequence[float] | typing.Sequence[typing.Sequence[float]] = dataclasses.field(default_factory=RectangleVertices)
    color: typing.Sequence[float] | typing.Sequence[typing.Sequence[float]] = (
        (1.0, 0.0, 0.0, 1.0),
        (0.0, 1.0, 0.0, 1.0),
        (0.0, 0.0, 1.0, 1.0),
        (1.0, 1.0, 0.0, 1.0)
    )
    indices: typing.Sequence[float] | typing.Sequence[typing.Sequence[float]] = dataclasses.field(default_factory=RectangleIndices)

    def draw(self):
        """Draw the rectangle using the FLAT_COLOR shader"""
        shader: gpu.types.GPUShader = gpu.shader.from_builtin('FLAT_COLOR')

        batch = gpu_extras.batch.batch_for_shader(  # type: ignore
            shader,
            'TRIS',
            {
                "pos": self.pos,  # type: ignore
                "color": self.color
            },
            indices=self.indices
        )

        shader.bind()
        batch.draw(shader)

    def __add__(self, other: 'FlatColorShaderCommand') -> 'FlatColorShaderCommand':
        biggest_index = max(max(tri) for tri in self.indices)  # type: ignore
        other_indices_offset = list(tuple( # type: ignore
            index + biggest_index + 1 for index in tri) for tri in other.indices)  # type: ignore
        
        return FlatColorShaderCommand(
            pos=self.pos + other.pos,  # type: ignore
            color=self.color + other.color,  # type: ignore
            indices=self.indices + other_indices_offset  # type: ignore
        )
