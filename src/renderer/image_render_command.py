"""
Defines a command to render an image using Blender's GPU module.
"""
import typing
import dataclasses
import bpy

from .buildin_vertices import RectangleVertices
from .draw_protocol import DrawProtocol, UnwrapProtocol
from .image_shader_command import ImageShaderCommand


@dataclasses.dataclass
class ImageRenderCommand(DrawProtocol, UnwrapProtocol):
    """Represents an image draw operation"""
    image: bpy.types.Image
    pos: tuple[float, float]
    size: typing.Optional[tuple[float, float]]
    opacity: float = 1.0
    
    def unwrap(self) -> ImageShaderCommand:
        image, pos = self.image, self.pos

        size = self.size or (float(image.size[0]), float(image.size[1]))

        return ImageShaderCommand(
            image=image,
            pos=RectangleVertices((pos[0], pos[1], size[0], size[1])),
            opacity=self.opacity,
        )

    def draw(self):
        self.unwrap().draw()
