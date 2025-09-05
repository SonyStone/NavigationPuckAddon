import typing

from . import Rect, Theme, WidgetResponse, WidgetState
from .gpu_painter import GPUPainter
from .ui_context import UIContext

def get_widget_id(widget_id: typing.Optional[str], text: str, pos: typing.Tuple[float, float]) -> str:
    """Generate a unique widget ID if none provided"""
    if widget_id is None:
        widget_id = f"button_{text}_{pos[0]}_{pos[1]}"
    return widget_id


class UI:
    """Main UI interface - use this to create widgets"""

    def __init__(self):
        self.theme = Theme()
        self.ctx = UIContext(self.theme)
        self.painter = GPUPainter(self.theme)

    def button(
        self,
        text: str,
        pos: typing.Tuple[float, float],
        size: typing.Tuple[float, float],
        widget_id: typing.Optional[str] = None
    ) -> WidgetResponse:
        """Create a button widget"""

        widget_id = get_widget_id(widget_id, text, pos)

        rect = Rect(pos[0], pos[1], size[0], size[1])
        
        # Choose color based on state
        state = self.ctx.get_widget_state(widget_id, rect)
        match state:
            case WidgetState.ACTIVE:
                color = self.theme.button_active
            case WidgetState.HOVERED:
                color = self.theme.button_hovered
            case _:
                color = self.theme.button_idle

        # Draw button background
        self.painter.draw_rect(rect, color)

        # Draw border
        self.painter.draw_rect_outline(
            rect, self.theme.border, self.theme.border_width)

        # Draw text
        text_size = self.painter.get_text_size(text)
        text_pos = (
            rect.x + (rect.width - text_size[0]) * 0.5,
            rect.y + (rect.height - text_size[1]) * 0.5
        )
        self.painter.draw_text(text, text_pos, self.theme.text)

        response = self.ctx.get_widget_response(widget_id, rect)
        return response

    def icon_button(
        self,
        icon: str,
        pos: typing.Tuple[float, float],
        size: typing.Tuple[float, float],
        widget_id: typing.Optional[str] = None
    ) -> WidgetResponse:
        """Create an icon button widget"""
        if widget_id is None:
            widget_id = f"icon_button_{icon}_{pos[0]}_{pos[1]}"

        rect = Rect(pos[0], pos[1], size[0], size[1])
        response = self.ctx.get_widget_response(widget_id, rect)
        state = self.ctx.get_widget_state(widget_id, rect)

        # Choose color based on state
        if state == WidgetState.ACTIVE:
            color = self.theme.button_active
        elif state == WidgetState.HOVERED:
            color = self.theme.button_hovered
        else:
            color = self.theme.button_idle

        # Draw button background
        self.painter.draw_rect(rect, color)

        # Draw border
        self.painter.draw_rect_outline(
            rect, self.theme.border, self.theme.border_width)

        # For now, just draw icon name as text
        # In a full implementation, you'd draw the actual icon
        text_size = self.painter.get_text_size(icon)
        text_pos = (
            rect.x + (rect.width - text_size[0]) * 0.5,
            rect.y + (rect.height - text_size[1]) * 0.5
        )
        self.painter.draw_text(icon, text_pos, self.theme.text)

        return response

    def panel(
        self,
        pos: typing.Tuple[float, float],
        size: typing.Tuple[float, float]
    ) -> Rect:
        """Create a panel background"""
        rect = Rect(pos[0], pos[1], size[0], size[1])
        self.painter.draw_rect(rect, self.theme.background)
        self.painter.draw_rect_outline(
            rect, self.theme.border, self.theme.border_width)
        return rect

