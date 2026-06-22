import typing

import bpy
import mathutils

from ..imgui.rect import Rect
from ..renderer.circle_outline_command import CircleOutlineCommand
from ..utils.draw_handler import force_redraw
from ..utils.operator_return import OperatorReturn, OperatorReturnType
from .editor_context import RegionLocalEvent
from .shortcut_layout import PUCK_ACTIONS, direct_menu_contains, direct_menu_rects
from .view_operation_dispatch import apply_view_action, handle_view_operation_events


class ShortcutDirectMenu:
    """Direct action menu behavior for the always-on shortcut."""

    def __init__(self, shortcut: typing.Any) -> None:
        self.shortcut = shortcut

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        shortcut = self.shortcut
        if shortcut._menu_is_running():
            return OperatorReturn.PASS_THROUGH

        if not shortcut._event_has_region_position(event):
            return OperatorReturn.PASS_THROUGH

        lock_owner_context = shortcut._has_active_pointer_interaction()
        previous_mouse_pos, local_event = shortcut._sync_pointer_from_event(
            context,
            event,
            refresh_owner=not lock_owner_context,
        )
        view_operation_was_active = shortcut.view_ops.any_active(shortcut._is_view2d_editor())
        if view_operation_was_active:
            return self._continue_view_operation(context, event, local_event, view_operation_was_active)

        return self._pointer_event_result(context, event, local_event, previous_mouse_pos)

    def draw(self, context: bpy.types.Context) -> None:
        shortcut = self.shortcut
        if shortcut._menu_is_running():
            return

        if (
            not shortcut._has_active_pointer_interaction()
            and shortcut._another_shortcut_has_active_pointer_interaction()
        ):
            shortcut.ui.ctx.reset_state()
            return

        if shortcut.view_ops.any_active(shortcut._is_view2d_editor()):
            shortcut.ui.ctx.reset_state()
            return

        shortcut._ensure_direct_menu_images()
        draw_opacity, debug_bounds = self._draw_opacity(context)
        if draw_opacity <= 0.01:
            return

        shortcut.ui.begin_frame(shortcut.mouse_pos)
        rects = direct_menu_rects(shortcut.button_center, shortcut.menu_button_size)
        for action in PUCK_ACTIONS:
            self._draw_action(context, action, shortcut.direct_menu_images[action], rects[action], draw_opacity)

        if debug_bounds:
            self._draw_debug_bounds()

        shortcut.ui.end_frame()

    def _continue_view_operation(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        local_event: RegionLocalEvent,
        view_operation_was_active: bool,
    ) -> OperatorReturnType:
        shortcut = self.shortcut
        handled_view_event = handle_view_operation_events(
            shortcut.view_ops,
            shortcut.owner_context,
            context,
            local_event,
            is_view2d_editor=shortcut._is_view2d_editor(),
        )
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            shortcut.ui.ctx.handle_event(local_event)
        if not shortcut.view_ops.any_active(shortcut._is_view2d_editor()):
            shortcut._reveal_at_cursor(shortcut.mouse_pos)
        force_redraw(context)
        return OperatorReturn.RUNNING_MODAL if handled_view_event or view_operation_was_active else OperatorReturn.PASS_THROUGH

    def _handle_mousemove(
        self,
        context: bpy.types.Context,
        previous_mouse_pos: mathutils.Vector,
        local_event: RegionLocalEvent,
    ) -> OperatorReturnType:
        shortcut = self.shortcut
        if shortcut.ui.ctx.active_id is None:
            shortcut.placement.update_button_position()
            shortcut.placement.update_target_opacity(previous_mouse_pos)
        shortcut.ui.ctx.handle_event(local_event)
        force_redraw(context)
        return OperatorReturn.RUNNING_MODAL if shortcut.ui.ctx.active_id is not None else OperatorReturn.PASS_THROUGH

    def _handle_leftmouse(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        local_event: RegionLocalEvent,
    ) -> OperatorReturnType | None:
        shortcut = self.shortcut
        is_over_menu = shortcut._is_clickable() and direct_menu_contains(
            shortcut.button_center,
            shortcut.menu_button_size,
            shortcut.mouse_pos.x,
            shortcut.mouse_pos.y,
            shortcut._supports_action,
        )

        if event.value == 'PRESS' and is_over_menu:
            shortcut.ui.ctx.handle_event(local_event)
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        if event.value == 'RELEASE' and shortcut.ui.ctx.active_id is not None:
            shortcut.ui.ctx.handle_event(local_event)
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        return None

    def _pointer_event_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        local_event: RegionLocalEvent,
        previous_mouse_pos: mathutils.Vector,
    ) -> OperatorReturnType:
        if event.type == 'MOUSEMOVE':
            return self._handle_mousemove(context, previous_mouse_pos, local_event)

        if event.type == 'LEFTMOUSE':
            result = self._handle_leftmouse(context, event, local_event)
            if result is not None:
                return result

        return OperatorReturn.PASS_THROUGH

    def _draw_opacity(self, context: bpy.types.Context) -> tuple[float, bool]:
        shortcut = self.shortcut
        debug_bounds = shortcut._debug_bounds_enabled(context)
        draw_opacity = max(shortcut.opacity, 0.65) if debug_bounds else shortcut.opacity
        return draw_opacity, debug_bounds

    def _draw_debug_bounds(self) -> None:
        shortcut = self.shortcut
        shortcut.ui.renderer.add(CircleOutlineCommand(
            center=(shortcut.button_center.x, shortcut.button_center.y),
            radius=shortcut.follow_zone_radius,
            color=(0.0, 0.85, 1.0, 0.85),
            width=2.0,
        ))

    def _draw_action(
        self,
        context: bpy.types.Context,
        action: str,
        image: typing.Any,
        rect: Rect,
        opacity: float,
    ) -> None:
        shortcut = self.shortcut
        if not image or not shortcut._supports_action(action):
            return

        response = shortcut.ui.icon_button(
            image,
            (rect.x, rect.y),
            (rect.width, rect.height),
            f"navigation_puck_direct_{action}",
            opacity=opacity,
        )
        self._handle_response(context, action, response)

    def _handle_response(
        self,
        context: bpy.types.Context,
        action: str,
        response: typing.Any,
    ) -> None:
        if not response.clicked and not response.dragged:
            return

        shortcut = self.shortcut
        pointer_offset = shortcut.mouse_pos - shortcut.button_center
        apply_view_action(
            shortcut.view_ops,
            shortcut.owner_context,
            context,
            action,
            response.drag_delta,
            shortcut.mouse_pos,
            pointer_offset,
            is_view2d_editor=shortcut._is_view2d_editor(),
            shift=response.shift,
        )
