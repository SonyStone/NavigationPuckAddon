import mathutils

from ..imgui.rect import Rect
from ..activation import ACTIVATION_DIRECT_MENU


PUCK_ACTIONS = ("pan", "orbit", "zoom", "roll")
PAN_ZOOM_ACTIONS = {"pan", "zoom"}

SHORTCUT_CURSOR_DIRECTIONS = {
    'TOP_LEFT': (-1.0, 1.0),
    'TOP': (0.0, 1.0),
    'TOP_RIGHT': (1.0, 1.0),
    'LEFT': (-1.0, 0.0),
    'RIGHT': (1.0, 0.0),
    'BOTTOM_LEFT': (-1.0, -1.0),
    'BOTTOM': (0.0, -1.0),
    'BOTTOM_RIGHT': (1.0, -1.0),
}


def button_rect(center: mathutils.Vector, size: float) -> Rect:
    half_size = size * 0.5
    return Rect(
        center.x - half_size,
        center.y - half_size,
        size,
        size,
    )


def puck_action_rects(
    center: mathutils.Vector,
    size: float,
    offset: tuple[float, float] = (5.0, 5.0),
) -> dict[str, Rect]:
    x, y = center
    return {
        "pan": Rect(x - size - 0.5 + offset[0], y - size - 0.5 + offset[1], size, size),
        "orbit": Rect(x + 0.5 + offset[0], y - size - 0.5 + offset[1], size, size),
        "zoom": Rect(x - size - 0.5 + offset[0], y + 0.5 + offset[1], size, size),
        "roll": Rect(x + 0.5 + offset[0], y + 0.5 + offset[1], size, size),
    }


def direct_menu_rects(
    center: mathutils.Vector,
    size: float,
    offset: float = 5.0,
) -> dict[str, Rect]:
    return puck_action_rects(center, size, (offset, offset))


def supports_puck_action(
    action: str,
    *,
    is_view2d_editor: bool,
    is_camera_view: bool,
    is_camera_view_locked: bool,
) -> bool:
    if is_view2d_editor:
        return action in PAN_ZOOM_ACTIONS
    if is_camera_view and not is_camera_view_locked:
        return action in PAN_ZOOM_ACTIONS
    return action in PUCK_ACTIONS


def cursor_offset(cursor_position: str, cursor_distance: float) -> mathutils.Vector:
    direction = SHORTCUT_CURSOR_DIRECTIONS.get(cursor_position, SHORTCUT_CURSOR_DIRECTIONS['BOTTOM_LEFT'])
    return mathutils.Vector((direction[0] * cursor_distance, direction[1] * cursor_distance))


def control_edge_radius(activation_mode: str, button_size: float, menu_button_size: float) -> float:
    if activation_mode == ACTIVATION_DIRECT_MENU:
        return menu_button_size
    return button_size * 0.5


def follow_zone_radius(cursor_offset: mathutils.Vector, edge_radius: float) -> float:
    return max(edge_radius * 2.0, cursor_offset.length + edge_radius)


def clamp_center(
    center: mathutils.Vector,
    region_size: mathutils.Vector,
    margin: float,
    half_size: float,
) -> mathutils.Vector:
    min_x = margin + half_size
    min_y = margin + half_size
    max_x = max(min_x, region_size.x - margin - half_size)
    max_y = max(min_y, region_size.y - margin - half_size)
    return mathutils.Vector((
        min(max(center.x, min_x), max_x),
        min(max(center.y, min_y), max_y),
    ))
