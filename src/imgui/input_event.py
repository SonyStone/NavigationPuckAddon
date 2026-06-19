import enum
import dataclasses
import typing
import mathutils


class EventType(enum.Enum):
    """Types of input events"""
    NONE = enum.auto()
    POINTER_MOVE = enum.auto()
    POINTER_DOWN = enum.auto()
    POINTER_UP = enum.auto()
    POINTER_DRAG = enum.auto()
    POINTER_ENTER = enum.auto()
    POINTER_EXIT = enum.auto()
    KEY_PRESS = enum.auto()
    KEY_RELEASE = enum.auto()


class PointerButton(enum.Enum):
    """Mouse button types"""
    MAIN_BUTTON = 'LEFTMOUSE'
    SECONDARY_BUTTON = 'RIGHTMOUSE'
    MIDDLE_BUTTON = 'MIDDLEMOUSE'


@dataclasses.dataclass
class PointerEvent:
    """Represents an input event"""
    event_type: EventType
    position: mathutils.Vector = dataclasses.field(
        default_factory=lambda: mathutils.Vector((0.0, 0.0))
    )
    button: typing.Optional[PointerButton] = None
    key: typing.Optional[str] = None
    shift: bool = False
    ctrl: bool = False
    alt: bool = False
    delta: mathutils.Vector = dataclasses.field(
        default_factory=lambda: mathutils.Vector((0.0, 0.0))
    )
    timestamp: float = 0.0
