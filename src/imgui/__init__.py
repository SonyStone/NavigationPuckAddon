"""
Immediate Mode GUI System for Blender
Inspired by imgui/egui with proper event handling for Blender widgets.
"""

import enum
import dataclasses
import typing
import time
import bpy
import mathutils

from .input_event import EventType, PointerEvent, PointerButton


@dataclasses.dataclass
class Rect:
    """Rectangle with position and size"""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    def contains(self, x: float, y: float) -> bool:
        """Check if point is inside rectangle"""
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)

    def center(self) -> typing.Tuple[float, float]:
        """Get center point of rectangle"""
        return (self.x + self.width * 0.5, self.y + self.height * 0.5)

    def expand(self, amount: float) -> 'Rect':
        """Return expanded rectangle"""
        return Rect(
            self.x - amount,
            self.y - amount,
            self.width + amount * 2,
            self.height + amount * 2
        )


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
    drag_delta: mathutils.Vector = mathutils.Vector((0.0, 0.0))
    released: bool = False
    double_clicked: bool = False
    shift: bool = False
    ctrl: bool = False


class Theme:
    """Theme colors and styles"""

    # Colors (RGBA)
    background = (0.15, 0.15, 0.15, 0.95)
    button_idle = (0.25, 0.25, 0.25, 1.0)
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

class InputEventAdapter:
    """Adapter to convert Blender events to imgui events"""

    mouse_pos = mathutils.Vector((0.0, 0.0))
    last_mouse_pos = mathutils.Vector((0.0, 0.0))
    mouse_delta = mathutils.Vector((0.0, 0.0))

    # we only track main button for now
    pointer_down: typing.Literal[PointerButton.MAIN_BUTTON] | None = None

    def to_pointer_event(self, event: bpy.types.Event) -> PointerEvent | None:
        """Handle Blender event and convert to imgui event format"""
        pointer_event = None

        event_type = EventType.NONE
        button = None
        delta =  mathutils.Vector((event.mouse_prev_x - event.mouse_x,event.mouse_prev_y -  event.mouse_y))

        match event.type:
            case 'MOUSEMOVE':
                if self.pointer_down is not None and self.pointer_down == PointerButton.MAIN_BUTTON:
                    event_type = EventType.POINTER_MOVE
                    button = self.pointer_down
                else:
                    event_type = EventType.POINTER_MOVE

            case 'LEFTMOUSE' | 'RIGHTMOUSE' | 'MIDDLEMOUSE':
                match event.value:
                    case 'PRESS':
                        if event.type == 'LEFTMOUSE':
                            self.pointer_down = PointerButton.MAIN_BUTTON
                        event_type = EventType.POINTER_DOWN
                    case 'RELEASE':
                        self.pointer_down = None
                        event_type = EventType.POINTER_UP
                    case _:
                        pass

                button = PointerButton(event.type)
            case _:
                pass


        pointer_event = PointerEvent(
            event_type=event_type,
            position=(event.mouse_region_x, event.mouse_region_y),
            button=button,
            shift=event.shift,
            ctrl=event.ctrl,
            alt=event.alt,
            delta=delta,
            timestamp=time.time(),
        )

        return pointer_event
        