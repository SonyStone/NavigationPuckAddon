"""
Immediate Mode GUI System for Blender
Inspired by imgui/egui with proper event handling for Blender widgets.
"""

import enum
import dataclasses
import typing
import time
import bpy
import blf
import mathutils

from .input_event import EventType, PointerEvent, PointerButton


class WidgetState(enum.Enum):
    """Widget interaction states"""
    IDLE = enum.auto()
    HOVERED = enum.auto()
    ACTIVE = enum.auto()  # Being clicked/dragged
    FOCUSED = enum.auto()  # Has keyboard focus


@dataclasses.dataclass
class WidgetResponse:
    """Response from widget interaction"""
    clicked: bool = False
    hovered: bool = False
    dragged: bool = False
    drag_delta: mathutils.Vector = dataclasses.field(
        default_factory=lambda: mathutils.Vector((0.0, 0.0))
    )
    released: bool = False
    double_clicked: bool = False
    shift: bool = False
    ctrl: bool = False


class Theme:
    """Theme colors and styles"""

    # Colors (RGBA)
    background = (0.15, 0.15, 0.15, 0.95)
    button_idle = (0.25, 0.25, 0.25, 0.5)
    button_hovered = (0.35, 0.35, 0.45, 1.0)
    button_active = (0.45, 0.45, 0.55, 1.0)
    text = (0.9, 0.9, 0.9, 1.0)
    text_disabled = (0.5, 0.5, 0.5, 1.0)
    border = (0.4, 0.4, 0.4, 1.0)
    accent = (0.3, 0.6, 0.9, 1.0)

    # Sizes
    font_size = 12
    button_padding = 6.0
    widget_spacing = 4.0
    border_radius = 3.0
    border_width = 1.0
    
    def get_text_size(
        self,
        text: str
    ) -> tuple[float, float]:
        """Calculate text dimensions"""
        font_id = 0
        blf.size(font_id, self.font_size)
        width, height = blf.dimensions(font_id, text)
        return (width, height)


class InputEventAdapter:
    """Adapter to convert Blender events to imgui events"""

    def __init__(self):
        self.mouse_pos = mathutils.Vector((0.0, 0.0))
        self.last_mouse_pos = mathutils.Vector((0.0, 0.0))
        self.mouse_delta = mathutils.Vector((0.0, 0.0))

        self.pointer_down: typing.Optional[PointerButton] = None

    def to_pointer_event(self, event: bpy.types.Event) -> PointerEvent | None:
        """Handle Blender event and convert to imgui event format"""
        event_type = EventType.NONE
        button = None
        delta = mathutils.Vector(
            (event.mouse_prev_x - event.mouse_x, event.mouse_prev_y - event.mouse_y))

        match event.type:
            case 'MOUSEMOVE':
                if self.pointer_down is not None:
                    event_type = EventType.POINTER_MOVE
                    button = self.pointer_down
                else:
                    event_type = EventType.POINTER_MOVE

            case 'LEFTMOUSE' | 'RIGHTMOUSE' | 'MIDDLEMOUSE':
                match event.value:
                    case 'PRESS':
                        event_type = EventType.POINTER_DOWN
                        self.pointer_down = PointerButton(event.type)
                    case 'RELEASE':
                        event_type = EventType.POINTER_UP
                    case _:
                        pass

                button = PointerButton(event.type)
            case _:
                return None

        if event_type == EventType.NONE:
            return None

        pointer_event = PointerEvent(
            event_type=event_type,
            position=mathutils.Vector((event.mouse_region_x, event.mouse_region_y)),
            button=button,
            shift=event.shift,
            ctrl=event.ctrl,
            alt=event.alt,
            delta=delta,
            timestamp=time.time(),
        )

        if event_type == EventType.POINTER_UP and button == self.pointer_down:
            self.pointer_down = None

        return pointer_event
