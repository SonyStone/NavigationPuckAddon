import math
import typing

import bpy
import mathutils


from ..imgui.ui import UI
from ..imgui.rect import Rect
from ..operators.view_operations import ViewOperationSet
from ..renderer.circle_outline_command import CircleOutlineCommand
from ..utils.draw_handler import DrawHandler, force_redraw
from ..utils.modal import add_modal_handler
from ..utils.operator_return import OperatorReturn, OperatorReturnType
from ..utils.view_math import event_drag_delta
from . import activation_runtime
from ..activation import (
    ACTIVATION_DIRECT_MENU,
    ACTIVATION_HOTKEY_MENU,
    ACTIVATION_SHORTCUT_BUTTON,
    MODIFIER_KEY_STATE_ATTRS,
    get_activation_mode,
    get_addon_preferences,
    get_mode_menu_button_size,
)
from .editor_context import (
    RegionLocalEvent,
    SUPPORTED_EDITOR_TYPES,
    VIEW2D_EDITOR_TYPES,
    ViewportRect,
    _quad_view_entries,
    context_area_key,
    context_editor_type,
    context_key,
    editor_context_override_at_event,
    event_area_position,
    event_position_in_context,
    event_region_position,
    event_window_position_is_in_context_area,
    find_supported_editor_overrides,
    is_supported_editor_context,
    make_context_override,
    region_view3d_for_position,
    viewport_local_rect_for_position,
    viewport_rects_for_position,
)
from .shortcut_layout import (
    PUCK_ACTIONS,
    button_rect,
    clamp_center,
    control_edge_radius,
    cursor_offset,
    direct_menu_rects,
    follow_zone_radius,
    puck_action_rects,
    supports_puck_action,
)
from .puck_assets import all_action_images_loaded, load_action_images, load_shortcut_icon


HOTKEY_MENU_POINTER_DEAD_ZONE_RADIUS = 12.0


def _call_navigation_puck_widget(
    anchor: mathutils.Vector,
    *,
    drag_select: bool,
    dismiss_on_key_release: bool,
    dismiss_key_type: str,
) -> OperatorReturnType:
    return bpy.ops.navigation_puck.widget(
        'INVOKE_DEFAULT',
        follow_mouse=False,
        drag_select=drag_select,
        anchor_x=anchor.x,
        anchor_y=anchor.y,
        dismiss_on_key_release=dismiss_on_key_release,
        dismiss_key_type=dismiss_key_type,
    )


def _invoke_navigation_puck_widget(
    context: bpy.types.Context,
    anchor: mathutils.Vector,
    *,
    drag_select: bool,
    dismiss_on_key_release: bool,
    dismiss_key_type: str,
    context_override: dict[str, typing.Any] | None = None,
) -> OperatorReturnType:
    if context_override:
        with context.temp_override(**context_override):
            return _call_navigation_puck_widget(
                anchor,
                drag_select=drag_select,
                dismiss_on_key_release=dismiss_on_key_release,
                dismiss_key_type=dismiss_key_type,
            )
    return _call_navigation_puck_widget(
        anchor,
        drag_select=drag_select,
        dismiss_on_key_release=dismiss_on_key_release,
        dismiss_key_type=dismiss_key_type,
    )


def _run_with_context_override(
    context: bpy.types.Context,
    context_override: dict[str, typing.Any] | None,
    callback: typing.Callable[[bpy.types.Context], typing.Any],
) -> typing.Any:
    if not context_override:
        return callback(context)

    try:
        with context.temp_override(**context_override):
            return callback(bpy.context)
    except (ReferenceError, RuntimeError, TypeError):
        return callback(context)


class NavigationPuckWidget:
    """Interactive navigation puck overlay for supported Blender editors."""

    def __init__(self) -> None:
        self._init_draw_state()
        self._init_view_state()
        self._init_interaction_state()

    def _init_draw_state(self) -> None:
        self.draw_handler = DrawHandler()
        self.mouse_pos = mathutils.Vector((0, 0))
        self.initial_mouse_pos = mathutils.Vector((0, 0))

        self.ui = UI()
        self.action_images: dict[str, typing.Any] = {}

    def _init_view_state(self) -> None:
        self.view_ops = ViewOperationSet()
        self.editor_type: str | None = None
        self.context_key: tuple[int, int, int, int] | None = None
        self.context_override: dict[str, typing.Any] | None = None
        self.owner_viewport_rects: tuple[ViewportRect, ...] = ()
        self.owner_viewport_rect: ViewportRect = (0, 0, 1, 1)
        self.owner_region_data: bpy.types.RegionView3D | None = None
        self.is_camera_view = False
        self.is_camera_view_locked = False

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
        editor_type = context_editor_type(context)
        if editor_type in SUPPORTED_EDITOR_TYPES:
            self.editor_type = editor_type
        self.is_camera_view = False
        self.is_camera_view_locked = False
        if self.editor_type == 'VIEW_3D':
            rv3d = self.owner_region_data or region_view3d_for_position(context)
            if rv3d is None:
                return
            self.is_camera_view = rv3d.view_perspective == 'CAMERA'
            self.is_camera_view_locked = self.is_camera_view and bool(getattr(context.space_data, "lock_camera", False))

    def _set_owner_context(
        self,
        context: bpy.types.Context,
        position: mathutils.Vector | None = None,
    ) -> None:
        self.context_key = context_key(context)
        self.context_override = make_context_override(context, position)
        self.owner_viewport_rect = viewport_local_rect_for_position(context, position)
        self.owner_viewport_rects = viewport_rects_for_position(context, position)
        self.owner_region_data = region_view3d_for_position(context, position)
        self._sync_preferences(context)

    def _update_draw_context(self, context: bpy.types.Context) -> None:
        self.draw_handler.update_context(context, self.owner_viewport_rects, self.owner_region_data)

    def _owner_local_position(self, position: mathutils.Vector) -> mathutils.Vector:
        return mathutils.Vector((
            position.x - self.owner_viewport_rect[0],
            position.y - self.owner_viewport_rect[1],
        ))

    def _owner_region_position(self, position: mathutils.Vector) -> mathutils.Vector:
        return mathutils.Vector((
            position.x + self.owner_viewport_rect[0],
            position.y + self.owner_viewport_rect[1],
        ))

    def _context_matches(self, context: bpy.types.Context) -> bool:
        if self.context_key is None:
            return True

        current_key = context_key(context)
        if current_key == self.context_key:
            return True

        # In Quad View Blender can deliver modal events through a different
        # WINDOW region than the one that owns the drawn menu.
        return bool(_quad_view_entries(context) and context_area_key(context) == self.context_key[:3])

    def _run_in_owner_context(
        self,
        context: bpy.types.Context,
        callback: typing.Callable[[bpy.types.Context], typing.Any],
    ) -> typing.Any:
        return _run_with_context_override(context, self.context_override, callback)

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
        self._update_draw_context(context)

    def _place_from_event_positions(
        self,
        raw_event_position: mathutils.Vector,
        owner_position: mathutils.Vector,
    ) -> None:
        self.mouse_pos[:] = self._owner_local_position(raw_event_position)
        self.initial_mouse_pos[:] = self._owner_local_position(owner_position)
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
        owner_key = self.context_key
        self.draw_handler.remove()
        self.ui.ctx.reset_state()
        self.is_running = False
        self.dismiss_on_key_release = False
        self.dismiss_key_type = ""
        if reveal_shortcut:
            try:
                NavigationPuckShortcutOperator.reveal_after_menu(context, owner_key, self.mouse_pos)
            except NameError:
                pass
        self.context_key = None
        self.context_override = None
        self.owner_viewport_rects = ()
        self.owner_viewport_rect = (0, 0, 1, 1)
        self.owner_region_data = None
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
        self.context_key = None
        self.context_override = None
        self.owner_viewport_rects = ()
        self.owner_viewport_rect = (0, 0, 1, 1)
        self.owner_region_data = None

    def _is_view2d_editor(self) -> bool:
        return self.editor_type in VIEW2D_EDITOR_TYPES

    def _supports_action(self, action: str) -> bool:
        return supports_puck_action(
            action,
            is_view2d_editor=self._is_view2d_editor(),
            is_camera_view=self.is_camera_view,
            is_camera_view_locked=self.is_camera_view_locked,
        )

    def _dismiss_modifier_is_held(self, event: bpy.types.Event) -> bool:
        modifier_attr = MODIFIER_KEY_STATE_ATTRS.get(self.dismiss_key_type)
        if modifier_attr is None:
            return False
        if event.type == self.dismiss_key_type and event.value == 'RELEASE':
            return False
        return bool(getattr(event, modifier_attr, False))

    def _dismiss_key_is_modifier(self) -> bool:
        return self.dismiss_on_key_release and self.dismiss_key_type in MODIFIER_KEY_STATE_ATTRS

    def _should_reopen_hotkey_menu_after_action(self, event: bpy.types.Event) -> bool:
        return self.dismiss_on_key_release and self._dismiss_modifier_is_held(event)

    def _reopen_hotkey_menu_after_action(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType:
        anchor = self._owner_region_position(self.mouse_pos)
        dismiss_key_type = self.dismiss_key_type
        context_override = self.context_override
        result = self.finish(context)

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

    def _finish_after_completed_operation(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        if self._should_reopen_hotkey_menu_after_action(event):
            return self._reopen_hotkey_menu_after_action(context, event)
        return self.finish(context, reveal_shortcut=True)

    def _hotkey_menu_pointer_on_button(self, context: bpy.types.Context, event: bpy.types.Event) -> bool:
        if not hasattr(event, "mouse_region_x") or not hasattr(event, "mouse_region_y"):
            return False

        pointer = self._owner_local_position(event_position_in_context(context, event, self._owner_region_position(self.mouse_pos)))
        if (pointer - self.initial_mouse_pos).length <= HOTKEY_MENU_POINTER_DEAD_ZONE_RADIUS:
            return False

        return any(
            self._supports_action(action) and rect.contains(pointer.x, pointer.y)
            for action, rect in self._button_rects().items()
        )

    def _modifier_hotkey_event_should_pass_through(self, context: bpy.types.Context, event: bpy.types.Event) -> bool:
        if not self._dismiss_key_is_modifier():
            return False

        if self.view_ops.any_active(self._is_view2d_editor()) or self.ui.ctx.active_id is not None:
            return False

        if event.type == 'LEFTMOUSE':
            return not self._hotkey_menu_pointer_on_button(context, event)

        return True

    def _debug_bounds_enabled(self, context: bpy.types.Context) -> bool:
        prefs = get_addon_preferences(context)
        return bool(getattr(prefs, "debug_shortcut_bounds", False))

    def _button_rects(self) -> dict[str, Rect]:
        return puck_action_rects(self.initial_mouse_pos, self.button_sizes, self.initial_offset)

    def _apply_action_drag(
        self,
        context: bpy.types.Context,
        action: str,
        delta: mathutils.Vector,
        pointer_offset: mathutils.Vector,
        *,
        shift: bool = False,
    ) -> None:
        self._run_in_owner_context(
            context,
            lambda owner_context: self.view_ops.apply_action(
                owner_context,
                action,
                delta,
                self.mouse_pos,
                pointer_offset,
                self._is_view2d_editor(),
                shift=shift,
            ),
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
        self.is_done_operation = True
        self._apply_action_drag(context, action, delta, pointer_offset, shift=shift)

    def _action_start_mouse_pos(self, action: str) -> mathutils.Vector | None:
        return self.view_ops.action_start_mouse_pos(action, self._is_view2d_editor())

    def _update_follow_anchor_for_action(self, action: str) -> None:
        if not self.follow_mouse:
            return

        start_mouse_pos = self._action_start_mouse_pos(action)
        if start_mouse_pos is not None:
            self.initial_mouse_pos[:] = self.mouse_pos - start_mouse_pos

    def _drag_select_action_is_ready(self, event: bpy.types.Event) -> bool:
        if not self.drag_select or not self.is_pressed or self.is_done_operation:
            return False

        if event.type != 'MOUSEMOVE':
            return False

        return (self.mouse_pos - self.initial_mouse_pos).length >= self.drag_select_start_distance

    def _action_at_mouse_position(self) -> str | None:
        rects = self._button_rects()
        for action in PUCK_ACTIONS:
            if self._supports_action(action) and rects[action].contains(self.mouse_pos.x, self.mouse_pos.y):
                return action
        return None

    def _try_drag_select_action(self, context: bpy.types.Context, event: bpy.types.Event) -> bool:
        if not self._drag_select_action_is_ready(event):
            return False

        delta = event_drag_delta(event)
        pointer_offset = self.mouse_pos - self.initial_mouse_pos
        action = self._action_at_mouse_position()
        if action is None:
            return False

        self._start_action_drag(context, action, delta, pointer_offset, shift=event.shift)
        return True

    def _draw_action_button(
        self,
        context: bpy.types.Context,
        action: str,
        image: typing.Any,
        rect: Rect,
    ) -> None:
        if not self._supports_action(action):
            return

        response = self.ui.icon_button(
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
            self.mouse_pos - self.initial_mouse_pos,
            shift=response.shift,
        )
        self._update_follow_anchor_for_action(action)

    def _local_event_from_event(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> RegionLocalEvent:
        raw_mouse_pos = event_position_in_context(context, event, self._owner_region_position(self.mouse_pos))
        self.mouse_pos[:] = self._owner_local_position(raw_mouse_pos)
        return RegionLocalEvent(event, self.mouse_pos)

    def _handle_view_operation_events(
        self,
        context: bpy.types.Context,
        local_event: RegionLocalEvent,
    ) -> bool:
        handled_view_event = False
        for view_handler in self.view_ops.handlers(self._is_view2d_editor()):
            handled_view_event = self._run_in_owner_context(
                context,
                lambda owner_context, handler=view_handler: handler.event_handler(owner_context, local_event),
            ) or handled_view_event
        return handled_view_event

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

    def _dismiss_key_release_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType | None:
        if self.dismiss_on_key_release and event.type == self.dismiss_key_type and event.value == 'RELEASE':
            self.view_ops.cancel(self._is_view2d_editor())
            return self.finish(context)
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
            return self._finish_after_completed_operation(context, event)
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
        if self._try_drag_select_action(context, event):
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
            if self.dismiss_on_key_release and self._hotkey_menu_pointer_on_button(context, event):
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
            return self._finish_after_completed_operation(context, event)
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

        self._update_draw_context(context)
        self._run_in_owner_context(context, self._sync_preferences)

        return self._dismiss_key_release_result(context, event)

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
        if self._handle_view_operation_events(context, local_event):
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

        pass_through_modifier_hotkey_event = self._modifier_hotkey_event_should_pass_through(context, event)

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
        self.ui.begin_frame(self.mouse_pos)

        rects = self._button_rects()

        if not all_action_images_loaded(self.action_images):
            return

        for action in PUCK_ACTIONS:
            self._draw_action_button(context, action, self.action_images[action], rects[action])

        if self.drag_select and self._debug_bounds_enabled(context):
            self.ui.renderer.add(CircleOutlineCommand(
                center=(self.initial_mouse_pos.x, self.initial_mouse_pos.y),
                radius=self.drag_select_start_distance,
                color=(0.0, 0.9, 1.0, 0.95),
                width=2.0,
            ))

        self.ui.end_frame()


class NavigationPuckShortcut:
    """Viewport shortcut button that opens the navigation puck."""

    def __init__(self) -> None:
        self._init_draw_state()
        self._init_owner_context_state()
        self.view_ops = ViewOperationSet()
        self._init_preference_defaults()

    def _init_draw_state(self) -> None:
        self.draw_handler = DrawHandler()
        self.ui = UI()
        self.mouse_pos = mathutils.Vector((0.0, 0.0))
        self.last_mouse_pos = mathutils.Vector((0.0, 0.0))
        self.button_center = mathutils.Vector((42.0, 42.0))
        self.region_size = mathutils.Vector((1.0, 1.0))
        self.icon = None
        self.direct_menu_images: dict[str, typing.Any] = {}
        self.opacity = 0.0
        self.target_opacity = 0.0
        self.is_running = False
        self.stop_requested = False
        self.press_started_on_button = False

    def _init_owner_context_state(self) -> None:
        self.context_key: tuple[int, int, int, int] | None = None
        self.context_override: dict[str, typing.Any] | None = None
        self.owner_viewport_rects: tuple[ViewportRect, ...] = ()
        self.owner_viewport_rect: ViewportRect = (0, 0, 1, 1)
        self.owner_region_data: bpy.types.RegionView3D | None = None
        self.pointer_in_owner_area = True
        self.modal_generation = 0
        self.editor_type: str | None = None
        self.is_camera_view = False
        self.is_camera_view_locked = False

    def _init_preference_defaults(self) -> None:
        self.button_size = 45.0
        self.menu_button_size = 55.0
        self.margin = 14.0
        self.cursor_distance = 80.0
        self.cursor_position = 'BOTTOM_LEFT'
        self.activation_mode = ACTIVATION_SHORTCUT_BUTTON
        self.cursor_offset = cursor_offset(self.cursor_position, self.cursor_distance)
        self.follow_zone_radius = follow_zone_radius(
            self.cursor_offset,
            control_edge_radius(self.activation_mode, self.button_size, self.menu_button_size),
        )
        self.idle_opacity = 0.0
        self.click_opacity_threshold = 0.12
        self.fade_zone_min_inset = 10.0
        self.fade_zone_inset_percent = 40.0

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Start the shortcut modal overlay."""
        self.is_running = True
        self.stop_requested = False
        self.context_key = self._context_key(context)
        self._sync_preferences(context)
        if self.activation_mode == ACTIVATION_SHORTCUT_BUTTON:
            self._ensure_shortcut_icon()
        self._update_region_size(context)
        raw_mouse_pos = self._event_region_pos(event, self.button_center)
        self._sync_owner_viewport(context, raw_mouse_pos)
        self.pointer_in_owner_area = event_window_position_is_in_context_area(context, event)
        self._update_region_size(context)
        self.mouse_pos[:] = self._owner_local_position(raw_mouse_pos)
        self.last_mouse_pos[:] = self.mouse_pos
        if self.pointer_in_owner_area:
            self._place_button_from_cursor()
            self._update_target_opacity()
        else:
            self.target_opacity = 0.0
            self.opacity = 0.0
        self.draw_handler.remove()
        self.ui.ctx.reset_state()
        self.draw_handler.add(context, self.draw_callback)
        self._update_draw_context(context)
        force_redraw(context)
        return OperatorReturn.RUNNING_MODAL

    def _ensure_direct_menu_images(self) -> None:
        load_action_images(self.direct_menu_images)

    def _ensure_shortcut_icon(self) -> None:
        if self.icon is None:
            self.icon = load_shortcut_icon()

    def shutdown(self) -> None:
        """Request a clean modal shutdown from add-on unregister."""
        self.stop_requested = True
        self.modal_generation += 1
        self.draw_handler.remove()
        self.ui.ctx.reset_state()
        self.is_running = False
        self.press_started_on_button = False
        self.context_key = None
        self.context_override = None
        self.owner_viewport_rects = ()
        self.owner_viewport_rect = (0, 0, 1, 1)
        self.owner_region_data = None
        self.pointer_in_owner_area = True

    def finish(self, context: bpy.types.Context) -> OperatorReturnType:
        """End the shortcut operator and clear draw/timer resources."""
        self.draw_handler.remove()
        self.ui.ctx.reset_state()
        self.is_running = False
        self.context_key = None
        self.context_override = None
        self.owner_viewport_rects = ()
        self.owner_viewport_rect = (0, 0, 1, 1)
        self.owner_region_data = None
        self.pointer_in_owner_area = True
        self.press_started_on_button = False
        force_redraw(context)
        return OperatorReturn.FINISHED

    def next_modal_generation(self) -> int:
        """Invalidate older modal operator instances and return the active generation."""
        self.modal_generation += 1
        return self.modal_generation

    def refresh_context(self, context: bpy.types.Context) -> None:
        """Refresh draw state when Blender changes the active 3D View area."""
        context_key = self._context_key(context)
        if context_key != self.context_key:
            self.context_key = context_key
            self._sync_owner_viewport(context, self._owner_region_position(self.mouse_pos))
            self.draw_handler.remove()
            self.draw_handler.add(context, self.draw_callback)
        elif self.context_override is None:
            self._sync_owner_viewport(context, self._owner_region_position(self.mouse_pos))

        self._update_draw_context(context)
        self._sync_preferences(context)
        self._update_region_size(context)
        self._clamp_button_center()
        force_redraw(context)

    def reveal_after_menu(self, mouse_pos: mathutils.Vector) -> None:
        """Show the shortcut near the cursor after a puck action finishes."""
        self._reveal_at_cursor(mouse_pos)

    def _reveal_at_cursor(self, mouse_pos: mathutils.Vector) -> None:
        self.mouse_pos[:] = mouse_pos
        self.button_center[:] = mouse_pos
        self._clamp_button_center()
        self.target_opacity = 1.0
        self.opacity = 1.0
        self.press_started_on_button = False
        self.ui.ctx.reset_state()

    def _sync_owner_viewport(
        self,
        context: bpy.types.Context,
        position: mathutils.Vector | None = None,
    ) -> None:
        self.context_override = make_context_override(context, position)
        self.owner_viewport_rect = viewport_local_rect_for_position(context, position)
        self.owner_viewport_rects = viewport_rects_for_position(context, position)
        self.owner_region_data = region_view3d_for_position(context, position)
        self._sync_preferences(context)

    def _update_draw_context(self, context: bpy.types.Context) -> None:
        self.draw_handler.update_context(context, self.owner_viewport_rects, self.owner_region_data)

    def _owner_local_position(self, position: mathutils.Vector) -> mathutils.Vector:
        return mathutils.Vector((
            position.x - self.owner_viewport_rect[0],
            position.y - self.owner_viewport_rect[1],
        ))

    def _owner_region_position(self, position: mathutils.Vector) -> mathutils.Vector:
        return mathutils.Vector((
            position.x + self.owner_viewport_rect[0],
            position.y + self.owner_viewport_rect[1],
        ))

    def _event_has_region_position(self, event: bpy.types.Event) -> bool:
        return hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y")

    def _sync_pointer_from_event(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        *,
        refresh_owner: bool = True,
    ) -> tuple[mathutils.Vector, RegionLocalEvent]:
        previous_mouse_pos = self.mouse_pos.copy()
        raw_mouse_pos = event_position_in_context(context, event, self._owner_region_position(self.mouse_pos))
        if refresh_owner:
            self._sync_owner_viewport(context, raw_mouse_pos)
        self.mouse_pos[:] = self._owner_local_position(raw_mouse_pos)
        self._update_draw_context(context)
        return previous_mouse_pos, RegionLocalEvent(event, self.mouse_pos)

    def _has_active_pointer_interaction(self) -> bool:
        return (
            self.press_started_on_button
            or self.ui.ctx.active_id is not None
            or self.view_ops.any_active(self._is_view2d_editor())
        )

    def _another_shortcut_has_active_pointer_interaction(self) -> bool:
        try:
            return NavigationPuckShortcutOperator.has_active_pointer_interaction(excluding=self)
        except NameError:
            return False

    def _hide_for_sibling_interaction(self, context: bpy.types.Context) -> OperatorReturnType:
        self.target_opacity = 0.0
        self.opacity = 0.0
        self.press_started_on_button = False
        self.ui.ctx.reset_state()
        force_redraw(context)
        return OperatorReturn.PASS_THROUGH

    def _hide_outside_owner_area(self, context: bpy.types.Context) -> OperatorReturnType:
        should_redraw = (
            self.pointer_in_owner_area
            or self.press_started_on_button
            or self.opacity > 0.0
            or self.target_opacity > 0.0
            or self.ui.ctx.active_id is not None
        )
        self.pointer_in_owner_area = False
        self.press_started_on_button = False
        self.target_opacity = 0.0
        self.opacity = 0.0
        if should_redraw:
            self.ui.ctx.reset_state()
            force_redraw(context)
        return OperatorReturn.PASS_THROUGH

    def _outside_owner_area_event_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType | None:
        if self._has_active_pointer_interaction():
            self.pointer_in_owner_area = True
            return None

        if event_window_position_is_in_context_area(context, event):
            self.pointer_in_owner_area = True
            return None

        return self._hide_outside_owner_area(context)

    def _hide_while_menu_runs(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType:
        if self._event_has_region_position(event):
            self._sync_pointer_from_event(context, event)
        self.press_started_on_button = False
        self.target_opacity = 0.0
        self.opacity = 0.0
        force_redraw(context)
        return OperatorReturn.PASS_THROUGH

    def _handle_shortcut_mousemove(
        self,
        context: bpy.types.Context,
        previous_mouse_pos: mathutils.Vector,
    ) -> OperatorReturnType:
        self._update_button_position()
        self._update_target_opacity(previous_mouse_pos)
        force_redraw(context)
        return OperatorReturn.PASS_THROUGH

    def _handle_shortcut_leftmouse(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        local_event: RegionLocalEvent,
    ) -> OperatorReturnType | None:
        is_over_button = self._is_clickable() and self._button_rect().contains(self.mouse_pos.x, self.mouse_pos.y)

        if event.value == 'PRESS' and is_over_button:
            self.press_started_on_button = True
            self.ui.ctx.handle_event(local_event)
            self._open_puck_menu(context)
            self.press_started_on_button = False
            self.target_opacity = 0.0
            self.opacity = 0.0
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        if event.value == 'RELEASE' and self.press_started_on_button:
            self.press_started_on_button = False
            self.ui.ctx.handle_event(local_event)
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        return None

    def _handle_view_operation_events(
        self,
        context: bpy.types.Context,
        local_event: RegionLocalEvent,
    ) -> bool:
        handled_view_event = False
        for view_handler in self.view_ops.handlers(self._is_view2d_editor()):
            handled_view_event = self._run_in_owner_context(
                context,
                lambda owner_context, handler=view_handler: handler.event_handler(owner_context, local_event),
            ) or handled_view_event
        return handled_view_event

    def _activation_mode_event_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType | None:
        if self.activation_mode == ACTIVATION_HOTKEY_MENU:
            return self._hotkey_event_handler(context, event)

        if self.activation_mode == ACTIVATION_DIRECT_MENU:
            if (
                not self._has_active_pointer_interaction()
                and self._another_shortcut_has_active_pointer_interaction()
            ):
                return self._hide_for_sibling_interaction(context)
            return self._direct_menu_event_handler(context, event)

        if self._menu_is_running():
            return self._hide_while_menu_runs(context, event)

        return None

    def _shortcut_button_event_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        previous_mouse_pos: mathutils.Vector,
        local_event: RegionLocalEvent,
    ) -> OperatorReturnType:
        if event.type == 'MOUSEMOVE':
            return self._handle_shortcut_mousemove(context, previous_mouse_pos)

        if event.type == 'LEFTMOUSE':
            result = self._handle_shortcut_leftmouse(context, event, local_event)
            if result is not None:
                return result

        return OperatorReturn.PASS_THROUGH

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Handle mouse movement/clicks while passing normal viewport input through."""
        if self.stop_requested:
            return self.finish(context)

        if not self._context_matches(context):
            return OperatorReturn.PASS_THROUGH

        outside_owner_area_result = self._outside_owner_area_event_result(context, event)
        if outside_owner_area_result is not None:
            return outside_owner_area_result

        self._sync_preferences(context)
        self._update_region_size(context)

        result = self._activation_mode_event_result(context, event)
        if result is not None:
            return result

        if not self._event_has_region_position(event):
            return OperatorReturn.PASS_THROUGH

        previous_mouse_pos, local_event = self._sync_pointer_from_event(context, event)
        return self._shortcut_button_event_result(context, event, previous_mouse_pos, local_event)

    def _continue_direct_menu_view_operation(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        local_event: RegionLocalEvent,
        view_operation_was_active: bool,
    ) -> OperatorReturnType:
        handled_view_event = self._handle_view_operation_events(context, local_event)
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.ui.ctx.handle_event(local_event)
        if not self.view_ops.any_active(self._is_view2d_editor()):
            self._reveal_at_cursor(self.mouse_pos)
        force_redraw(context)
        return OperatorReturn.RUNNING_MODAL if handled_view_event or view_operation_was_active else OperatorReturn.PASS_THROUGH

    def _handle_direct_menu_mousemove(
        self,
        context: bpy.types.Context,
        previous_mouse_pos: mathutils.Vector,
        local_event: RegionLocalEvent,
    ) -> OperatorReturnType:
        if self.ui.ctx.active_id is None:
            self._update_button_position()
            self._update_target_opacity(previous_mouse_pos)
        self.ui.ctx.handle_event(local_event)
        force_redraw(context)
        return OperatorReturn.RUNNING_MODAL if self.ui.ctx.active_id is not None else OperatorReturn.PASS_THROUGH

    def _handle_direct_menu_leftmouse(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        local_event: RegionLocalEvent,
    ) -> OperatorReturnType | None:
        is_over_menu = self._direct_menu_is_clickable() and self._direct_menu_contains(self.mouse_pos.x, self.mouse_pos.y)

        if event.value == 'PRESS' and is_over_menu:
            self.ui.ctx.handle_event(local_event)
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        if event.value == 'RELEASE' and self.ui.ctx.active_id is not None:
            self.ui.ctx.handle_event(local_event)
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        return None

    def _direct_menu_pointer_event_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        local_event: RegionLocalEvent,
        previous_mouse_pos: mathutils.Vector,
    ) -> OperatorReturnType:
        if event.type == 'MOUSEMOVE':
            return self._handle_direct_menu_mousemove(context, previous_mouse_pos, local_event)

        if event.type == 'LEFTMOUSE':
            result = self._handle_direct_menu_leftmouse(context, event, local_event)
            if result is not None:
                return result

        return OperatorReturn.PASS_THROUGH

    def _hotkey_event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        from .. import keymap

        if self._menu_is_running():
            return OperatorReturn.PASS_THROUGH

        if not event_window_position_is_in_context_area(context, event):
            return OperatorReturn.PASS_THROUGH

        dismiss_key_type = keymap.held_modifier_hotkey_type(event)
        if not dismiss_key_type and keymap.event_matches_hotkey(event):
            dismiss_key_type = event.type
        if not dismiss_key_type:
            return OperatorReturn.PASS_THROUGH

        raw_mouse_pos = event_position_in_context(context, event, self._owner_region_position(self.mouse_pos))
        self._sync_owner_viewport(context, raw_mouse_pos)
        self.mouse_pos[:] = self._owner_local_position(raw_mouse_pos)
        self._update_draw_context(context)
        self.button_center[:] = self.mouse_pos
        self._clamp_button_center()
        self._open_puck_menu(context, drag_select=False, dismiss_key_type=dismiss_key_type)
        force_redraw(context)
        return OperatorReturn.PASS_THROUGH if dismiss_key_type in MODIFIER_KEY_STATE_ATTRS else OperatorReturn.RUNNING_MODAL

    def _direct_menu_event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        if self._menu_is_running():
            return OperatorReturn.PASS_THROUGH

        if not self._event_has_region_position(event):
            return OperatorReturn.PASS_THROUGH

        lock_owner_context = self._has_active_pointer_interaction()
        previous_mouse_pos, local_event = self._sync_pointer_from_event(
            context,
            event,
            refresh_owner=not lock_owner_context,
        )
        view_operation_was_active = self.view_ops.any_active(self._is_view2d_editor())
        if view_operation_was_active:
            return self._continue_direct_menu_view_operation(context, event, local_event, view_operation_was_active)

        return self._direct_menu_pointer_event_result(context, event, local_event, previous_mouse_pos)

    def _shortcut_draw_opacity(self, context: bpy.types.Context) -> tuple[float, bool]:
        debug_bounds = self._debug_bounds_enabled(context)
        draw_opacity = max(self.opacity, 0.65) if debug_bounds else self.opacity
        return draw_opacity, debug_bounds

    def _draw_shortcut_button(self, button_rect: Rect, opacity: float) -> typing.Any | None:
        if self.icon:
            return self.ui.icon_button(
                self.icon,
                (button_rect.x, button_rect.y),
                (self.button_size, self.button_size),
                "navigation_puck_shortcut",
                opacity=opacity,
            )

        return None

    def _draw_shortcut_debug_bounds(self) -> None:
        self.ui.renderer.add(CircleOutlineCommand(
            center=(self.button_center.x, self.button_center.y),
            radius=self.follow_zone_radius,
            color=(0.0, 0.85, 1.0, 0.85),
            width=2.0,
        ))
        self.ui.renderer.add(CircleOutlineCommand(
            center=(self.button_center.x, self.button_center.y),
            radius=self._fade_start_radius(),
            color=(1.0, 0.35, 0.0, 0.95),
            width=2.0,
        ))
        self.ui.renderer.add(CircleOutlineCommand(
            center=(self.button_center.x, self.button_center.y),
            radius=self.button_size * 0.5,
            color=(0.2, 1.0, 0.25, 1.0),
            width=2.0,
        ))

    def _draw_activation_mode_overlay(self, context: bpy.types.Context) -> bool:
        if self.activation_mode == ACTIVATION_HOTKEY_MENU:
            return True

        if self.activation_mode == ACTIVATION_DIRECT_MENU:
            self._draw_direct_menu(context)
            return True

        return False

    def _draw_shortcut_overlay(self, context: bpy.types.Context) -> None:
        if self._menu_is_running():
            return

        draw_opacity, debug_bounds = self._shortcut_draw_opacity(context)
        if draw_opacity <= 0.01:
            return

        self.ui.begin_frame(self.mouse_pos)
        response = self._draw_shortcut_button(self._button_rect(), draw_opacity)
        if debug_bounds:
            self._draw_shortcut_debug_bounds()
        if response and response.hovered:
            self.target_opacity = 1.0
            self.opacity = 1.0

        self.ui.end_frame()

    def draw_callback(self, _op: typing.Any, context: bpy.types.Context):
        """Draw the shortcut icon and its debug zones."""
        self._sync_preferences(context)
        if not self.pointer_in_owner_area and not self._has_active_pointer_interaction():
            return

        if self._draw_activation_mode_overlay(context):
            return

        self._draw_shortcut_overlay(context)

    def _direct_menu_draw_opacity(self, context: bpy.types.Context) -> tuple[float, bool]:
        debug_bounds = self._debug_bounds_enabled(context)
        draw_opacity = max(self.opacity, 0.65) if debug_bounds else self.opacity
        return draw_opacity, debug_bounds

    def _draw_direct_menu_debug_bounds(self) -> None:
        self.ui.renderer.add(CircleOutlineCommand(
            center=(self.button_center.x, self.button_center.y),
            radius=self.follow_zone_radius,
            color=(0.0, 0.85, 1.0, 0.85),
            width=2.0,
        ))

    def _draw_direct_menu(self, context: bpy.types.Context) -> None:
        if self._menu_is_running():
            return

        if (
            not self._has_active_pointer_interaction()
            and self._another_shortcut_has_active_pointer_interaction()
        ):
            self.ui.ctx.reset_state()
            return

        if self.view_ops.any_active(self._is_view2d_editor()):
            self.ui.ctx.reset_state()
            return

        self._ensure_direct_menu_images()
        draw_opacity, debug_bounds = self._direct_menu_draw_opacity(context)
        if draw_opacity <= 0.01:
            return

        self.ui.begin_frame(self.mouse_pos)
        rects = self._direct_menu_rects()
        for action in PUCK_ACTIONS:
            self._draw_direct_menu_action(context, action, self.direct_menu_images[action], rects[action], draw_opacity)

        if debug_bounds:
            self._draw_direct_menu_debug_bounds()

        self.ui.end_frame()

    def _handle_direct_menu_response(
        self,
        context: bpy.types.Context,
        action: str,
        response: typing.Any,
    ) -> None:
        if not response.clicked and not response.dragged:
            return

        pointer_offset = self.mouse_pos - self.button_center
        self._run_in_owner_context(
            context,
            lambda owner_context: self.view_ops.apply_action(
                owner_context,
                action,
                response.drag_delta,
                self.mouse_pos,
                pointer_offset,
                self._is_view2d_editor(),
                shift=response.shift,
            ),
        )

    def _open_puck_menu(
        self,
        context: bpy.types.Context,
        drag_select: bool = True,
        dismiss_key_type: str = "",
    ) -> None:
        dismiss_on_key_release = bool(dismiss_key_type)
        anchor = self._owner_region_position(self.button_center)
        try:
            _invoke_navigation_puck_widget(
                context,
                anchor,
                drag_select=drag_select,
                dismiss_on_key_release=dismiss_on_key_release,
                dismiss_key_type=dismiss_key_type,
                context_override=self.context_override,
            )
        except RuntimeError as ex:
            print(f"Navigation Puck shortcut failed to open menu: {ex}")

    def _is_clickable(self) -> bool:
        return self.opacity >= self.click_opacity_threshold

    def _button_rect(self) -> Rect:
        return button_rect(self.button_center, self.button_size)

    def _direct_menu_rects(self) -> dict[str, Rect]:
        return direct_menu_rects(self.button_center, self.menu_button_size)

    def _direct_menu_contains(self, x: float, y: float) -> bool:
        return any(
            self._supports_action(action) and rect.contains(x, y)
            for action, rect in self._direct_menu_rects().items()
        )

    def _direct_menu_is_clickable(self) -> bool:
        return self.opacity >= self.click_opacity_threshold

    def _cursor_in_follow_zone(self) -> bool:
        return (self.mouse_pos - self.button_center).length <= self.follow_zone_radius

    def _draw_direct_menu_action(
        self,
        context: bpy.types.Context,
        action: str,
        image: typing.Any,
        rect: Rect,
        opacity: float,
    ) -> None:
        if not image or not self._supports_action(action):
            return

        response = self.ui.icon_button(
            image,
            (rect.x, rect.y),
            (rect.width, rect.height),
            f"navigation_puck_direct_{action}",
            opacity=opacity,
        )
        self._handle_direct_menu_response(context, action, response)

    def _context_key(self, context: bpy.types.Context) -> tuple[int, int, int, int]:
        return context_key(context)

    def _context_matches(self, context: bpy.types.Context) -> bool:
        return self._context_is_supported_editor(context) and self._context_key(context) == self.context_key

    def _context_is_supported_editor(self, context: bpy.types.Context) -> bool:
        return is_supported_editor_context(context)

    def _run_in_owner_context(
        self,
        context: bpy.types.Context,
        callback: typing.Callable[[bpy.types.Context], typing.Any],
    ) -> typing.Any:
        return _run_with_context_override(context, self.context_override, callback)

    def _update_region_size(self, context: bpy.types.Context) -> None:
        if self.owner_viewport_rect != (0, 0, 1, 1):
            self.region_size[:] = (
                max(float(self.owner_viewport_rect[2]), 1.0),
                max(float(self.owner_viewport_rect[3]), 1.0),
            )
            return
        if context.region:
            self.region_size[:] = (max(float(context.region.width), 1.0), max(float(context.region.height), 1.0))

    def _event_mouse_pos(
        self,
        event: bpy.types.Event,
        fallback: mathutils.Vector,
    ) -> mathutils.Vector:
        return self._owner_local_position(self._event_region_pos(event, fallback))

    def _event_region_pos(
        self,
        event: bpy.types.Event,
        fallback: mathutils.Vector,
    ) -> mathutils.Vector:
        return event_region_position(event, fallback)

    def _debug_bounds_enabled(self, context: bpy.types.Context) -> bool:
        prefs = get_addon_preferences(context)
        return bool(getattr(prefs, "debug_shortcut_bounds", False))

    def _is_view2d_editor(self) -> bool:
        return self.editor_type in VIEW2D_EDITOR_TYPES

    def _supports_action(self, action: str) -> bool:
        return supports_puck_action(
            action,
            is_view2d_editor=self._is_view2d_editor(),
            is_camera_view=self.is_camera_view,
            is_camera_view_locked=self.is_camera_view_locked,
        )

    def _sync_preferences(self, context: bpy.types.Context) -> None:
        prefs = get_addon_preferences(context)
        self.activation_mode = get_activation_mode(context)
        if self.activation_mode == ACTIVATION_SHORTCUT_BUTTON:
            self._ensure_shortcut_icon()
        self.button_size = max(float(getattr(prefs, "shortcut_button_size", self.button_size)), 1.0)
        self.menu_button_size = get_mode_menu_button_size(prefs, self.activation_mode, self.menu_button_size)
        self.fade_zone_inset_percent = max(
            float(getattr(prefs, "shortcut_fade_start_inset_percent", self.fade_zone_inset_percent)),
            0.0,
        )
        distance = getattr(prefs, "shortcut_cursor_distance", self.cursor_distance)
        self.cursor_distance = max(float(distance), self.button_size * 0.5)
        self.cursor_position = str(getattr(prefs, "shortcut_cursor_position", self.cursor_position))
        self.cursor_offset[:] = cursor_offset(self.cursor_position, self.cursor_distance)
        self.follow_zone_radius = follow_zone_radius(
            self.cursor_offset,
            control_edge_radius(self.activation_mode, self.button_size, self.menu_button_size),
        )
        editor_type = context_editor_type(context)
        if editor_type in SUPPORTED_EDITOR_TYPES:
            self.editor_type = editor_type
        self.is_camera_view = False
        self.is_camera_view_locked = False
        if self.editor_type == 'VIEW_3D':
            rv3d = self.owner_region_data or region_view3d_for_position(context)
            if rv3d is None:
                return
            self.is_camera_view = rv3d.view_perspective == 'CAMERA'
            self.is_camera_view_locked = self.is_camera_view and bool(getattr(context.space_data, "lock_camera", False))

    def _fade_start_radius(self) -> float:
        inset = max(
            self.fade_zone_min_inset,
            self.follow_zone_radius * (self.fade_zone_inset_percent / 100.0),
        )
        edge_radius = control_edge_radius(self.activation_mode, self.button_size, self.menu_button_size)
        return max(edge_radius, self.follow_zone_radius - inset)

    def _full_visible_radius(self) -> float:
        return control_edge_radius(self.activation_mode, self.button_size, self.menu_button_size)

    def _cursor_is_on_visible_control(self) -> bool:
        if self.activation_mode == ACTIVATION_DIRECT_MENU and self._direct_menu_contains(self.mouse_pos.x, self.mouse_pos.y):
            return True
        return self._button_rect().contains(self.mouse_pos.x, self.mouse_pos.y)

    def _fade_proximity(self, distance_to_button: float, full_visible_radius: float, fade_start_radius: float) -> float:
        if self._cursor_is_on_visible_control():
            return 1.0
        if distance_to_button <= full_visible_radius:
            return 1.0
        if distance_to_button >= fade_start_radius:
            return 0.0

        fade_span = max(fade_start_radius - full_visible_radius, 1.0)
        return 1.0 - ((distance_to_button - full_visible_radius) / fade_span)

    def _set_target_opacity(self, opacity: float) -> None:
        self.target_opacity = opacity
        self.opacity = self.target_opacity

    def _menu_is_running(self) -> bool:
        return NavigationPuckWidgetOperator.app.is_running

    def _update_button_position(self) -> None:
        if self._cursor_in_follow_zone():
            return
        self._place_button_from_cursor()

    def _place_button_from_cursor(self) -> None:
        self.button_center[:] = self.mouse_pos + self.cursor_offset
        self._clamp_button_center()

    def _clamp_button_center(self) -> None:
        if self.activation_mode == ACTIVATION_DIRECT_MENU:
            half_size = self.menu_button_size + 6.0
        else:
            half_size = self.button_size * 0.5
        self.button_center[:] = clamp_center(self.button_center, self.region_size, self.margin, half_size)

    def _update_target_opacity(self, previous_mouse_pos: mathutils.Vector | None = None) -> None:
        if not self._cursor_in_follow_zone():
            self._set_target_opacity(self.idle_opacity)
            return

        distance_to_button = (self.mouse_pos - self.button_center).length
        proximity = self._fade_proximity(
            distance_to_button,
            self._full_visible_radius(),
            self._fade_start_radius(),
        )
        self._set_target_opacity(max(self.idle_opacity, proximity))


class NavigationPuckWidgetOperator(bpy.types.Operator):
    """Show the Navigation Puck viewport overlay."""
    bl_idname = "navigation_puck.widget"
    bl_label = "Navigation Puck"
    bl_options = {'REGISTER'}

    follow_mouse: bpy.props.BoolProperty(default=False) # type: ignore
    drag_select: bpy.props.BoolProperty(default=False) # type: ignore
    dismiss_on_key_release: bpy.props.BoolProperty(default=False) # type: ignore
    dismiss_key_type: bpy.props.StringProperty(default="") # type: ignore
    anchor_x: bpy.props.FloatProperty(default=-1.0) # type: ignore
    anchor_y: bpy.props.FloatProperty(default=-1.0) # type: ignore

    app = NavigationPuckWidget()

    # Override Operator method
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """
        Start the modal operator and initialize widget

        Called once when the operator is invoked
        """
        anchor = None
        if self.anchor_x >= 0.0 and self.anchor_y >= 0.0:
            anchor = mathutils.Vector((self.anchor_x, self.anchor_y))

        if self.app.is_running:
            return self.app.reopen(
                context,
                event,
                self.follow_mouse,
                self.drag_select,
                anchor,
                self.dismiss_on_key_release,
                self.dismiss_key_type,
            )

        if not add_modal_handler(context, self):
            return OperatorReturn.CANCELLED

        return self.app.invoke(
            context,
            event,
            self.follow_mouse,
            self.drag_select,
            anchor,
            self.dismiss_on_key_release,
            self.dismiss_key_type,
        )

    # Override Operator method
    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """
        Handle widget events

        Called on any mouse move or click event, as well as every frame
        """

        return self.app.event_handler(context, event)


class NavigationPuckHotkeyOperator(bpy.types.Operator):
    """Open the Navigation Puck from a keymap item."""
    bl_idname = "navigation_puck.hotkey"
    bl_label = "Navigation Puck Hotkey"
    bl_options = {'INTERNAL'}

    @staticmethod
    def _modifier_event_should_pass_through(event: bpy.types.Event) -> bool:
        if event.type not in MODIFIER_KEY_STATE_ATTRS:
            return False
        return any(app.is_running for app in NavigationPuckShortcutOperator.apps.values())

    @staticmethod
    def _operator_result_for_event(result: OperatorReturnType, event: bpy.types.Event) -> OperatorReturnType:
        if 'CANCELLED' in result:
            return OperatorReturn.CANCELLED

        if event.type in MODIFIER_KEY_STATE_ATTRS:
            return OperatorReturn.PASS_THROUGH

        return OperatorReturn.FINISHED

    def _invoke_in_editor_context(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        *,
        require_event_in_context: bool = True,
    ) -> OperatorReturnType:
        if not is_supported_editor_context(context):
            return OperatorReturn.CANCELLED

        if require_event_in_context and not event_window_position_is_in_context_area(context, event):
            return OperatorReturn.CANCELLED

        if self._modifier_event_should_pass_through(event):
            return OperatorReturn.PASS_THROUGH

        anchor = event_position_in_context(context, event, mathutils.Vector((-1.0, -1.0)))
        context_override = make_context_override(context, anchor)
        try:
            result = _invoke_navigation_puck_widget(
                context,
                anchor,
                drag_select=False,
                dismiss_on_key_release=True,
                dismiss_key_type=event.type,
                context_override=context_override,
            )
        except RuntimeError as ex:
            print(f"Navigation Puck hotkey failed to open menu: {ex}")
            return OperatorReturn.CANCELLED

        return self._operator_result_for_event(result, event)

    def _invoke_first_supported_editor_context(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType:
        for override in find_supported_editor_overrides(context.window_manager):
            try:
                with context.temp_override(**override):
                    result = self._invoke_in_editor_context(
                        bpy.context,
                        event,
                        require_event_in_context=False,
                    )
                    if 'CANCELLED' not in result:
                        return result
            except (ReferenceError, RuntimeError, TypeError) as ex:
                print(f"Navigation Puck hotkey failed to use fallback editor context: {ex}")

        return OperatorReturn.CANCELLED

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        target_override = editor_context_override_at_event(context, event)
        if target_override:
            try:
                with context.temp_override(**target_override):
                    result = self._invoke_in_editor_context(bpy.context, event)
                    if 'CANCELLED' not in result:
                        return result
            except (ReferenceError, RuntimeError, TypeError) as ex:
                print(f"Navigation Puck hotkey failed to use cursor editor context: {ex}")

        result = self._invoke_in_editor_context(context, event)
        if 'CANCELLED' not in result:
            return result

        return self._invoke_first_supported_editor_context(context, event)


class NavigationPuckShortcutOperator(bpy.types.Operator):
    """Run the always-available Navigation Puck viewport shortcut."""
    bl_idname = "navigation_puck.shortcut"
    bl_label = "Navigation Puck Shortcut"
    bl_options = {'INTERNAL'}

    restart_context: bpy.props.BoolProperty(default=False) # type: ignore

    apps: dict[tuple[int, int, int, int], NavigationPuckShortcut] = {}

    @classmethod
    def get_app(cls, key: tuple[int, int, int, int]) -> NavigationPuckShortcut | None:
        return cls.apps.get(key)

    @classmethod
    def has_active_pointer_interaction(
        cls,
        *,
        excluding: NavigationPuckShortcut | None = None,
    ) -> bool:
        return any(
            app is not excluding and app.is_running and app._has_active_pointer_interaction()
            for app in cls.apps.values()
        )

    @classmethod
    def ensure_app(cls, context: bpy.types.Context) -> NavigationPuckShortcut:
        key = context_key(context)
        app = cls.apps.get(key)
        if app is None:
            app = NavigationPuckShortcut()
            cls.apps[key] = app
        return app

    @classmethod
    def reveal_after_menu(
        cls,
        context: bpy.types.Context,
        key: tuple[int, int, int, int] | None,
        mouse_pos: mathutils.Vector,
    ) -> None:
        app = cls.apps.get(key) if key is not None else cls.apps.get(context_key(context))
        if app:
            app.reveal_after_menu(mouse_pos)

    @classmethod
    def shutdown_all(cls) -> None:
        for app in cls.apps.values():
            app.shutdown()
        cls.apps.clear()

    @classmethod
    def prune_missing(cls, existing_keys: set[tuple[int, int, int, int]]) -> None:
        for key, app in list(cls.apps.items()):
            if key not in existing_keys:
                app.shutdown()
                del cls.apps[key]

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        if not is_supported_editor_context(context):
            return OperatorReturn.CANCELLED

        self.app = self.ensure_app(context)

        if self.app.is_running and not self.restart_context:
            self.app.refresh_context(context)
            return OperatorReturn.CANCELLED

        if not add_modal_handler(context, self):
            return OperatorReturn.CANCELLED

        self.modal_generation = self.app.next_modal_generation()
        return self.app.invoke(context, event)

    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        if getattr(self, "modal_generation", None) != self.app.modal_generation:
            return OperatorReturn.FINISHED
        return self.app.event_handler(context, event)


refresh_activation_runtime = activation_runtime.refresh_activation_runtime


def register() -> None:
    activation_runtime.configure(NavigationPuckShortcutOperator)
    activation_runtime.refresh_activation_runtime(bpy.context)


def unregister() -> None:
    activation_runtime.shutdown()
    NavigationPuckWidgetOperator.app.shutdown()
