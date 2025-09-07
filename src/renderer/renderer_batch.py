"""
Defines a batch renderer to optimize draw calls
"""
import typing

from .draw_protocol import DrawProtocol


class RendererBatch:
    """
    Manages batched draw operations for performance

    """

    def __init__(self):
        self.draw_calls: typing.List[typing.Any] = []

    def add(self, draw_call: DrawProtocol):
        """Add a draw call to the batch"""

        self.draw_calls.append(draw_call)

    def draw(self):
        """Execute all batched operations"""

        for draw_call in self.draw_calls:
            draw_call.draw()

        self.merge = None
        self.draw_calls.clear()
