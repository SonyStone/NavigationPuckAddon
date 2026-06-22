import typing

import bpy

from ..activation import MODIFIER_KEY_STATE_ATTRS
from ..utils.draw_handler import force_redraw
from ..utils.operator_return import OperatorReturn, OperatorReturnType
from .editor_context import event_position_in_context, event_window_position_is_in_context_area
from .shortcut_layout import clamp_shortcut_center


class ShortcutHotkey:
    """Hotkey activation behavior for the always-on shortcut."""

    def __init__(self, shortcut: typing.Any) -> None:
        self.shortcut = shortcut

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        from .. import keymap

        shortcut = self.shortcut
        if shortcut._menu_is_running():
            return OperatorReturn.PASS_THROUGH

        if not event_window_position_is_in_context_area(context, event):
            return OperatorReturn.PASS_THROUGH

        dismiss_key_type = keymap.held_modifier_hotkey_type(event)
        if not dismiss_key_type and keymap.event_matches_hotkey(event):
            dismiss_key_type = event.type
        if not dismiss_key_type:
            return OperatorReturn.PASS_THROUGH

        self._open_menu_at_event(context, event, dismiss_key_type)
        return OperatorReturn.PASS_THROUGH if dismiss_key_type in MODIFIER_KEY_STATE_ATTRS else OperatorReturn.RUNNING_MODAL

    def _open_menu_at_event(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        dismiss_key_type: str,
    ) -> None:
        shortcut = self.shortcut
        raw_mouse_pos = event_position_in_context(
            context,
            event,
            shortcut.owner_context.region_position(shortcut.mouse_pos),
        )
        shortcut._sync_owner_viewport(context, raw_mouse_pos)
        shortcut.mouse_pos[:] = shortcut.owner_context.local_position(raw_mouse_pos)
        shortcut.owner_context.update_draw_handler(shortcut.draw_handler, context)
        shortcut.button_center[:] = shortcut.mouse_pos
        shortcut.button_center[:] = clamp_shortcut_center(
            shortcut.button_center,
            shortcut.region_size,
            shortcut.margin,
            shortcut.activation_mode,
            shortcut.button_size,
            shortcut.menu_button_size,
            shortcut.menu_gap,
        )
        shortcut._open_puck_menu(context, drag_select=False, dismiss_key_type=dismiss_key_type)
        force_redraw(context)
