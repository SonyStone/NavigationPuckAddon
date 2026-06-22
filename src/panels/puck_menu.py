import math
import typing

import bpy
import mathutils

from ..imgui.ui import UI
from ..operators.view_operations import ViewOperationSet
from ..utils.draw_handler import DrawHandler, force_redraw
from ..utils.operator_return import OperatorReturn, OperatorReturnType
from ..activation import get_activation_mode, get_addon_preferences, get_mode_menu_button_size
from .editor_context import (
    RegionLocalEvent,
    event_position_in_context,
    event_region_position,
)
from .editor_state import EditorState
from .puck_assets import load_action_images
from .owner_context import OwnerContext
from .puck_menu_actions import PuckMenuActions
from .puck_menu_hotkey import PuckMenuHotkey
from .view_operation_dispatch import handle_view_operation_events


class NavigationPuckWidget:
    """Interactive navigation puck overlay for supported Blender editors."""

    def __init__(self) -> None:
        self._init_draw_state()
        self._init_view_state()
        self._init_interaction_state()
        self.actions = PuckMenuActions(self)
        self.hotkey = PuckMenuHotkey(self)

    def _init_draw_state(self) -> None:
        self.draw_handler = DrawHandler()
        self.mouse_pos = mathutils.Vector((0, 0))
        self.initial_mouse_pos = mathutils.Vector((0, 0))

        self.ui = UI()
        self.action_images: dict[str, typing.Any] = {}

    def _init_view_state(self) -> None:
        self.view_ops = ViewOperationSet()
        self.editor_state = EditorState()
        self.owner_context = OwnerContext()

    def _init_interaction_state(self) -> None:
        self.is_pressed = False
        self.is_in_radius = False
        self.is_done_operation = False
        self.auto_dismiss_distance = 200.0
        self.follow_distance = 70.0

        self.button_sizes = 55
        self.initial_offset = (5, 5)
        
        self.follow_mouse = False
        self.drag_select = False
        self.dismiss_on_key_release = False
        self.dismiss_key_type = ""
        self.drag_select_start_distance = 30.0
        self.is_running = False
        self.stop_requested = False

    def ensure_images_loaded(self) -> None:
        """Load the puck icons on demand."""
        load_action_images(self.action_images)

    def _sync_preferences(self, context: bpy.types.Context) -> None:
        prefs = get_addon_preferences(context)
        activation_mode = get_activation_mode(context)
        self.button_sizes = get_mode_menu_button_size(prefs, activation_mode, self.button_sizes)
        self.drag_select_start_distance = max(
            float(getattr(prefs, "drag_select_threshold_radius", self.drag_select_start_distance)),
            0.0,
        )
        self.editor_state.update(context, self.owner_context.region_data)

    def _set_owner_context(
        self,
        context: bpy.types.Context,
        position: mathutils.Vector | None = None,
    ) -> None:
        self.owner_context.set(context, position, update_key=True)
        self._sync_preferences(context)

    def _context_matches(self, context: bpy.types.Context) -> bool:
        return self.owner_context.matches_menu_context(context)

    def _configure_open_state(
        self,
        follow_mouse: bool,
        drag_select: bool,
        dismiss_on_key_release: bool,
        dismiss_key_type: str,
    ) -> None:
        self.is_pressed = follow_mouse or drag_select
        self.is_in_radius = True
        self.is_done_operation = False
        self.follow_mouse = follow_mouse
        self.drag_select = drag_select
        self.dismiss_on_key_release = dismiss_on_key_release
        self.dismiss_key_type = dismiss_key_type

    def _event_positions(
        self,
        event: bpy.types.Event,
        anchor: mathutils.Vector | None,
        dismiss_on_key_release: bool,
    ) -> tuple[mathutils.Vector, mathutils.Vector]:
        if anchor is not None and dismiss_on_key_release:
            raw_event_position = anchor.copy()
        else:
            raw_event_position = event_region_position(event, self.mouse_pos)
        return raw_event_position, anchor or raw_event_position

    def _install_draw_handler(self, context: bpy.types.Context, *, reset_ui: bool = False) -> None:
        self.draw_handler.remove()
        if reset_ui:
            self.ui.ctx.reset_state()
        self.draw_handler.add(context, self.draw_callback)
        self.owner_context.update_draw_handler(self.draw_handler, context)

    def _place_from_event_positions(
        self,
        raw_event_position: mathutils.Vector,
        owner_position: mathutils.Vector,
    ) -> None:
        self.mouse_pos[:] = self.owner_context.local_position(raw_event_position)
        self.initial_mouse_pos[:] = self.owner_context.local_position(owner_position)
        self.ensure_images_loaded()

    def invoke(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        follow_mouse: bool = False,
        drag_select: bool = False,
        anchor: mathutils.Vector | None = None,
        dismiss_on_key_release: bool = False,
        dismiss_key_type: str = "",
    ) -> OperatorReturnType:
        """Start the modal operator and initialize widget"""
        self.is_running = True
        self.stop_requested = False
        self._configure_open_state(follow_mouse, drag_select, dismiss_on_key_release, dismiss_key_type)

        raw_event_position, owner_position = self._event_positions(event, anchor, dismiss_on_key_release)
        self._set_owner_context(context, owner_position)

        self._install_draw_handler(context)
        self._place_from_event_positions(raw_event_position, owner_position)
        force_redraw(context)

        return OperatorReturn.RUNNING_MODAL

    def reopen(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        follow_mouse: bool = False,
        drag_select: bool = False,
        anchor: mathutils.Vector | None = None,
        dismiss_on_key_release: bool = False,
        dismiss_key_type: str = "",
    ) -> OperatorReturnType:
        """Move an already-running menu to the pointer instead of stacking modals."""
        self._configure_open_state(follow_mouse, drag_select, dismiss_on_key_release, dismiss_key_type)

        raw_event_position, owner_position = self._event_positions(event, anchor, dismiss_on_key_release)
        self._set_owner_context(context, owner_position)

        self._install_draw_handler(context, reset_ui=True)
        self._place_from_event_positions(raw_event_position, owner_position)
        force_redraw(context)
        return OperatorReturn.FINISHED

    def finish(
        self,
        context: bpy.types.Context,
        reveal_shortcut: bool = False,
    ) -> OperatorReturnType:
        """Remove draw state and end the menu operator."""
        owner_key = self.owner_context.context_key
        self.draw_handler.remove()
        self.ui.ctx.reset_state()
        self.is_running = False
        self.dismiss_on_key_release = False
        self.dismiss_key_type = ""
        if reveal_shortcut:
            try:
                from .navigation_puck_operators import NavigationPuckShortcutOperator
                NavigationPuckShortcutOperator.reveal_after_menu(context, owner_key, self.mouse_pos)
            except NameError:
                pass
        self.owner_context.clear()
        force_redraw(context)
        return OperatorReturn.FINISHED

    def shutdown(self) -> None:
        """Clear draw state during add-on unregister."""
        self.draw_handler.remove()
        self.ui.ctx.reset_state()
        self.is_running = False
        self.stop_requested = True
        self.dismiss_on_key_release = False
        self.dismiss_key_type = ""
        self.owner_context.clear()

    def _is_view2d_editor(self) -> bool:
        return self.editor_state.is_view2d_editor()

    def _supports_action(self, action: str) -> bool:
        return self.editor_state.supports_action(action)

    def _debug_bounds_enabled(self, context: bpy.types.Context) -> bool:
        prefs = get_addon_preferences(context)
        return bool(getattr(prefs, "debug_shortcut_bounds", False))

    def _local_event_from_event(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> RegionLocalEvent:
        raw_mouse_pos = event_position_in_context(context, event, self.owner_context.region_position(self.mouse_pos))
        self.mouse_pos[:] = self.owner_context.local_position(raw_mouse_pos)
        return RegionLocalEvent(event, self.mouse_pos)

    def _update_follow_anchor_for_active_3d_operations(self) -> None:
        if not self.follow_mouse:
            return

        for handler in self.view_ops.view_3d_handlers():
            if handler.view_op.is_active:
                self.initial_mouse_pos[:] = self.mouse_pos - handler.view_op.start_mouse_pos

    def _finish_handled_view_event(self, context: bpy.types.Context) -> OperatorReturnType:
        self._update_follow_anchor_for_active_3d_operations()
        self.is_done_operation = True
        force_redraw(context)
        return OperatorReturn.RUNNING_MODAL

    def _update_follow_mouse_anchor(self) -> None:
        if not self.follow_mouse or not self.is_pressed:
            return

        pointer_distance = math.dist(self.mouse_pos, self.initial_mouse_pos)  # type: ignore
        if pointer_distance <= self.follow_distance:
            return

        direction = (self.mouse_pos - self.initial_mouse_pos).normalized()
        self.initial_mouse_pos += direction * (pointer_distance - self.follow_distance)

    def _modal_or_passthrough(self, should_pass_through: bool) -> OperatorReturnType:
        return OperatorReturn.PASS_THROUGH if should_pass_through else OperatorReturn.RUNNING_MODAL

    def _initial_modal_result(self, context: bpy.types.Context) -> OperatorReturnType | None:
        if self.stop_requested:
            return self.finish(context)

        if not self._context_matches(context):
            return OperatorReturn.PASS_THROUGH

        return None

    def _escape_result(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType | None:
        if event.type == 'ESC':
            return self.finish(context)
        return None

    def _mark_outside_auto_dismiss_radius(self) -> None:
        if math.dist(self.mouse_pos, self.initial_mouse_pos) > self.auto_dismiss_distance:  # type: ignore
            self.is_in_radius = False

    def _completed_operation_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType | None:
        if self.is_done_operation and not self.view_ops.any_active(self._is_view2d_editor()):
            return self.hotkey.finish_after_completed_operation(context, event)
        return None

    def _drag_select_release_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType | None:
        if self.drag_select and event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.is_pressed = False
            return self.finish(context, reveal_shortcut=True)
        return None

    def _drag_select_action_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType | None:
        if self.actions.try_drag_select_action(context, event):
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL
        return None

    def _outside_radius_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        pass_through_modifier_hotkey_event: bool,
    ) -> OperatorReturnType | None:
        if not self.is_pressed and not self.is_in_radius:
            if self.dismiss_on_key_release and self.actions.hotkey_pointer_on_button(context, event):
                self.is_in_radius = True
                return None
            force_redraw(context)
            return self._modal_or_passthrough(pass_through_modifier_hotkey_event)
        return None

    def _done_operation_release_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType | None:
        if self.is_done_operation and not self.is_pressed:
            return self.hotkey.finish_after_completed_operation(context, event)
        return None

    def _ui_event_result(
        self,
        context: bpy.types.Context,
        local_event: RegionLocalEvent,
    ) -> OperatorReturnType | None:
        if self.ui.ctx.handle_event(local_event):
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL
        return None

    def _modal_entry_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType | None:
        result = self._initial_modal_result(context)
        if result is not None:
            return result

        self.owner_context.update_draw_handler(self.draw_handler, context)
        self.owner_context.run(context, self._sync_preferences)

        return self.hotkey.dismiss_key_release_result(context, event)

    def _pre_view_operation_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType | None:
        self._mark_outside_auto_dismiss_radius()
        return self._completed_operation_result(context, event)

    def _view_operation_event_result(
        self,
        context: bpy.types.Context,
        local_event: RegionLocalEvent,
    ) -> OperatorReturnType | None:
        if handle_view_operation_events(
            self.view_ops,
            self.owner_context,
            context,
            local_event,
            is_view2d_editor=self._is_view2d_editor(),
        ):
            return self._finish_handled_view_event(context)
        return None

    def _drag_select_event_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType | None:
        result = self._drag_select_release_result(context, event)
        if result is not None:
            return result

        return self._drag_select_action_result(context, event)

    def _idle_modal_event_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        local_event: RegionLocalEvent,
        pass_through_modifier_hotkey_event: bool,
    ) -> OperatorReturnType:
        self._update_follow_mouse_anchor()

        result = self._outside_radius_result(context, event, pass_through_modifier_hotkey_event)
        if result is not None:
            return result

        result = self._done_operation_release_result(context, event)
        if result is not None:
            return result

        result = self._ui_event_result(context, local_event)
        if result is not None:
            return result

        force_redraw(context)
        return self._modal_or_passthrough(pass_through_modifier_hotkey_event)

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Handle widget events"""
        result = self._modal_entry_result(context, event)
        if result is not None:
            return result

        local_event = self._local_event_from_event(context, event)

        result = self._escape_result(context, event)
        if result is not None:
            return result

        pass_through_modifier_hotkey_event = self.hotkey.modifier_event_should_pass_through(context, event)

        result = self._pre_view_operation_result(context, event)
        if result is not None:
            return result

        result = self._view_operation_event_result(context, local_event)
        if result is not None:
            return result

        result = self._drag_select_event_result(context, event)
        if result is not None:
            return result

        return self._idle_modal_event_result(context, event, local_event, pass_through_modifier_hotkey_event)

    def draw_callback(self, _op: typing.Any, context: bpy.types.Context):
        """
        Draw shaders UI for viewport overlay

        registered with a DrawHandler(), called after each `force_redraw` call
        """

        if self.view_ops.any_active(self._is_view2d_editor()):
            self.ui.ctx.reset_state()
            return

        self._sync_preferences(context)
        self.actions.draw(context)
