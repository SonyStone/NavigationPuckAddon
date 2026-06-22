import dataclasses
import enum

import mathutils


class WidgetState(enum.Enum):
    """Widget interaction states."""

    IDLE = enum.auto()
    HOVERED = enum.auto()
    ACTIVE = enum.auto()


@dataclasses.dataclass
class WidgetResponse:
    """Response from widget interaction."""

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
    """Theme colors and styles."""

    button_idle = (0.25, 0.25, 0.25, 0.5)
    button_hovered = (0.35, 0.35, 0.45, 1.0)
    button_active = (0.45, 0.45, 0.55, 1.0)
    border = (0.4, 0.4, 0.4, 1.0)
    border_width = 1.0
