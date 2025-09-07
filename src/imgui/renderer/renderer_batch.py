"""
Defines a batch renderer to optimize draw calls
"""
import typing

from .draw_protocol import DrawProtocol, UnwrapProtocol
from .flat_color_shader_command import FlatColorShaderCommand


class RendererBatch:
    """
    Manages batched draw operations for performance

    """

    def __init__(self):
        self.draw_calls: typing.List[typing.Any] = []
        self.merge: typing.Optional[FlatColorShaderCommand] = None

    def add(self, draw_call: DrawProtocol):
        """Add a draw call to the batch"""

        if isinstance(draw_call, UnwrapProtocol):
            draw_call = draw_call.unwrap()
        
        if isinstance(draw_call, FlatColorShaderCommand):
            if self.merge is None:
                self.merge = draw_call
                return
            self.merge = self.merge + draw_call
            return

        self.draw_calls.append(draw_call)

    def draw(self):
        """Execute all batched operations"""

        if self.merge:
            self.merge.draw()

        for draw_call in self.draw_calls:
            draw_call.draw()

        self.merge = None
        self.draw_calls.clear()
