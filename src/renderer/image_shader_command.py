"""
Defines a command to render an image using Blender's GPU module.
"""
import typing
import dataclasses
import gpu
import gpu_extras
import bpy

from .draw_protocol import DrawProtocol


@dataclasses.dataclass
class ImageShaderCommand(DrawProtocol):
    """Wrapper for IMAGE shader"""

    image: bpy.types.Image
    pos: typing.Sequence[float] | typing.Sequence[typing.Sequence[float]] = (
        (0, 0),
        (1, 0),
        (1, 1),
        (0, 1)
    )
    tex_coord: typing.Sequence[float] | typing.Sequence[typing.Sequence[float]] = (
        (0, 0),  # Top-left
        (1, 0),  # Top-right
        (1, 1),  # Bottom-right
        (0, 1),  # Bottom-left
    )
    indices: typing.Sequence[float] | typing.Sequence[typing.Sequence[float]] = (
        (0, 1, 2), (2, 3, 0))

    def draw(self):
        """Draw the image using the IMAGE shader"""
        self.image.gl_load()

        # Set up GPU state for image rendering
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('NONE')

        shader = gpu.shader.from_builtin('IMAGE')

        batch = gpu_extras.batch.batch_for_shader(  # type: ignore
            shader, 'TRIS',
            {
                "pos": self.pos,
                "texCoord": self.tex_coord
            },
            indices=self.indices
        )

        texture = gpu.texture.from_image(self.image)
        shader.bind()
        shader.uniform_sampler("image", texture)
        batch.draw(shader)
