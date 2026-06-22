import time
import typing

import bpy
import mathutils

from ..utils.view_math import event_drag_delta
from .input_event import EventType, PointerButton, PointerEvent


class InputEventAdapter:
    """Adapter to convert Blender events to imgui events."""

    def __init__(self):
        self.mouse_pos = mathutils.Vector((0.0, 0.0))
        self.last_mouse_pos = mathutils.Vector((0.0, 0.0))
        self.mouse_delta = mathutils.Vector((0.0, 0.0))
        self.pointer_down: typing.Optional[PointerButton] = None

    def to_pointer_event(self, event: bpy.types.Event) -> PointerEvent | None:
        """Handle Blender event and convert to imgui event format."""
        pointer_event_kind = self._pointer_event_kind(event)
        if pointer_event_kind is None:
            return None

        event_type, button = pointer_event_kind
        if event_type == EventType.NONE:
            return None

        pointer_event = PointerEvent(
            event_type=event_type,
            position=mathutils.Vector((event.mouse_region_x, event.mouse_region_y)),
            button=button,
            shift=event.shift,
            ctrl=event.ctrl,
            alt=event.alt,
            delta=event_drag_delta(event),
            timestamp=time.time(),
        )

        if event_type == EventType.POINTER_UP and button == self.pointer_down:
            self.pointer_down = None

        return pointer_event

    def _pointer_event_kind(self, event: bpy.types.Event) -> tuple[EventType, PointerButton | None] | None:
        match event.type:
            case 'MOUSEMOVE':
                return EventType.POINTER_MOVE, self.pointer_down
            case 'LEFTMOUSE' | 'RIGHTMOUSE' | 'MIDDLEMOUSE':
                return self._mouse_button_event_kind(event)
            case _:
                return None

    def _mouse_button_event_kind(self, event: bpy.types.Event) -> tuple[EventType, PointerButton]:
        button = PointerButton(event.type)
        match event.value:
            case 'PRESS':
                self.pointer_down = button
                return EventType.POINTER_DOWN, button
            case 'RELEASE':
                return EventType.POINTER_UP, button
            case _:
                return EventType.NONE, button
