import typing
import bpy
import mathutils

from ..renderer.rect_outline_command import RectOutlineCommand

from . import Theme, WidgetResponse, WidgetState
from .rect import Rect
from ..renderer import Renderer
from .ui_context import UIContext

class UniqueID:
    """Simple unique ID generator"""
    _id = 0
    
    @classmethod
    def reset(cls) -> None:
        """Reset ID counter to zero"""
        cls._id = 0
    
    @classmethod
    def get_id(cls) -> str:
        """Return a new unique ID as a string"""
        cls._id += 1
        return str(cls._id)

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

    def begin_frame(self, mouse_pos: mathutils.Vector):
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

        # Draw rect
        self.renderer.add_rect_outline(rect, self.theme.border, color, self.theme.border_width)

        # Draw text
        if text:
            text_size = self.theme.get_text_size(text)
            text_pos = (
                rect.x + (rect.width - text_size[0]) * 0.5,
                rect.y + (rect.height - text_size[1]) * 0.5
            )
            self.renderer.add_text(text, text_pos, self.theme.text)

        response = self.ctx.get_widget_response(widget_id, rect)
        return response

    def icon_button(
        self,
        icon: bpy.types.Image,
        pos: tuple[float, float],
        size: tuple[float, float],
        widget_id: typing.Optional[str] = None,
    ) -> WidgetResponse:
        """Create an icon button widget"""
        widget_id = get_widget_id(widget_id, None, pos)

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

        self.renderer.add(RectOutlineCommand(rect, outline_color= self.theme.border , fill_color=color, outline_width=self.theme.border_width))

        # Draw image icon centered in the button
        icon_size = (size[0] * 0.8, size[1] * 0.8)  # Make icon 80% of button size
        icon_pos = (
            rect.x + (rect.width - icon_size[0]) * 0.5,
            rect.y + (rect.height - icon_size[1]) * 0.5
        )
        self.renderer.add_image(icon, icon_pos, icon_size)

        return response

    def panel(
        self,
        pos: tuple[float, float],
        size: tuple[float, float]
    ) -> Rect:
        """Create a panel background"""
        rect = Rect(pos[0], pos[1], size[0], size[1])
        self.renderer.add_rect_outline(rect, self.theme.border, self.theme.background, self.theme.border_width)
        return rect

