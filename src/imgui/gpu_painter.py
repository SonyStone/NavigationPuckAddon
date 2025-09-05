
import typing
import blf
import gpu
import gpu_extras

from . import Rect, Theme


class GPUPainter:
    """Handles drawing operations"""

    def __init__(self, theme: Theme):
        self.theme = theme

    def draw_rect(
        self,
        rect: Rect,
        color: typing.Tuple[float, float, float, float]
    ):
        """Draw filled rectangle"""
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')

        batch = gpu_extras.batch.batch_for_shader(  # type: ignore
            shader, 'TRI_FAN',
            {
                "pos": [
                    (rect.x, rect.y),
                    (rect.x + rect.width, rect.y),
                    (rect.x + rect.width, rect.y + rect.height),
                    (rect.x, rect.y + rect.height)
                ]
            }
        )

        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)  # type: ignore

    def draw_rect_outline(
        self,
        rect: Rect,
        color: typing.Tuple[float, float, float, float],
        width: float = 1.0
    ):
        """Draw rectangle outline"""
        # Draw outline as four rectangles
        # Top
        self.draw_rect(Rect(rect.x, rect.y + rect.height -
                       width, rect.width, width), color)
        # Bottom
        self.draw_rect(Rect(rect.x, rect.y, rect.width, width), color)
        # Left
        self.draw_rect(Rect(rect.x, rect.y, width, rect.height), color)
        # Right
        self.draw_rect(Rect(rect.x + rect.width - width,
                       rect.y, width, rect.height), color)

    def draw_text(
        self,
        text: str,
        pos: typing.Tuple[float, float],
        color: typing.Tuple[float, float, float, float]
    ):
        """Draw text at position"""
        font_id = 0
        blf.position(font_id, pos[0], pos[1], 0)
        blf.size(font_id, self.theme.font_size)
        blf.color(font_id, *color)
        blf.draw(font_id, text)

    def draw_image(self, image: typing.Any, pos: typing.Tuple[float, float]):
        """Draw image at position"""
        pass


    def get_text_size(self, text: str) -> typing.Tuple[float, float]:
        """Get text dimensions"""
        font_id = 0
        blf.size(font_id, self.theme.font_size)
        width, height = blf.dimensions(font_id, text)
        return (width, height)
        
