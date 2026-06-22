import typing

import bpy

from ..activation import MODIFIER_KEY_STATE_ATTRS
from ..utils.operator_return import OperatorReturnType
from .puck_invocation import _invoke_navigation_puck_widget


class PuckMenuHotkey:
    """Modifier-hotkey dismissal and reopen policy for the puck menu."""

    def __init__(self, menu: typing.Any) -> None:
        self.menu = menu

    def dismiss_key_release_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType | None:
        menu = self.menu
        if menu.dismiss_on_key_release and event.type == menu.dismiss_key_type and event.value == 'RELEASE':
            menu.view_ops.cancel(menu._is_view2d_editor())
            return menu.finish(context)
        return None

    def finish_after_completed_operation(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType:
        menu = self.menu
        if self._should_reopen_after_action(event):
            return self._reopen_after_action(context)
        return menu.finish(context, reveal_shortcut=True)

    def modifier_event_should_pass_through(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> bool:
        menu = self.menu
        if not self._dismiss_key_is_modifier():
            return False

        if menu.view_ops.any_active(menu._is_view2d_editor()) or menu.ui.ctx.active_id is not None:
            return False

        if event.type == 'LEFTMOUSE':
            return not menu.actions.hotkey_pointer_on_button(context, event)

        return True

    def _dismiss_modifier_is_held(self, event: bpy.types.Event) -> bool:
        menu = self.menu
        modifier_attr = MODIFIER_KEY_STATE_ATTRS.get(menu.dismiss_key_type)
        if modifier_attr is None:
            return False
        if event.type == menu.dismiss_key_type and event.value == 'RELEASE':
            return False
        return bool(getattr(event, modifier_attr, False))

    def _dismiss_key_is_modifier(self) -> bool:
        menu = self.menu
        return menu.dismiss_on_key_release and menu.dismiss_key_type in MODIFIER_KEY_STATE_ATTRS

    def _should_reopen_after_action(self, event: bpy.types.Event) -> bool:
        return self.menu.dismiss_on_key_release and self._dismiss_modifier_is_held(event)

    def _reopen_after_action(self, context: bpy.types.Context) -> OperatorReturnType:
        menu = self.menu
        anchor = menu.owner_context.region_position(menu.mouse_pos)
        dismiss_key_type = menu.dismiss_key_type
        context_override = menu.owner_context.context_override
        result = menu.finish(context)

        try:
            _invoke_navigation_puck_widget(
                context,
                anchor,
                drag_select=False,
                dismiss_on_key_release=True,
                dismiss_key_type=dismiss_key_type,
                context_override=context_override,
            )
        except (ReferenceError, RuntimeError, TypeError) as ex:
            print(f"Navigation Puck hotkey failed to reopen menu: {ex}")

        return result
