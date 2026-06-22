import typing
import bpy
import mathutils

from .unique_id import UniqueID
from ..renderer import TextRendererCommand
from ..renderer.rect_outline_command import RectOutlineCommand
from . import Theme, WidgetResponse, WidgetState
from .rect import Rect
from ..renderer import Renderer
from .ui_context import UIContext


ICON_BUTTON_SCALE = 0.8


def get_widget_id(widget_id: typing.Optional[str], text: typing.Optional[str], pos: tuple[float, float]) -> str:
    """Generate a unique widget ID if none provided"""
    text = text or "widget"
    if widget_id is None:
        widget_id = f"{text}_{pos[0]}_{pos[1]}_{UniqueID.get_id()}"
    return widget_id


class UI:
    """Main UI interface - use this to create widgets with batching for performance"""

    def __init__(self):
        self.theme = Theme()
        self.ctx = UIContext(self.theme)
        self.renderer = Renderer()

    def begin_frame(self, mouse_pos: mathutils.Vector | tuple[float, float]):
        """Begin UI frame with batching"""
        self.ctx.begin_frame(mouse_pos)

    def end_frame(self):
        """End UI frame and flush all batched draws"""
        self.ctx.end_frame()
        UniqueID.reset()
        self.renderer.draw()

    def button(
        self,
        text: typing.Optional[str],
        pos: tuple[float, float],
        size: tuple[float, float],
        widget_id: typing.Optional[str] = None,
        opacity: float = 1.0
    ) -> WidgetResponse:
        """Create a button widget"""

        widget_id = get_widget_id(widget_id, text, pos)
        rect, response, state = self._button_interaction(widget_id, pos, size)

        self._draw_button_background(rect, state, opacity)
        if text:
            self._draw_centered_text(text, rect, opacity)

        return response

    def icon_button(
        self,
        icon: bpy.types.Image,
        pos: tuple[float, float],
        size: tuple[float, float],
        widget_id: typing.Optional[str] = None,
        opacity: float = 1.0,
    ) -> WidgetResponse:
        """Create an icon button widget"""
        widget_id = get_widget_id(widget_id, None, pos)
        rect, response, state = self._button_interaction(widget_id, pos, size)

        self._draw_button_background(rect, state, opacity)
        self._draw_centered_icon(icon, rect, opacity)

        return response

    def _button_interaction(
        self,
        widget_id: str,
        pos: tuple[float, float],
        size: tuple[float, float],
    ) -> tuple[Rect, WidgetResponse, WidgetState]:
        rect = Rect(pos[0], pos[1], size[0], size[1])
        response = self.ctx.get_widget_response(widget_id, rect)
        state = self.ctx.get_widget_state(widget_id, rect)
        return rect, response, state

    def _draw_button_background(self, rect: Rect, state: WidgetState, opacity: float) -> None:
        color = self._button_color(state)
        self.renderer.add(RectOutlineCommand(
            rect,
            outline_color=self._with_opacity(self.theme.border, opacity),
            fill_color=self._with_opacity(color, opacity),
            outline_width=self.theme.border_width,
        ))

    def _draw_centered_text(self, text: str, rect: Rect, opacity: float) -> None:
        text_size = self.theme.get_text_size(text)
        text_pos = self._centered_position(rect, text_size)
        self.renderer.add(TextRendererCommand(
            text,
            text_pos,
            color=self._with_opacity(self.theme.text, opacity),
        ))

    def _draw_centered_icon(self, icon: bpy.types.Image, rect: Rect, opacity: float) -> None:
        icon_size = (rect.width * ICON_BUTTON_SCALE, rect.height * ICON_BUTTON_SCALE)
        self.renderer.add_image(icon, self._centered_position(rect, icon_size), icon_size, opacity=opacity)

    def _button_color(self, state: WidgetState) -> tuple[float, float, float, float]:
        match state:
            case WidgetState.ACTIVE:
                return self.theme.button_active
            case WidgetState.HOVERED:
                return self.theme.button_hovered
            case _:
                return self.theme.button_idle

    @staticmethod
    def _with_opacity(color: tuple[float, float, float, float], opacity: float) -> tuple[float, float, float, float]:
        return (color[0], color[1], color[2], color[3] * opacity)

    @staticmethod
    def _centered_position(rect: Rect, size: tuple[float, float]) -> tuple[float, float]:
        return (
            rect.x + (rect.width - size[0]) * 0.5,
            rect.y + (rect.height - size[1]) * 0.5,
        )

    def panel(
        self,
        pos: tuple[float, float],
        size: tuple[float, float]
    ) -> Rect:
        """Create a panel background"""
        rect = Rect(pos[0], pos[1], size[0], size[1])
        self.renderer.add_rect_outline(rect, self.theme.border, self.theme.background, self.theme.border_width)
        return rect

