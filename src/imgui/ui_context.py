import typing
import bpy
import mathutils

from . import InputEventAdapter, Theme, WidgetResponse, WidgetState
from .double_click_tracker import DoubleClickTracker
from .rect import Rect

from .input_event import EventType, PointerEvent, PointerButton



class UIContext:
    """Main UI context managing widget state and interaction"""

    def __init__(self, theme: Theme):
        self.theme = theme

        self.input_event_adapter = InputEventAdapter()

        # Input state
        self.mouse_pos = mathutils.Vector((0.0, 0.0))
        self.last_mouse_pos = mathutils.Vector((0.0, 0.0))
        self.mouse_delta = mathutils.Vector((0.0, 0.0))

        # Widget state tracking
        self.hovered_id: typing.Optional[str] = None
        self.active_id: typing.Optional[str] = None
        self.focused_id: typing.Optional[str] = None

        # Click tracking
        self.click_start_pos = (0.0, 0.0)
        self.click_time = 0.0
        self.double_click_tracker = DoubleClickTracker()

        # Layout state
        self.next_widget_pos = (0.0, 0.0)
        self.layout_direction = mathutils.Vector((1.0, 0.0))  # Horizontal by default
        self.auto_layout = True

        # Frame state
        self.frame_count = 0

        # Event queue
        self.pending_events: typing.List[PointerEvent] = []

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
        self.focused_id = None
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

        consumed = False

        if event.event_type == EventType.POINTER_DOWN:
            if event.button == PointerButton.MAIN_BUTTON:
                self.click_start_pos = event.position
                self.click_time = event.timestamp

        elif event.event_type == EventType.POINTER_UP:
            if event.button == PointerButton.MAIN_BUTTON:
                consumed = self.active_id is not None or self.hovered_id is not None

        return consumed

    def get_widget_state(self, widget_id: str, rect: Rect) -> WidgetState:
        """Get current state of widget"""
        if rect.contains(*self.mouse_pos):
            self.hovered_id = widget_id

            if self.active_id == widget_id:
                return WidgetState.ACTIVE
            else:
                return WidgetState.HOVERED

        elif self.active_id == widget_id:
            return WidgetState.ACTIVE
        else:
            return WidgetState.IDLE

    def get_widget_response(self, widget_id: str, rect: Rect) -> WidgetResponse:
        """Get interaction response for widget"""
        state = self.get_widget_state(widget_id, rect)

        hovered = (state in (WidgetState.HOVERED, WidgetState.ACTIVE))
        clicked = False
        dragged = False
        drag_delta = mathutils.Vector((0.0, 0.0))
        released = False
        double_clicked = False
        shift = False
        ctrl = False

        for event in self.pending_events:
            if is_event_pointer_down(event, rect):
                self.active_id = widget_id
                clicked = True
                double_clicked = self.double_click_tracker.is_double_click(
                    widget_id, event
                )

            if event.shift:
                shift = True

            if event.ctrl:
                ctrl = True

            if is_event_drag(event, self.active_id, widget_id):
                dragged = True
                drag_delta = event.delta

            if is_event_release(event, self.active_id, widget_id):
                released = True

        response = WidgetResponse(
            clicked=clicked,
            hovered=hovered,
            dragged=dragged,
            drag_delta=drag_delta,
            released=released,
            double_clicked=double_clicked,
            shift=shift,
            ctrl=ctrl,
        )

        return response

def is_event_pointer_down(event: PointerEvent, rect: Rect) -> bool:
    """Check if event starts on this widget."""
    return event.event_type == EventType.POINTER_DOWN and \
        event.button == PointerButton.MAIN_BUTTON and \
        rect.contains(*event.position)

def is_event_drag(event: PointerEvent, active_id: str | None, widget_id: str | None) -> bool:
    """Check if event represents a drag on the widget"""
    return event.event_type == EventType.POINTER_MOVE and \
        active_id == widget_id and \
        event.button == PointerButton.MAIN_BUTTON

def is_event_release(event: PointerEvent, active_id: str | None, widget_id: str | None) -> bool:
    """Check if event represents a mouse release on the widget"""
    return event.event_type == EventType.POINTER_UP and \
        event.button == PointerButton.MAIN_BUTTON and \
        active_id == widget_id and \
        widget_id is not None
