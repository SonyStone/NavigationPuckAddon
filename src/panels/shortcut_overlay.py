import typing

import bpy
import mathutils

from ..imgui.ui import UI
from ..operators.view_operations import ViewOperationSet
from ..utils.draw_handler import DrawHandler, force_redraw
from ..utils.operator_return import OperatorReturn, OperatorReturnType
from ..utils.scale import interface_scale
from ..activation import (
    ACTIVATION_DIRECT_MENU,
    ACTIVATION_HOTKEY_MENU,
    ACTIVATION_SHORTCUT_BUTTON,
    DEFAULT_ACTIVATION_MODE,
    get_activation_mode,
    get_addon_preferences,
    get_mode_menu_button_size,
)
from .editor_context import (
    RegionLocalEvent,
    context_key,
    event_position_in_context,
    event_region_position,
    event_window_position_is_in_context_area,
)
from .shortcut_layout import (
    control_edge_radius,
    cursor_offset,
    follow_zone_radius,
)
from .editor_state import EditorState
from .puck_assets import load_action_images, load_shortcut_icon
from .owner_context import OwnerContext
from .puck_invocation import _invoke_navigation_puck_widget
from .shortcut_button import ShortcutButton
from .shortcut_direct_menu import ShortcutDirectMenu
from .shortcut_hotkey import ShortcutHotkey
from .shortcut_placement import ShortcutPlacement


DEFAULT_SHORTCUT_BUTTON_SIZE = 45.0
DEFAULT_MENU_BUTTON_SIZE = 55.0
DEFAULT_SHORTCUT_MARGIN = 14.0
DEFAULT_MENU_GAP = 5.0
DEFAULT_SHORTCUT_CURSOR_DISTANCE = 80.0
DEFAULT_FADE_ZONE_MIN_INSET = 10.0


class NavigationPuckShortcut:
    """Viewport shortcut button that opens the navigation puck."""

    def __init__(self) -> None:
        self._init_draw_state()
        self._init_owner_context_state()
        self.view_ops = ViewOperationSet()
        self._init_preference_defaults()
        self.placement = ShortcutPlacement(self)
        self.shortcut_button = ShortcutButton(self)
        self.direct_menu = ShortcutDirectMenu(self)
        self.hotkey = ShortcutHotkey(self)

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
        self.owner_context = OwnerContext()
        self.pointer_in_owner_area = True
        self.modal_generation = 0
        self.editor_state = EditorState()

    def _init_preference_defaults(self) -> None:
        self.button_size = DEFAULT_SHORTCUT_BUTTON_SIZE
        self.menu_button_size = DEFAULT_MENU_BUTTON_SIZE
        self.margin = DEFAULT_SHORTCUT_MARGIN
        self.menu_gap = DEFAULT_MENU_GAP
        self.cursor_distance = DEFAULT_SHORTCUT_CURSOR_DISTANCE
        self.cursor_position = 'BOTTOM_LEFT'
        self.activation_mode = DEFAULT_ACTIVATION_MODE
        self.cursor_offset = cursor_offset(self.cursor_position, self.cursor_distance)
        self.follow_zone_radius = follow_zone_radius(
            self.cursor_offset,
            control_edge_radius(self.activation_mode, self.button_size, self.menu_button_size),
        )
        self.idle_opacity = 0.0
        self.click_opacity_threshold = 0.12
        self.fade_zone_min_inset = DEFAULT_FADE_ZONE_MIN_INSET
        self.fade_zone_inset_percent = 40.0

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Start the shortcut modal overlay."""
        self.is_running = True
        self.stop_requested = False
        self.owner_context.context_key = self._context_key(context)
        self._sync_preferences(context)
        if self.activation_mode == ACTIVATION_SHORTCUT_BUTTON:
            self._ensure_shortcut_icon()
        self._update_region_size(context)
        raw_mouse_pos = self._event_region_pos(event, self.button_center)
        self._sync_owner_viewport(context, raw_mouse_pos)
        self.pointer_in_owner_area = event_window_position_is_in_context_area(context, event)
        self._update_region_size(context)
        self.mouse_pos[:] = self.owner_context.local_position(raw_mouse_pos)
        self.last_mouse_pos[:] = self.mouse_pos
        if self.pointer_in_owner_area:
            self.placement.place_from_cursor()
            self.placement.update_target_opacity()
        else:
            self.target_opacity = 0.0
            self.opacity = 0.0
        self.draw_handler.remove()
        self.ui.ctx.reset_state()
        self.draw_handler.add(context, self.draw_callback)
        self.owner_context.update_draw_handler(self.draw_handler, context)
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
        self.owner_context.clear()
        self.pointer_in_owner_area = True

    def finish(self, context: bpy.types.Context) -> OperatorReturnType:
        """End the shortcut operator and clear draw/timer resources."""
        self.draw_handler.remove()
        self.ui.ctx.reset_state()
        self.is_running = False
        self.owner_context.clear()
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
        if context_key != self.owner_context.context_key:
            self.owner_context.context_key = context_key
            self._sync_owner_viewport(context, self.owner_context.region_position(self.mouse_pos))
            self.draw_handler.remove()
            self.draw_handler.add(context, self.draw_callback)
        elif self.owner_context.context_override is None:
            self._sync_owner_viewport(context, self.owner_context.region_position(self.mouse_pos))

        self.owner_context.update_draw_handler(self.draw_handler, context)
        self._sync_preferences(context)
        self._update_region_size(context)
        self.placement.clamp_center()
        force_redraw(context)

    def reveal_after_menu(self, mouse_pos: mathutils.Vector) -> None:
        """Show the shortcut near the cursor after a puck action finishes."""
        self._reveal_at_cursor(mouse_pos)

    def _reveal_at_cursor(self, mouse_pos: mathutils.Vector) -> None:
        self.mouse_pos[:] = mouse_pos
        self.button_center[:] = mouse_pos
        self.placement.clamp_center()
        self.target_opacity = 1.0
        self.opacity = 1.0
        self.press_started_on_button = False
        self.ui.ctx.reset_state()

    def _sync_owner_viewport(
        self,
        context: bpy.types.Context,
        position: mathutils.Vector | None = None,
    ) -> None:
        self.owner_context.set(context, position, update_key=False)
        self._sync_preferences(context)

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
        raw_mouse_pos = event_position_in_context(context, event, self.owner_context.region_position(self.mouse_pos))
        if refresh_owner:
            self._sync_owner_viewport(context, raw_mouse_pos)
        self.mouse_pos[:] = self.owner_context.local_position(raw_mouse_pos)
        self.owner_context.update_draw_handler(self.draw_handler, context)
        return previous_mouse_pos, RegionLocalEvent(event, self.mouse_pos)

    def _has_active_pointer_interaction(self) -> bool:
        return (
            self.press_started_on_button
            or self.ui.ctx.active_id is not None
            or self.view_ops.any_active(self._is_view2d_editor())
        )

    def _another_shortcut_has_active_pointer_interaction(self) -> bool:
        try:
            from .navigation_puck_operators import NavigationPuckShortcutOperator
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

    def _activation_mode_event_result(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType | None:
        if self.activation_mode == ACTIVATION_HOTKEY_MENU:
            return self.hotkey.event_handler(context, event)

        if self.activation_mode == ACTIVATION_DIRECT_MENU:
            if (
                not self._has_active_pointer_interaction()
                and self._another_shortcut_has_active_pointer_interaction()
            ):
                return self._hide_for_sibling_interaction(context)
            return self.direct_menu.event_handler(context, event)

        if self._menu_is_running():
            return self._hide_while_menu_runs(context, event)

        return None

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
        return self.shortcut_button.event_result(context, event, previous_mouse_pos, local_event)

    def _draw_activation_mode_overlay(self, context: bpy.types.Context) -> bool:
        if self.activation_mode == ACTIVATION_HOTKEY_MENU:
            return True

        if self.activation_mode == ACTIVATION_DIRECT_MENU:
            self.direct_menu.draw(context)
            return True

        return False

    def draw_callback(self, _op: typing.Any, context: bpy.types.Context):
        """Draw the shortcut icon and its debug zones."""
        self._sync_preferences(context)
        if not self.pointer_in_owner_area and not self._has_active_pointer_interaction():
            return

        if self._draw_activation_mode_overlay(context):
            return

        self.shortcut_button.draw(context)

    def _open_puck_menu(
        self,
        context: bpy.types.Context,
        drag_select: bool = True,
        dismiss_key_type: str = "",
    ) -> None:
        dismiss_on_key_release = bool(dismiss_key_type)
        anchor = self.owner_context.region_position(self.button_center)
        try:
            _invoke_navigation_puck_widget(
                context,
                anchor,
                drag_select=drag_select,
                dismiss_on_key_release=dismiss_on_key_release,
                dismiss_key_type=dismiss_key_type,
                context_override=self.owner_context.context_override,
            )
        except RuntimeError as ex:
            print(f"Navigation Puck shortcut failed to open menu: {ex}")

    def _is_clickable(self) -> bool:
        return self.opacity >= self.click_opacity_threshold

    def _context_key(self, context: bpy.types.Context) -> tuple[int, int, int, int]:
        return context_key(context)

    def _context_matches(self, context: bpy.types.Context) -> bool:
        return self.owner_context.matches_supported_context(context)

    def _update_region_size(self, context: bpy.types.Context) -> None:
        if self.owner_context.viewport_rect != (0, 0, 1, 1):
            self.region_size[:] = (
                max(float(self.owner_context.viewport_rect[2]), 1.0),
                max(float(self.owner_context.viewport_rect[3]), 1.0),
            )
            return
        if context.region:
            self.region_size[:] = (max(float(context.region.width), 1.0), max(float(context.region.height), 1.0))

    def _event_mouse_pos(
        self,
        event: bpy.types.Event,
        fallback: mathutils.Vector,
    ) -> mathutils.Vector:
        return self.owner_context.local_position(self._event_region_pos(event, fallback))

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
        return self.editor_state.is_view2d_editor()

    def _supports_action(self, action: str) -> bool:
        return self.editor_state.supports_action(action)

    def _sync_preferences(self, context: bpy.types.Context) -> None:
        prefs = get_addon_preferences(context)
        scale = interface_scale(context)
        self.activation_mode = get_activation_mode(context)
        if self.activation_mode == ACTIVATION_SHORTCUT_BUTTON:
            self._ensure_shortcut_icon()
        self.button_size = max(
            float(getattr(prefs, "shortcut_button_size", DEFAULT_SHORTCUT_BUTTON_SIZE)) * scale,
            1.0,
        )
        self.menu_button_size = max(
            get_mode_menu_button_size(prefs, self.activation_mode, DEFAULT_MENU_BUTTON_SIZE) * scale,
            1.0,
        )
        self.margin = max(DEFAULT_SHORTCUT_MARGIN * scale, 0.0)
        self.menu_gap = max(DEFAULT_MENU_GAP * scale, 0.0)
        self.fade_zone_min_inset = max(DEFAULT_FADE_ZONE_MIN_INSET * scale, 0.0)
        self.fade_zone_inset_percent = max(
            float(getattr(prefs, "shortcut_fade_start_inset_percent", self.fade_zone_inset_percent)),
            0.0,
        )
        distance = getattr(prefs, "shortcut_cursor_distance", DEFAULT_SHORTCUT_CURSOR_DISTANCE)
        self.cursor_distance = max(float(distance) * scale, self.button_size * 0.5)
        self.cursor_position = str(getattr(prefs, "shortcut_cursor_position", self.cursor_position))
        self.cursor_offset[:] = cursor_offset(self.cursor_position, self.cursor_distance)
        self.follow_zone_radius = follow_zone_radius(
            self.cursor_offset,
            control_edge_radius(self.activation_mode, self.button_size, self.menu_button_size),
        )
        self.editor_state.update(context, self.owner_context.region_data)

    def _menu_is_running(self) -> bool:
        from .navigation_puck_operators import NavigationPuckWidgetOperator
        return NavigationPuckWidgetOperator.app.is_running
