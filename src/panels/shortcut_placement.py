import typing

import mathutils

from .shortcut_layout import (
    clamp_shortcut_center,
    cursor_in_follow_zone,
    fade_proximity,
    fade_start_radius,
    full_visible_radius,
    visible_control_contains,
)


class ShortcutPlacement:
    """Shortcut button position and fade-zone calculations."""

    def __init__(self, shortcut: typing.Any) -> None:
        self.shortcut = shortcut

    def clamp_center(self) -> None:
        shortcut = self.shortcut
        shortcut.button_center[:] = clamp_shortcut_center(
            shortcut.button_center,
            shortcut.region_size,
            shortcut.margin,
            shortcut.activation_mode,
            shortcut.button_size,
            shortcut.menu_button_size,
            shortcut.menu_gap,
        )

    def update_button_position(self) -> None:
        shortcut = self.shortcut
        if cursor_in_follow_zone(shortcut.mouse_pos, shortcut.button_center, shortcut.follow_zone_radius):
            return
        self.place_from_cursor()

    def place_from_cursor(self) -> None:
        shortcut = self.shortcut
        shortcut.button_center[:] = shortcut.mouse_pos + shortcut.cursor_offset
        self.clamp_center()

    def update_target_opacity(self, previous_mouse_pos: mathutils.Vector | None = None) -> None:
        shortcut = self.shortcut
        if not cursor_in_follow_zone(shortcut.mouse_pos, shortcut.button_center, shortcut.follow_zone_radius):
            self.set_target_opacity(shortcut.idle_opacity)
            return

        distance_to_button = (shortcut.mouse_pos - shortcut.button_center).length
        proximity = fade_proximity(
            visible_control_contains(
                shortcut.activation_mode,
                shortcut.button_center,
                shortcut.button_size,
                shortcut.menu_button_size,
                shortcut.mouse_pos,
                shortcut._supports_action,
                shortcut.menu_gap,
            ),
            distance_to_button,
            full_visible_radius(shortcut.activation_mode, shortcut.button_size, shortcut.menu_button_size),
            fade_start_radius(
                shortcut.fade_zone_min_inset,
                shortcut.follow_zone_radius,
                shortcut.fade_zone_inset_percent,
                shortcut.activation_mode,
                shortcut.button_size,
                shortcut.menu_button_size,
            ),
        )
        self.set_target_opacity(max(shortcut.idle_opacity, proximity))

    def set_target_opacity(self, opacity: float) -> None:
        shortcut = self.shortcut
        shortcut.target_opacity = opacity
        shortcut.opacity = shortcut.target_opacity
