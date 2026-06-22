import typing

import bpy
import mathutils

from ..imgui.rect import Rect
from ..renderer.circle_outline_command import CircleOutlineCommand
from ..utils.view_math import event_drag_delta
from .editor_context import event_position_in_context
from .puck_assets import all_action_images_loaded
from .shortcut_layout import PUCK_ACTIONS, puck_action_rects
from .view_operation_dispatch import apply_view_action


HOTKEY_MENU_POINTER_DEAD_ZONE_RADIUS = 12.0


class PuckMenuActions:
    """Action-grid hit testing, drawing, and drag dispatch for the puck menu."""

    def __init__(self, menu: typing.Any) -> None:
        self.menu = menu

    def button_rects(self) -> dict[str, Rect]:
        menu = self.menu
        return puck_action_rects(menu.initial_mouse_pos, menu.button_sizes, menu.initial_offset)

    def hotkey_pointer_on_button(self, context: bpy.types.Context, event: bpy.types.Event) -> bool:
        menu = self.menu
        if not hasattr(event, "mouse_region_x") or not hasattr(event, "mouse_region_y"):
            return False

        pointer = menu.owner_context.local_position(event_position_in_context(
            context,
            event,
            menu.owner_context.region_position(menu.mouse_pos),
        ))
        dead_zone_radius = getattr(menu, "hotkey_dead_zone_radius", HOTKEY_MENU_POINTER_DEAD_ZONE_RADIUS)
        if (pointer - menu.initial_mouse_pos).length <= dead_zone_radius:
            return False

        return any(
            menu._supports_action(action) and rect.contains(pointer.x, pointer.y)
            for action, rect in self.button_rects().items()
        )

    def try_drag_select_action(self, context: bpy.types.Context, event: bpy.types.Event) -> bool:
        if not self._drag_select_action_is_ready(event):
            return False

        menu = self.menu
        delta = event_drag_delta(event)
        pointer_offset = menu.mouse_pos - menu.initial_mouse_pos
        action = self._action_at_mouse_position()
        if action is None:
            return False

        self._start_action_drag(context, action, delta, pointer_offset, shift=event.shift)
        return True

    def draw(self, context: bpy.types.Context) -> None:
        menu = self.menu
        menu.ui.begin_frame(menu.mouse_pos)

        rects = self.button_rects()
        if not all_action_images_loaded(menu.action_images):
            return

        for action in PUCK_ACTIONS:
            self._draw_action_button(context, action, menu.action_images[action], rects[action])

        if menu.drag_select and menu._debug_bounds_enabled(context):
            self._draw_drag_select_bounds()

        menu.ui.end_frame()

    def _apply_action_drag(
        self,
        context: bpy.types.Context,
        action: str,
        delta: mathutils.Vector,
        pointer_offset: mathutils.Vector,
        *,
        shift: bool = False,
    ) -> None:
        menu = self.menu
        apply_view_action(
            menu.view_ops,
            menu.owner_context,
            context,
            action,
            delta,
            menu.mouse_pos,
            pointer_offset,
            is_view2d_editor=menu._is_view2d_editor(),
            shift=shift,
        )

    def _start_action_drag(
        self,
        context: bpy.types.Context,
        action: str,
        delta: mathutils.Vector,
        pointer_offset: mathutils.Vector,
        *,
        shift: bool = False,
    ) -> None:
        menu = self.menu
        menu.is_done_operation = True
        self._apply_action_drag(context, action, delta, pointer_offset, shift=shift)

    def _action_start_mouse_pos(self, action: str) -> mathutils.Vector | None:
        menu = self.menu
        return menu.view_ops.action_start_mouse_pos(action, menu._is_view2d_editor())

    def _update_follow_anchor_for_action(self, action: str) -> None:
        menu = self.menu
        if not menu.follow_mouse:
            return

        start_mouse_pos = self._action_start_mouse_pos(action)
        if start_mouse_pos is not None:
            menu.initial_mouse_pos[:] = menu.mouse_pos - start_mouse_pos

    def _drag_select_action_is_ready(self, event: bpy.types.Event) -> bool:
        menu = self.menu
        if not menu.drag_select or not menu.is_pressed or menu.is_done_operation:
            return False

        if event.type != 'MOUSEMOVE':
            return False

        return (menu.mouse_pos - menu.initial_mouse_pos).length >= menu.drag_select_start_distance

    def _action_at_mouse_position(self) -> str | None:
        menu = self.menu
        rects = self.button_rects()
        for action in PUCK_ACTIONS:
            if menu._supports_action(action) and rects[action].contains(menu.mouse_pos.x, menu.mouse_pos.y):
                return action
        return None

    def _draw_action_button(
        self,
        context: bpy.types.Context,
        action: str,
        image: typing.Any,
        rect: Rect,
    ) -> None:
        menu = self.menu
        if not menu._supports_action(action):
            return

        response = menu.ui.icon_button(
            image,
            (rect.x, rect.y),
            (rect.width, rect.height),
        )
        if not response.clicked and not response.dragged:
            return

        self._start_action_drag(
            context,
            action,
            response.drag_delta,
            menu.mouse_pos - menu.initial_mouse_pos,
            shift=response.shift,
        )
        self._update_follow_anchor_for_action(action)

    def _draw_drag_select_bounds(self) -> None:
        menu = self.menu
        menu.ui.renderer.add(CircleOutlineCommand(
            center=(menu.initial_mouse_pos.x, menu.initial_mouse_pos.y),
            radius=menu.drag_select_start_distance,
            color=(0.0, 0.9, 1.0, 0.95),
            width=2.0,
        ))
