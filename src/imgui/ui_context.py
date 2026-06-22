import typing
import bpy
import mathutils

from .double_click_tracker import DoubleClickTracker
from .input_adapter import InputEventAdapter
from .rect import Rect
from .types import Theme, WidgetResponse, WidgetState

from .input_event import EventType, PointerEvent, PointerButton



class UIContext:
    """Main UI context managing widget state and interaction"""

    def __init__(self, theme: Theme):
        self.theme = theme
        self.input_event_adapter = InputEventAdapter()

        self._init_input_state()
        self._init_widget_state()
        self._init_click_state()

        self.frame_count = 0
        self.pending_events: typing.List[PointerEvent] = []

    def _init_input_state(self) -> None:
        self.mouse_pos = mathutils.Vector((0.0, 0.0))
        self.last_mouse_pos = mathutils.Vector((0.0, 0.0))
        self.mouse_delta = mathutils.Vector((0.0, 0.0))

    def _init_widget_state(self) -> None:
        self.hovered_id: typing.Optional[str] = None
        self.active_id: typing.Optional[str] = None

    def _init_click_state(self) -> None:
        self.click_start_pos = (0.0, 0.0)
        self.click_time = 0.0
        self.double_click_tracker = DoubleClickTracker()

    def begin_frame(self, mouse_pos: mathutils.Vector | tuple[float, float]):
        """Begin new frame - call this before drawing widgets"""
        if not isinstance(mouse_pos, mathutils.Vector):
            mouse_pos = mathutils.Vector(mouse_pos)

        self.last_mouse_pos = self.mouse_pos
        self.mouse_pos = mouse_pos
        self.mouse_delta = mathutils.Vector((
            mouse_pos.x - self.last_mouse_pos.x,
            mouse_pos.y - self.last_mouse_pos.y
        ))
        self.frame_count += 1

        # Reset per-frame state
        self.hovered_id = None

    def end_frame(self):
        """End frame - call this after drawing all widgets"""
        if any(
            event.event_type == EventType.POINTER_UP and event.button == PointerButton.MAIN_BUTTON
            for event in self.pending_events
        ):
            self.active_id = None

        # Clear processed events
        self.pending_events.clear()

    def reset_state(self):
        """Reset UI state - call this when context changes"""
        self.hovered_id = None
        self.active_id = None
        self.pending_events.clear()

    def handle_event(self, blender_event: bpy.types.Event) -> bool:
        """
        Handle Blender event and convert to internal event format
        
        Process input event and update UI state
        """

        event = self.input_event_adapter.to_pointer_event(blender_event)

        if not event:
            return False

        self.pending_events.append(event)
        self._remember_click_start(event)
        return self._release_consumed(event)

    def _remember_click_start(self, event: PointerEvent) -> None:
        if event.event_type == EventType.POINTER_DOWN and event.button == PointerButton.MAIN_BUTTON:
            self.click_start_pos = event.position
            self.click_time = event.timestamp

    def _release_consumed(self, event: PointerEvent) -> bool:
        if event.event_type != EventType.POINTER_UP or event.button != PointerButton.MAIN_BUTTON:
            return False
        return self.active_id is not None or self.hovered_id is not None

    def get_widget_state(self, widget_id: str, rect: Rect) -> WidgetState:
        """Get current state of widget"""
        if not rect.contains(*self.mouse_pos):
            if self.active_id == widget_id:
                return WidgetState.ACTIVE
            return WidgetState.IDLE

        self.hovered_id = widget_id
        if self.active_id == widget_id:
            return WidgetState.ACTIVE
        return WidgetState.HOVERED

    def get_widget_response(self, widget_id: str, rect: Rect) -> WidgetResponse:
        """Get interaction response for widget"""
        state = self.get_widget_state(widget_id, rect)
        response = WidgetResponse(hovered=state in (WidgetState.HOVERED, WidgetState.ACTIVE))

        for event in self.pending_events:
            self._apply_widget_event(widget_id, rect, event, response)

        return response

    def _apply_widget_event(
        self,
        widget_id: str,
        rect: Rect,
        event: PointerEvent,
        response: WidgetResponse,
    ) -> None:
        if is_event_pointer_down(event, rect):
            self.active_id = widget_id
            response.clicked = True
            response.double_clicked = self.double_click_tracker.is_double_click(widget_id, event)

        response.shift = response.shift or event.shift
        response.ctrl = response.ctrl or event.ctrl

        if is_event_drag(event, self.active_id, widget_id):
            response.dragged = True
            response.drag_delta = event.delta

        if is_event_release(event, self.active_id, widget_id):
            response.released = True


def is_event_pointer_down(event: PointerEvent, rect: Rect) -> bool:
    """Check if event starts on this widget."""
    return (
        event.event_type == EventType.POINTER_DOWN
        and event.button == PointerButton.MAIN_BUTTON
        and rect.contains(*event.position)
    )

def is_event_drag(event: PointerEvent, active_id: str | None, widget_id: str | None) -> bool:
    """Check if event represents a drag on the widget"""
    return (
        event.event_type == EventType.POINTER_MOVE
        and active_id == widget_id
        and event.button == PointerButton.MAIN_BUTTON
    )

def is_event_release(event: PointerEvent, active_id: str | None, widget_id: str | None) -> bool:
    """Check if event represents a mouse release on the widget"""
    return (
        event.event_type == EventType.POINTER_UP
        and event.button == PointerButton.MAIN_BUTTON
        and active_id == widget_id
        and widget_id is not None
    )
