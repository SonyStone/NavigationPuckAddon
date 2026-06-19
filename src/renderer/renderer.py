"""
High-level interface for drawing operations with batching support
"""
import typing
import bpy

from .draw_protocol import DrawProtocol
from .image_render_command import ImageRenderCommand
from .text_renderer_command import TextRendererCommand

from .renderer_batch import RendererBatch
from .rect_outline_command import RectOutlineCommand


class Renderer:
    """High-level interface for drawing operations with batching support"""

    def __init__(self):
        self.batch = RendererBatch()

    def draw(self):
        """Execute all batched draw operations"""
        self.batch.draw()
        
    def add(
        self,
        draw_call: DrawProtocol
    ):
        """Add a draw call to the batch"""
        self.batch.add(draw_call)


    def add_rect_outline(
        self,
        rect: tuple[float, float, float, float],
        outline_color: tuple[float, float, float, float],
        fill_color: tuple[float, float, float, float],
        width: float = 1.0
    ):
        """Draw rectangle outline as four separate rectangles"""

        self.batch.add(RectOutlineCommand(rect, outline_color, fill_color, width))

    def add_text(
        self,
        text: str,
        pos: tuple[float, float],
        color: tuple[float, float, float, float]
    ):
        """Draw text at the specified position"""
        self.batch.add(TextRendererCommand(text, pos, color))

    def add_image(
        self,
        image: bpy.types.Image,
        pos: tuple[float, float],
        size: typing.Optional[tuple[float, float]] = None,
        opacity: float = 1.0
    ):
        """Draw an image at the specified position"""
        self.batch.add(ImageRenderCommand(image, pos, size, opacity))
