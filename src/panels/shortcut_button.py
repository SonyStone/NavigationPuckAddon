import typing

import bpy
import mathutils

from ..imgui.rect import Rect
from ..renderer.circle_outline_command import CircleOutlineCommand
from ..utils.draw_handler import force_redraw
from ..utils.operator_return import OperatorReturn, OperatorReturnType
from .editor_context import RegionLocalEvent
from .shortcut_layout import button_rect, fade_start_radius


class ShortcutButton:
    """Shortcut-button activation behavior for the always-on shortcut."""

    def __init__(self, shortcut: typing.Any) -> None:
        self.shortcut = shortcut

    def event_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        previous_mouse_pos: mathutils.Vector,
        local_event: RegionLocalEvent,
    ) -> OperatorReturnType:
        if event.type == 'MOUSEMOVE':
            return self._handle_mousemove(context, previous_mouse_pos)

        if event.type == 'LEFTMOUSE':
            result = self._handle_leftmouse(context, event, local_event)
            if result is not None:
                return result

        return OperatorReturn.PASS_THROUGH

    def draw(self, context: bpy.types.Context) -> None:
        shortcut = self.shortcut
        if shortcut._menu_is_running():
            return

        draw_opacity, debug_bounds = self._draw_opacity(context)
        if draw_opacity <= 0.01:
            return

        shortcut.ui.begin_frame(shortcut.mouse_pos)
        response = self._draw_button(button_rect(shortcut.button_center, shortcut.button_size), draw_opacity)
        if debug_bounds:
            self._draw_debug_bounds()
        if response and response.hovered:
            shortcut.target_opacity = 1.0
            shortcut.opacity = 1.0

        shortcut.ui.end_frame()

    def _handle_mousemove(
        self,
        context: bpy.types.Context,
        previous_mouse_pos: mathutils.Vector,
    ) -> OperatorReturnType:
        shortcut = self.shortcut
        shortcut.placement.update_button_position()
        shortcut.placement.update_target_opacity(previous_mouse_pos)
        force_redraw(context)
        return OperatorReturn.PASS_THROUGH

    def _handle_leftmouse(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        local_event: RegionLocalEvent,
    ) -> OperatorReturnType | None:
        shortcut = self.shortcut
        is_over_button = shortcut._is_clickable() and button_rect(
            shortcut.button_center,
            shortcut.button_size,
        ).contains(shortcut.mouse_pos.x, shortcut.mouse_pos.y)

        if event.value == 'PRESS' and is_over_button:
            shortcut.press_started_on_button = True
            shortcut.ui.ctx.handle_event(local_event)
            shortcut._open_puck_menu(context)
            shortcut.press_started_on_button = False
            shortcut.target_opacity = 0.0
            shortcut.opacity = 0.0
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        if event.value == 'RELEASE' and shortcut.press_started_on_button:
            shortcut.press_started_on_button = False
            shortcut.ui.ctx.handle_event(local_event)
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        return None

    def _draw_opacity(self, context: bpy.types.Context) -> tuple[float, bool]:
        shortcut = self.shortcut
        debug_bounds = shortcut._debug_bounds_enabled(context)
        draw_opacity = max(shortcut.opacity, 0.65) if debug_bounds else shortcut.opacity
        return draw_opacity, debug_bounds

    def _draw_button(self, button_rect: Rect, opacity: float) -> typing.Any | None:
        shortcut = self.shortcut
        if shortcut.icon:
            return shortcut.ui.icon_button(
                shortcut.icon,
                (button_rect.x, button_rect.y),
                (shortcut.button_size, shortcut.button_size),
                "navigation_puck_shortcut",
                opacity=opacity,
            )

        return None

    def _draw_debug_bounds(self) -> None:
        shortcut = self.shortcut
        shortcut.ui.renderer.add(CircleOutlineCommand(
            center=(shortcut.button_center.x, shortcut.button_center.y),
            radius=shortcut.follow_zone_radius,
            color=(0.0, 0.85, 1.0, 0.85),
            width=2.0,
        ))
        shortcut.ui.renderer.add(CircleOutlineCommand(
            center=(shortcut.button_center.x, shortcut.button_center.y),
            radius=fade_start_radius(
                shortcut.fade_zone_min_inset,
                shortcut.follow_zone_radius,
                shortcut.fade_zone_inset_percent,
                shortcut.activation_mode,
                shortcut.button_size,
                shortcut.menu_button_size,
            ),
            color=(1.0, 0.35, 0.0, 0.95),
            width=2.0,
        ))
        shortcut.ui.renderer.add(CircleOutlineCommand(
            center=(shortcut.button_center.x, shortcut.button_center.y),
            radius=shortcut.button_size * 0.5,
            color=(0.2, 1.0, 0.25, 1.0),
            width=2.0,
        ))
