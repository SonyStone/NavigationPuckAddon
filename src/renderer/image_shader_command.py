"""
Defines a command to render an image using Blender's GPU module.
"""
import typing
import dataclasses
import gpu
import bpy
from gpu_extras.batch import batch_for_shader

from .draw_protocol import DrawProtocol

_IMAGE_OPACITY_SHADER: gpu.types.GPUShader | None = None
_IMAGE_OPACITY_SHADER_FAILED = False
IMAGE_OPACITY_VERTEX_SHADER = """
    uniform mat4 ModelViewProjectionMatrix;
    in vec2 pos;
    in vec2 texCoord;
    out vec2 texCoord_interp;

    void main()
    {
        texCoord_interp = texCoord;
        gl_Position = ModelViewProjectionMatrix * vec4(pos.xy, 0.0, 1.0);
    }
"""
IMAGE_OPACITY_FRAGMENT_SHADER = """
    uniform sampler2D image;
    uniform float opacity;
    in vec2 texCoord_interp;
    out vec4 fragColor;

    void main()
    {
        vec4 color = texture(image, texCoord_interp);
        fragColor = vec4(color.rgb, color.a * opacity);
    }
"""


def get_image_opacity_shader() -> gpu.types.GPUShader | None:
    """Create the image shader used when an icon needs alpha fading."""
    global _IMAGE_OPACITY_SHADER, _IMAGE_OPACITY_SHADER_FAILED
    if _IMAGE_OPACITY_SHADER_FAILED:
        return None

    if _IMAGE_OPACITY_SHADER is None:
        try:
            _IMAGE_OPACITY_SHADER = gpu.types.GPUShader(IMAGE_OPACITY_VERTEX_SHADER, IMAGE_OPACITY_FRAGMENT_SHADER)
        except Exception as ex:
            _IMAGE_OPACITY_SHADER_FAILED = True
            print(f"Image opacity shader disabled: {ex}")
            return None
    return _IMAGE_OPACITY_SHADER


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
    opacity: float = 1.0

    def draw(self):
        """Draw the image using the IMAGE shader"""
        if self.opacity <= 0.0:
            return

        self.image.gl_load()

        # Set up GPU state for image rendering
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('NONE')

        opacity_shader = None if self.opacity >= 1.0 else get_image_opacity_shader()
        shader = opacity_shader or gpu.shader.from_builtin('IMAGE')

        batch = batch_for_shader(  # type: ignore
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
        if opacity_shader:
            shader.uniform_float("opacity", self.opacity)
        batch.draw(shader)
