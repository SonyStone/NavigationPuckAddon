import typing

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


def direct_menu_contains(
    center: mathutils.Vector,
    size: float,
    x: float,
    y: float,
    supports_action: typing.Callable[[str], bool],
) -> bool:
    return any(
        supports_action(action) and rect.contains(x, y)
        for action, rect in direct_menu_rects(center, size).items()
    )


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


def cursor_in_follow_zone(
    mouse_pos: mathutils.Vector,
    button_center: mathutils.Vector,
    zone_radius: float,
) -> bool:
    return (mouse_pos - button_center).length <= zone_radius


def fade_start_radius(
    fade_zone_min_inset: float,
    follow_zone_radius: float,
    fade_zone_inset_percent: float,
    activation_mode: str,
    button_size: float,
    menu_button_size: float,
) -> float:
    inset = max(
        fade_zone_min_inset,
        follow_zone_radius * (fade_zone_inset_percent / 100.0),
    )
    edge_radius = control_edge_radius(activation_mode, button_size, menu_button_size)
    return max(edge_radius, follow_zone_radius - inset)


def full_visible_radius(activation_mode: str, button_size: float, menu_button_size: float) -> float:
    return control_edge_radius(activation_mode, button_size, menu_button_size)


def visible_control_contains(
    activation_mode: str,
    button_center: mathutils.Vector,
    button_size: float,
    menu_button_size: float,
    mouse_pos: mathutils.Vector,
    supports_action: typing.Callable[[str], bool],
) -> bool:
    if activation_mode == ACTIVATION_DIRECT_MENU:
        return direct_menu_contains(
            button_center,
            menu_button_size,
            mouse_pos.x,
            mouse_pos.y,
            supports_action,
        )
    return button_rect(button_center, button_size).contains(mouse_pos.x, mouse_pos.y)


def fade_proximity(
    is_on_visible_control: bool,
    distance_to_button: float,
    full_visible_radius: float,
    fade_start_radius: float,
) -> float:
    if is_on_visible_control:
        return 1.0
    if distance_to_button <= full_visible_radius:
        return 1.0
    if distance_to_button >= fade_start_radius:
        return 0.0

    fade_span = max(fade_start_radius - full_visible_radius, 1.0)
    return 1.0 - ((distance_to_button - full_visible_radius) / fade_span)


def shortcut_control_half_size(activation_mode: str, button_size: float, menu_button_size: float) -> float:
    if activation_mode == ACTIVATION_DIRECT_MENU:
        return menu_button_size + 6.0
    return button_size * 0.5


def clamp_shortcut_center(
    center: mathutils.Vector,
    region_size: mathutils.Vector,
    margin: float,
    activation_mode: str,
    button_size: float,
    menu_button_size: float,
) -> mathutils.Vector:
    return clamp_center(
        center,
        region_size,
        margin,
        shortcut_control_half_size(activation_mode, button_size, menu_button_size),
    )


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
