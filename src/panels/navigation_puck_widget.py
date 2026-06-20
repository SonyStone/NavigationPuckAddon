import math
import typing
import bpy
import mathutils


from ..utils import add_modal_handler, load_image, force_redraw
from ..operators.view_operations import ViewPan, ViewOrbit, ViewZoom, ViewRoll, View2DPan, View2DZoom
from ..imgui.ui import UI
from ..imgui.rect import Rect
from ..renderer.rect_outline_command import RectOutlineCommand
from ..renderer.circle_outline_command import CircleOutlineCommand
from ..utils.draw_handler import DrawHandler
from ..utils.operator_return import OperatorReturn, OperatorReturnType


def get_addon_preferences(context: bpy.types.Context) -> typing.Any | None:
    """Return this add-on's preferences, if Blender has them available."""
    package_name = __package__.partition(".src")[0]
    addon = context.preferences.addons.get(package_name)
    if not addon:
        return None
    return addon.preferences


SUPPORTED_EDITOR_TYPES = {'VIEW_3D', 'IMAGE_EDITOR', 'NODE_EDITOR'}
VIEW2D_EDITOR_TYPES = {'IMAGE_EDITOR', 'NODE_EDITOR'}


def context_editor_type(context: bpy.types.Context) -> str | None:
    if context.area is None:
        return None
    return context.area.type


def context_key(context: bpy.types.Context) -> tuple[int, int, int, int]:
    return (
        context.window.as_pointer() if context.window else 0,
        context.screen.as_pointer() if context.screen else 0,
        context.area.as_pointer() if context.area else 0,
        context.region.as_pointer() if context.region else 0,
    )


def make_context_override(context: bpy.types.Context) -> dict[str, typing.Any] | None:
    if not context.window or not context.screen or not context.area or not context.region or not context.space_data:
        return None

    override: dict[str, typing.Any] = {
        "window": context.window,
        "screen": context.screen,
        "area": context.area,
        "region": context.region,
        "space_data": context.space_data,
    }
    if context.area.type == 'VIEW_3D' and getattr(context.space_data, "region_3d", None):
        override["region_data"] = context.space_data.region_3d
    return override


def is_supported_editor_context(context: bpy.types.Context) -> bool:
    return bool(
        context.area
        and context.area.type in SUPPORTED_EDITOR_TYPES
        and context.region
        and context.region.type == 'WINDOW'
    )


class NavigationPuckWidget:
    """Interactive navigation puck overlay for supported Blender editors."""

    def __init__(self) -> None:
        self.draw_handler = DrawHandler()
        self.mouse_pos = mathutils.Vector((0, 0))
        self.initial_mouse_pos = mathutils.Vector((0, 0))

        self.ui = UI()

        self.image_pan = None
        self.image_orbit = None
        self.image_zoom = None
        self.image_roll = None

        # View handlers
        self.view_pan = ViewPan()
        self.view_orbit = ViewOrbit()
        self.view_zoom = ViewZoom()
        self.view_roll = ViewRoll()
        self.view2d_pan = View2DPan()
        self.view2d_zoom = View2DZoom()
        self.editor_type: str | None = None
        self.context_key: tuple[int, int, int, int] | None = None
        self.context_override: dict[str, typing.Any] | None = None
        self.is_camera_view = False
        self.is_camera_view_locked = False

        self.is_pressed = False
        self.is_in_radius = False
        self.is_done_operation = False
        self.auto_dismiss_distance = 200.0
        self.follow_distance = 70.0

        self.button_sizes = 55
        self.initial_offset = (5, 5)
        
        self.follow_mouse = False
        self.drag_select = False
        self.drag_select_start_distance = 30.0
        self.is_running = False
        self.stop_requested = False

    def ensure_images_loaded(self) -> None:
        """Load the puck icons on demand."""
        if not self.image_pan:
            self.image_pan = load_image("pan_tool_wght300.png")
        if not self.image_orbit:
            self.image_orbit = load_image("3d_rotation_wght300.png")
        if not self.image_zoom:
            self.image_zoom = load_image("zoom_in_wght300.png")
        if not self.image_roll:
            self.image_roll = load_image("flip_camera_wght300.png")

    def _sync_preferences(self, context: bpy.types.Context) -> None:
        prefs = get_addon_preferences(context)
        self.button_sizes = max(float(getattr(prefs, "menu_button_size", self.button_sizes)), 1.0)
        self.drag_select_start_distance = max(
            float(getattr(prefs, "drag_select_threshold_radius", self.drag_select_start_distance)),
            0.0,
        )
        editor_type = context_editor_type(context)
        if editor_type in SUPPORTED_EDITOR_TYPES:
            self.editor_type = editor_type
        self.is_camera_view = False
        self.is_camera_view_locked = False
        if self.editor_type == 'VIEW_3D' and getattr(context.space_data, "region_3d", None):
            rv3d = context.space_data.region_3d
            self.is_camera_view = rv3d.view_perspective == 'CAMERA'
            self.is_camera_view_locked = self.is_camera_view and bool(getattr(context.space_data, "lock_camera", False))

    def _set_owner_context(self, context: bpy.types.Context) -> None:
        self._sync_preferences(context)
        self.context_key = context_key(context)
        self.context_override = make_context_override(context)

    def _context_matches(self, context: bpy.types.Context) -> bool:
        return self.context_key is None or context_key(context) == self.context_key

    def _run_in_owner_context(
        self,
        context: bpy.types.Context,
        callback: typing.Callable[[bpy.types.Context], typing.Any],
    ) -> typing.Any:
        if not self.context_override:
            return callback(context)

        try:
            with context.temp_override(**self.context_override):
                return callback(bpy.context)
        except (ReferenceError, RuntimeError, TypeError):
            return callback(context)

    def invoke(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        follow_mouse: bool = False,
        drag_select: bool = False,
        anchor: mathutils.Vector | None = None,
    ) -> OperatorReturnType:
        """Start the modal operator and initialize widget"""
        self.is_running = True
        self.stop_requested = False
        self.is_pressed = follow_mouse or drag_select
        self.is_in_radius = True
        self.is_done_operation = False
        self.follow_mouse = follow_mouse
        self.drag_select = drag_select
        self._set_owner_context(context)

        self.draw_handler.remove()
        self.draw_handler.add(context, self.draw_callback)

        # setup
        self.mouse_pos[:] = mathutils.Vector(
            (event.mouse_region_x, event.mouse_region_y))
        self.initial_mouse_pos[:] = anchor or self.mouse_pos
        self.ensure_images_loaded()

        force_redraw(context)

        return OperatorReturn.RUNNING_MODAL

    def reopen(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        follow_mouse: bool = False,
        drag_select: bool = False,
        anchor: mathutils.Vector | None = None,
    ) -> OperatorReturnType:
        """Move an already-running menu to the pointer instead of stacking modals."""
        self.is_pressed = follow_mouse or drag_select
        self.is_in_radius = True
        self.is_done_operation = False
        self.follow_mouse = follow_mouse
        self.drag_select = drag_select
        self._set_owner_context(context)
        self.draw_handler.remove()
        self.ui.ctx.reset_state()
        self.draw_handler.add(context, self.draw_callback)
        self.mouse_pos[:] = (event.mouse_region_x, event.mouse_region_y)
        self.initial_mouse_pos[:] = anchor or self.mouse_pos
        self.ensure_images_loaded()
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
        if reveal_shortcut:
            try:
                NavigationPuckShortcutOperator.reveal_after_menu(context, owner_key, self.mouse_pos)
            except NameError:
                pass
        self.context_key = None
        self.context_override = None
        force_redraw(context)
        return OperatorReturn.FINISHED

    def shutdown(self) -> None:
        """Clear draw state during add-on unregister."""
        self.draw_handler.remove()
        self.ui.ctx.reset_state()
        self.is_running = False
        self.stop_requested = True
        self.context_key = None
        self.context_override = None

    def _view_handlers(self) -> tuple[typing.Any, ...]:
        if self._is_view2d_editor():
            return (self.view2d_pan, self.view2d_zoom)
        return (self.view_pan, self.view_orbit, self.view_zoom, self.view_roll)

    def _is_view2d_editor(self) -> bool:
        return self.editor_type in VIEW2D_EDITOR_TYPES

    def _supports_action(self, action: str) -> bool:
        if self._is_view2d_editor():
            return action in {'pan', 'zoom'}
        if self.is_camera_view and not self.is_camera_view_locked:
            return action in {'pan', 'zoom'}
        return action in {'pan', 'orbit', 'zoom', 'roll'}

    def _pan_handler(self) -> typing.Any:
        return self.view2d_pan if self._is_view2d_editor() else self.view_pan

    def _zoom_handler(self) -> typing.Any:
        return self.view2d_zoom if self._is_view2d_editor() else self.view_zoom

    def _any_view_operation_active(self) -> bool:
        return any(handler.view_op.is_active for handler in self._view_handlers())

    def _debug_bounds_enabled(self, context: bpy.types.Context) -> bool:
        prefs = get_addon_preferences(context)
        return bool(getattr(prefs, "debug_shortcut_bounds", False))

    def _button_rects(self) -> dict[str, Rect]:
        x, y = self.initial_mouse_pos
        offset = self.initial_offset
        size = self.button_sizes
        return {
            "pan": Rect(x - size - 0.5 + offset[0], y - size - 0.5 + offset[1], size, size),
            "orbit": Rect(x + 0.5 + offset[0], y - size - 0.5 + offset[1], size, size),
            "zoom": Rect(x - size - 0.5 + offset[0], y + 0.5 + offset[1], size, size),
            "roll": Rect(x + 0.5 + offset[0], y + 0.5 + offset[1], size, size),
        }

    def _drag_delta_from_event(self, event: bpy.types.Event) -> mathutils.Vector:
        return mathutils.Vector((event.mouse_prev_x - event.mouse_x, event.mouse_prev_y - event.mouse_y))

    def _try_drag_select_action(self, context: bpy.types.Context, event: bpy.types.Event) -> bool:
        if not self.drag_select or not self.is_pressed or self.is_done_operation:
            return False

        if event.type != 'MOUSEMOVE':
            return False

        if (self.mouse_pos - self.initial_mouse_pos).length < self.drag_select_start_distance:
            return False

        delta = self._drag_delta_from_event(event)
        pointer_offset = self.mouse_pos - self.initial_mouse_pos
        rects = self._button_rects()

        if self._supports_action("pan") and rects["pan"].contains(self.mouse_pos.x, self.mouse_pos.y):
            self.is_done_operation = True
            self._run_in_owner_context(
                context,
                lambda owner_context: self._pan_handler().apply(owner_context, delta, pointer_offset),
            )
            return True

        if self._supports_action("orbit") and rects["orbit"].contains(self.mouse_pos.x, self.mouse_pos.y):
            self.is_done_operation = True
            self._run_in_owner_context(
                context,
                lambda owner_context: self.view_orbit.apply(owner_context, delta, pointer_offset, event.shift),
            )
            return True

        if self._supports_action("zoom") and rects["zoom"].contains(self.mouse_pos.x, self.mouse_pos.y):
            self.is_done_operation = True
            self._run_in_owner_context(
                context,
                lambda owner_context: self._zoom_handler().apply(owner_context, delta, pointer_offset),
            )
            return True

        if self._supports_action("roll") and rects["roll"].contains(self.mouse_pos.x, self.mouse_pos.y):
            self.is_done_operation = True
            self._run_in_owner_context(
                context,
                lambda owner_context: self.view_roll.apply(owner_context, self.mouse_pos, pointer_offset),
            )
            return True

        return False

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Handle widget events"""
        if self.stop_requested:
            return self.finish(context)

        if not self._context_matches(context):
            return OperatorReturn.PASS_THROUGH

        self._run_in_owner_context(context, self._sync_preferences)
        self.mouse_pos[:] = (event.mouse_region_x, event.mouse_region_y)

        if event.type == 'ESC':
            return self.finish(context)

        if math.dist(self.mouse_pos, self.initial_mouse_pos) > self.auto_dismiss_distance:  # type: ignore
            self.is_in_radius = False

        handled_view_event = False
        for view_handler in self._view_handlers():
            handled_view_event = self._run_in_owner_context(
                context,
                lambda owner_context, handler=view_handler: handler.event_handler(owner_context, event),
            ) or handled_view_event

        if self.is_done_operation and not self._any_view_operation_active():
            return self.finish(context, reveal_shortcut=True)

        if handled_view_event:
            if self.follow_mouse:
                if self.view_pan.view_op.is_active:
                    self.initial_mouse_pos[:] = self.mouse_pos - \
                        self.view_pan.view_op.start_mouse_pos
                if self.view_orbit.view_op.is_active:
                    self.initial_mouse_pos[:] = self.mouse_pos - \
                        self.view_orbit.view_op.start_mouse_pos
                if self.view_zoom.view_op.is_active:
                    self.initial_mouse_pos[:] = self.mouse_pos - \
                        self.view_zoom.view_op.start_mouse_pos
                if self.view_roll.view_op.is_active:
                    self.initial_mouse_pos[:] = self.mouse_pos - \
                        self.view_roll.view_op.start_mouse_pos
            self.is_done_operation = True
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        if self.drag_select and event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.is_pressed = False
            return self.finish(context, reveal_shortcut=True)

        if self._try_drag_select_action(context, event):
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        if self.follow_mouse and self.is_pressed:
            # Move initial_mouse_pos closer to current mouse pos
            if math.dist(self.mouse_pos, self.initial_mouse_pos) > self.follow_distance:  # type: ignore
                direction = (self.mouse_pos -
                             self.initial_mouse_pos).normalized()
                self.initial_mouse_pos += direction * \
                    (math.dist(self.mouse_pos, self.initial_mouse_pos) -  # type: ignore
                        self.follow_distance)

        if not self.is_pressed and not self.is_in_radius:
            # self.draw_handler.remove()
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        if self.is_done_operation and not self.is_pressed:
            return self.finish(context, reveal_shortcut=True)
        


        if self.ui.ctx.handle_event(event):
            # Event was consumed by the widget, redraw
            force_redraw(context)
            return OperatorReturn.RUNNING_MODAL

        force_redraw(context)
        return OperatorReturn.RUNNING_MODAL

    def draw_callback(self, _op: typing.Any, context: bpy.types.Context):
        """
        Draw shaders UI for viewport overlay

        registered with a DrawHandler(), called after each `force_redraw` call
        """

        if self._any_view_operation_active():
            self.ui.ctx.reset_state()
            return

        self._sync_preferences(context)
        self.ui.begin_frame(self.mouse_pos)

        rects = self._button_rects()

        if not self.image_pan or not self.image_orbit or not self.image_zoom or not self.image_roll:
            return

        if self._supports_action("pan"):
            response = self.ui.icon_button(
                self.image_pan,
                (rects["pan"].x, rects["pan"].y),
                (rects["pan"].width, rects["pan"].height)
            )
            if response.clicked or response.dragged:
                self.is_done_operation = True
                self._run_in_owner_context(
                    context,
                    lambda owner_context: self._pan_handler().apply(
                        owner_context,
                        response.drag_delta,
                        self.mouse_pos - self.initial_mouse_pos,
                    ),
                )
                if self.follow_mouse:
                    self.initial_mouse_pos[:] = self.mouse_pos - \
                        self._pan_handler().view_op.start_mouse_pos

        if self._supports_action("orbit"):
            response = self.ui.icon_button(
                self.image_orbit,
                (rects["orbit"].x, rects["orbit"].y),
                (rects["orbit"].width, rects["orbit"].height))
            if response.clicked or response.dragged:
                self.is_done_operation = True
                self._run_in_owner_context(
                    context,
                    lambda owner_context: self.view_orbit.apply(
                        owner_context,
                        response.drag_delta,
                        self.mouse_pos - self.initial_mouse_pos,
                        response.shift,
                    ),
                )
                if self.follow_mouse:
                    self.initial_mouse_pos[:] = self.mouse_pos - \
                        self.view_orbit.view_op.start_mouse_pos

        if self._supports_action("zoom"):
            response = self.ui.icon_button(
                self.image_zoom,
                (rects["zoom"].x, rects["zoom"].y),
                (rects["zoom"].width, rects["zoom"].height)
            )
            if response.clicked or response.dragged:
                self.is_done_operation = True
                self._run_in_owner_context(
                    context,
                    lambda owner_context: self._zoom_handler().apply(
                        owner_context,
                        response.drag_delta,
                        self.mouse_pos - self.initial_mouse_pos,
                    ),
                )
                if self.follow_mouse:
                    self.initial_mouse_pos[:] = self.mouse_pos - \
                        self._zoom_handler().view_op.start_mouse_pos

        if self._supports_action("roll"):
            response = self.ui.icon_button(
                self.image_roll,
                (rects["roll"].x, rects["roll"].y),
                (rects["roll"].width, rects["roll"].height)
            )
            if response.clicked or response.dragged:
                self.is_done_operation = True
                self._run_in_owner_context(
                    context,
                    lambda owner_context: self.view_roll.apply(
                        owner_context,
                        self.mouse_pos,
                        self.mouse_pos - self.initial_mouse_pos,
                    ),
                )
                if self.follow_mouse:
                    self.initial_mouse_pos[:] = self.mouse_pos - \
                        self.view_roll.view_op.start_mouse_pos

        if self.drag_select and self._debug_bounds_enabled(context):
            self.ui.renderer.add(CircleOutlineCommand(
                center=(self.initial_mouse_pos.x, self.initial_mouse_pos.y),
                radius=self.drag_select_start_distance,
                color=(0.0, 0.9, 1.0, 0.95),
                width=2.0,
            ))

        self.ui.end_frame()


class NavigationPuckShortcut:
    """Always-on viewport shortcut that summons the navigation puck."""

    def __init__(self) -> None:
        self.draw_handler = DrawHandler()
        self.ui = UI()
        self.mouse_pos = mathutils.Vector((0.0, 0.0))
        self.last_mouse_pos = mathutils.Vector((0.0, 0.0))
        self.button_center = mathutils.Vector((42.0, 42.0))
        self.region_size = mathutils.Vector((1.0, 1.0))
        self.icon = None
        self.opacity = 0.0
        self.target_opacity = 0.0
        self.is_running = False
        self.stop_requested = False
        self.press_started_on_button = False
        self.context_key: tuple[int, int, int, int] | None = None
        self.context_override: dict[str, typing.Any] | None = None
        self.modal_generation = 0

        self.button_size = 45.0
        self.margin = 14.0
        self.cursor_distance = 80.0
        self.follow_zone_radius = self._calculate_follow_zone_radius(self.cursor_distance)
        self.cursor_offset = mathutils.Vector((-self.cursor_distance, -self.cursor_distance))
        self.idle_opacity = 0.0
        self.click_opacity_threshold = 0.12
        self.fade_zone_min_inset = 10.0
        self.fade_zone_inset_percent = 40.0

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Start the shortcut modal overlay."""
        self.is_running = True
        self.stop_requested = False
        self.icon = load_image("explore_wght300.png")
        self.context_key = self._context_key(context)
        self.context_override = make_context_override(context)
        self._sync_preferences(context)
        self._update_region_size(context)
        self.mouse_pos[:] = self._event_mouse_pos(event, self.button_center)
        self.last_mouse_pos[:] = self.mouse_pos
        self._place_button_from_cursor()
        self._update_target_opacity()
        self.draw_handler.remove()
        self.ui.ctx.reset_state()
        self.draw_handler.add(context, self.draw_callback)
        force_redraw(context)
        return OperatorReturn.RUNNING_MODAL

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

    def finish(self, context: bpy.types.Context) -> OperatorReturnType:
        """End the shortcut operator and clear draw/timer resources."""
        self.draw_handler.remove()
        self.ui.ctx.reset_state()
        self.is_running = False
        self.context_key = None
        self.context_override = None
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
            self.context_override = make_context_override(context)
            self.draw_handler.remove()
            self.draw_handler.add(context, self.draw_callback)
        elif self.context_override is None:
            self.context_override = make_context_override(context)

        self._sync_preferences(context)
        self._update_region_size(context)
        self._clamp_button_center()
        force_redraw(context)

    def reveal_after_menu(self, mouse_pos: mathutils.Vector) -> None:
        """Show the shortcut near the cursor after a puck action finishes."""
        self.mouse_pos[:] = mouse_pos
        self.button_center[:] = mouse_pos
        self._clamp_button_center()
        self.target_opacity = 1.0
        self.opacity = 1.0
        self.press_started_on_button = False

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Handle mouse movement/clicks while passing normal viewport input through."""
        if self.stop_requested:
            return self.finish(context)

        if not self._context_matches(context):
            return OperatorReturn.PASS_THROUGH

        self._sync_preferences(context)
        self._update_region_size(context)

        if self._menu_is_running():
            if hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y"):
                self.mouse_pos[:] = self._event_mouse_pos(event, self.mouse_pos)
            self.press_started_on_button = False
            self.target_opacity = 0.0
            self.opacity = 0.0
            force_redraw(context)
            return OperatorReturn.PASS_THROUGH

        has_mouse_position = hasattr(event, "mouse_region_x") and hasattr(event, "mouse_region_y")
        if not has_mouse_position:
            return OperatorReturn.PASS_THROUGH

        previous_mouse_pos = self.mouse_pos.copy()
        self.mouse_pos[:] = self._event_mouse_pos(event, self.mouse_pos)

        if event.type == 'MOUSEMOVE':
            self._update_button_position()
            self._update_target_opacity(previous_mouse_pos)
            force_redraw(context)
            return OperatorReturn.PASS_THROUGH

        if event.type == 'LEFTMOUSE':
            is_over_button = self._is_clickable() and self._button_rect().contains(
                event.mouse_region_x,
                event.mouse_region_y,
            )

            if event.value == 'PRESS' and is_over_button:
                self.press_started_on_button = True
                self.ui.ctx.handle_event(event)
                self._open_puck_menu(context)
                self.press_started_on_button = False
                self.target_opacity = 0.0
                self.opacity = 0.0
                force_redraw(context)
                return OperatorReturn.RUNNING_MODAL

            if event.value == 'RELEASE' and self.press_started_on_button:
                self.press_started_on_button = False
                self.ui.ctx.handle_event(event)
                force_redraw(context)
                return OperatorReturn.RUNNING_MODAL

        return OperatorReturn.PASS_THROUGH

    def draw_callback(self, _op: typing.Any, context: bpy.types.Context):
        """Draw the shortcut icon and its debug zones."""
        if self._menu_is_running():
            return

        self._sync_preferences(context)
        debug_bounds = self._debug_bounds_enabled(context)
        draw_opacity = max(self.opacity, 0.65) if debug_bounds else self.opacity

        if draw_opacity <= 0.01:
            return

        self.ui.begin_frame(self.mouse_pos)

        button_rect = self._button_rect()

        if self.icon:
            response = self.ui.icon_button(
                self.icon,
                (button_rect.x, button_rect.y),
                (self.button_size, self.button_size),
                "navigation_puck_shortcut",
                opacity=draw_opacity,
            )
        else:
            response = self.ui.button(
                None,
                (button_rect.x, button_rect.y),
                (self.button_size, self.button_size),
                "navigation_puck_shortcut",
                opacity=draw_opacity,
            )
        if debug_bounds:
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
        if response.hovered:
            self.target_opacity = 1.0
            self.opacity = 1.0

        self.ui.end_frame()

    def _open_puck_menu(self, context: bpy.types.Context) -> None:
        try:
            if self.context_override:
                with context.temp_override(**self.context_override):
                    bpy.ops.navigation_puck.widget(
                        'INVOKE_DEFAULT',
                        follow_mouse=False,
                        drag_select=True,
                        anchor_x=self.button_center.x,
                        anchor_y=self.button_center.y,
                    )
            else:
                bpy.ops.navigation_puck.widget(
                    'INVOKE_DEFAULT',
                    follow_mouse=False,
                    drag_select=True,
                    anchor_x=self.button_center.x,
                    anchor_y=self.button_center.y,
                )
        except RuntimeError as ex:
            print(f"Navigation Puck shortcut failed to open menu: {ex}")

    def _is_clickable(self) -> bool:
        return self.opacity >= self.click_opacity_threshold

    def _button_rect(self) -> Rect:
        half_size = self.button_size * 0.5
        return Rect(
            self.button_center.x - half_size,
            self.button_center.y - half_size,
            self.button_size,
            self.button_size,
        )

    def _cursor_in_follow_zone(self) -> bool:
        return (self.mouse_pos - self.button_center).length <= self.follow_zone_radius

    def _context_key(self, context: bpy.types.Context) -> tuple[int, int, int, int]:
        return context_key(context)

    def _context_matches(self, context: bpy.types.Context) -> bool:
        return self._context_is_supported_editor(context) and self._context_key(context) == self.context_key

    def _context_is_supported_editor(self, context: bpy.types.Context) -> bool:
        return is_supported_editor_context(context)

    def _update_region_size(self, context: bpy.types.Context) -> None:
        if context.region:
            self.region_size[:] = (max(float(context.region.width), 1.0), max(float(context.region.height), 1.0))

    def _event_mouse_pos(
        self,
        event: bpy.types.Event,
        fallback: mathutils.Vector,
    ) -> mathutils.Vector:
        x = getattr(event, "mouse_region_x", fallback.x)
        y = getattr(event, "mouse_region_y", fallback.y)
        return mathutils.Vector((x, y))

    def _debug_bounds_enabled(self, context: bpy.types.Context) -> bool:
        prefs = get_addon_preferences(context)
        return bool(getattr(prefs, "debug_shortcut_bounds", False))

    def _sync_preferences(self, context: bpy.types.Context) -> None:
        prefs = get_addon_preferences(context)
        self.button_size = max(float(getattr(prefs, "shortcut_button_size", self.button_size)), 1.0)
        self.fade_zone_inset_percent = max(
            float(getattr(prefs, "shortcut_fade_start_inset_percent", self.fade_zone_inset_percent)),
            0.0,
        )
        distance = getattr(prefs, "shortcut_cursor_distance", self.cursor_distance)
        self.cursor_distance = max(float(distance), self.button_size * 0.5)
        self.follow_zone_radius = self._calculate_follow_zone_radius(self.cursor_distance)
        self.cursor_offset[:] = (-self.cursor_distance, -self.cursor_distance)

    def _calculate_follow_zone_radius(self, cursor_distance: float) -> float:
        diagonal_distance = cursor_distance * math.sqrt(2.0)
        return max(self.button_size, diagonal_distance + self.button_size * 0.5)

    def _fade_start_radius(self) -> float:
        inset = max(
            self.fade_zone_min_inset,
            self.follow_zone_radius * (self.fade_zone_inset_percent / 100.0),
        )
        return max(self.button_size * 0.5, self.follow_zone_radius - inset)

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
        half_size = self.button_size * 0.5
        min_x = self.margin + half_size
        min_y = self.margin + half_size
        max_x = max(min_x, self.region_size.x - self.margin - half_size)
        max_y = max(min_y, self.region_size.y - self.margin - half_size)
        self.button_center.x = min(max(self.button_center.x, min_x), max_x)
        self.button_center.y = min(max(self.button_center.y, min_y), max_y)

    def _update_target_opacity(self, previous_mouse_pos: mathutils.Vector | None = None) -> None:
        if not self._cursor_in_follow_zone():
            self.target_opacity = self.idle_opacity
            self.opacity = self.target_opacity
            return

        distance_to_button = (self.mouse_pos - self.button_center).length
        fade_start_radius = self._fade_start_radius()
        full_visible_radius = self.button_size * 0.5
        if self._button_rect().contains(self.mouse_pos.x, self.mouse_pos.y):
            proximity = 1.0
        elif distance_to_button <= full_visible_radius:
            proximity = 1.0
        elif distance_to_button >= fade_start_radius:
            proximity = 0.0
        else:
            fade_span = max(fade_start_radius - full_visible_radius, 1.0)
            proximity = 1.0 - ((distance_to_button - full_visible_radius) / fade_span)
        self.target_opacity = max(self.idle_opacity, proximity)
        self.opacity = self.target_opacity


class NavigationPuckWidgetOperator(bpy.types.Operator):
    """Show the Navigation Puck viewport overlay."""
    bl_idname = "navigation_puck.widget"
    bl_label = "Navigation Puck"
    bl_options = {'REGISTER'}

    follow_mouse: bpy.props.BoolProperty(default=False) # type: ignore
    drag_select: bpy.props.BoolProperty(default=False) # type: ignore
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
            return self.app.reopen(context, event, self.follow_mouse, self.drag_select, anchor)

        if not add_modal_handler(context, self):
            return OperatorReturn.CANCELLED

        return self.app.invoke(context, event, self.follow_mouse, self.drag_select, anchor)

    # Override Operator method
    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """
        Handle widget events

        Called on any mouse move or click event, as well as every frame
        """

        return self.app.event_handler(context, event)


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


_shortcut_autostart_enabled = False


def _editor_context_key(override: dict[str, typing.Any]) -> tuple[int, int, int, int]:
    return (
        override["window"].as_pointer(),
        override["screen"].as_pointer(),
        override["area"].as_pointer(),
        override["region"].as_pointer(),
    )


def _find_supported_editor_overrides() -> list[dict[str, typing.Any]]:
    wm = bpy.context.window_manager
    if not wm:
        return []

    overrides: list[dict[str, typing.Any]] = []
    for window in wm.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type not in SUPPORTED_EDITOR_TYPES:
                continue
            space = area.spaces.active
            if space.type not in SUPPORTED_EDITOR_TYPES:
                continue
            for region in area.regions:
                if region.type == 'WINDOW':
                    override = {
                        "window": window,
                        "screen": screen,
                        "area": area,
                        "region": region,
                        "space_data": space,
                    }
                    if area.type == 'VIEW_3D':
                        override["region_data"] = space.region_3d
                    overrides.append(override)
                    break
    return overrides


def _start_shortcut_operator() -> float | None:
    if not _shortcut_autostart_enabled:
        return None

    overrides = _find_supported_editor_overrides()
    if not overrides:
        NavigationPuckShortcutOperator.shutdown_all()
        return 0.5

    existing_keys = {_editor_context_key(override) for override in overrides}
    NavigationPuckShortcutOperator.prune_missing(existing_keys)

    for override in overrides:
        key = _editor_context_key(override)
        app = NavigationPuckShortcutOperator.get_app(key)
        if app and app.is_running:
            with bpy.context.temp_override(**override):
                app.refresh_context(bpy.context)
            continue

        try:
            with bpy.context.temp_override(**override):
                bpy.ops.navigation_puck.shortcut('INVOKE_DEFAULT')
        except RuntimeError as ex:
            print(f"Navigation Puck shortcut autostart failed: {ex}")

    return 0.5


def register() -> None:
    global _shortcut_autostart_enabled
    _shortcut_autostart_enabled = True
    if not bpy.app.timers.is_registered(_start_shortcut_operator):
        bpy.app.timers.register(_start_shortcut_operator, first_interval=0.25)


def unregister() -> None:
    global _shortcut_autostart_enabled
    _shortcut_autostart_enabled = False
    NavigationPuckWidgetOperator.app.shutdown()
    NavigationPuckShortcutOperator.shutdown_all()
    if bpy.app.timers.is_registered(_start_shortcut_operator):
        bpy.app.timers.unregister(_start_shortcut_operator)
