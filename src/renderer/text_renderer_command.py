"""
Defines a command to render text using Blender's BLF module.
"""

import dataclasses
import blf

from .draw_protocol import DrawProtocol


@dataclasses.dataclass
class TextRendererCommand(DrawProtocol):
    """Represents a text draw operation"""
    text: str
    pos: tuple[float, float]
    color: tuple[float, float, float, float]

    def draw(self):
        font_id = 0
        blf.position(font_id, self.pos[0], self.pos[1], 0)
        blf.color(font_id, *self.color)
        blf.draw(font_id, self.text)
