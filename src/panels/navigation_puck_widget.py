import math
import typing
import bpy
import mathutils


from ..utils import add_modal_handler, load_image, force_redraw
from ..operators.view_operations import ViewPan, ViewOrbit, ViewZoom, ViewRoll
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


class NavigationPuckWidget:
    """Interactive navigation puck overlay for the 3D View."""

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
        self._sync_preferences(context)

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
        self._sync_preferences(context)
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
        self.draw_handler.remove()
        self.ui.ctx.reset_state()
        self.is_running = False
        if reveal_shortcut:
            try:
                NavigationPuckShortcutOperator.app.reveal_after_menu(self.mouse_pos)
            except NameError:
                pass
        force_redraw(context)
        return OperatorReturn.FINISHED

    def shutdown(self) -> None:
        """Clear draw state during add-on unregister."""
        self.draw_handler.remove()
        self.ui.ctx.reset_state()
        self.is_running = False
        self.stop_requested = True

    def _view_handlers(self) -> tuple[ViewPan, ViewOrbit, ViewZoom, ViewRoll]:
        return (
            self.view_pan,
            self.view_orbit,
            self.view_zoom,
            self.view_roll,
        )

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

        if rects["pan"].contains(self.mouse_pos.x, self.mouse_pos.y):
            self.is_done_operation = True
            self.view_pan.apply(context, delta, pointer_offset)
            return True

        if rects["orbit"].contains(self.mouse_pos.x, self.mouse_pos.y):
            self.is_done_operation = True
            self.view_orbit.apply(context, delta, pointer_offset, event.shift)
            return True

        if rects["zoom"].contains(self.mouse_pos.x, self.mouse_pos.y):
            self.is_done_operation = True
            self.view_zoom.apply(context, delta, pointer_offset)
            return True

        if rects["roll"].contains(self.mouse_pos.x, self.mouse_pos.y):
            self.is_done_operation = True
            self.view_roll.apply(context, self.mouse_pos, pointer_offset)
            return True

        return False

    def event_handler(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """Handle widget events"""
        if self.stop_requested:
            return self.finish(context)

        self._sync_preferences(context)
        self.mouse_pos[:] = (event.mouse_region_x, event.mouse_region_y)

        if event.type == 'ESC':
            return self.finish(context)

        if math.dist(self.mouse_pos, self.initial_mouse_pos) > self.auto_dismiss_distance:  # type: ignore
            self.is_in_radius = False

        handled_view_event = False
        for view_handler in self._view_handlers():
            handled_view_event = view_handler.event_handler(context, event) or handled_view_event

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

        if self.view_pan.view_op.is_active or \
           self.view_orbit.view_op.is_active or \
           self.view_zoom.view_op.is_active or \
           self.view_roll.view_op.is_active:
            self.ui.ctx.reset_state()
            return

        self._sync_preferences(context)
        self.ui.begin_frame(self.mouse_pos)

        rects = self._button_rects()

        if not self.image_pan or not self.image_orbit or not self.image_zoom or not self.image_roll:
            return

        response = self.ui.icon_button(
            self.image_pan,
            # "Pan",
            (rects["pan"].x, rects["pan"].y),
            (rects["pan"].width, rects["pan"].height)
        )
        if response.clicked or response.dragged:
            self.is_done_operation = True
            self.view_pan.apply(
                context, response.drag_delta, self.mouse_pos - self.initial_mouse_pos)
            if self.follow_mouse:
                self.initial_mouse_pos[:] = self.mouse_pos - \
                    self.view_pan.view_op.start_mouse_pos

        response = self.ui.icon_button(
            self.image_orbit,
            # "Rotate",
            (rects["orbit"].x, rects["orbit"].y),
            (rects["orbit"].width, rects["orbit"].height))
        if response.clicked or response.dragged:
            self.is_done_operation = True
            self.view_orbit.apply(context, response.drag_delta,
                                  self.mouse_pos - self.initial_mouse_pos, response.shift)
            if self.follow_mouse:
                self.initial_mouse_pos[:] = self.mouse_pos - \
                    self.view_orbit.view_op.start_mouse_pos

        response = self.ui.icon_button(
            self.image_zoom,
            # "Zoom",
            (rects["zoom"].x, rects["zoom"].y),
            (rects["zoom"].width, rects["zoom"].height)
        )
        if response.clicked or response.dragged:
            self.is_done_operation = True
            self.view_zoom.apply(context, response.drag_delta,
                                 self.mouse_pos - self.initial_mouse_pos)
            if self.follow_mouse:
                self.initial_mouse_pos[:] = self.mouse_pos - \
                    self.view_zoom.view_op.start_mouse_pos

        response = self.ui.icon_button(
            self.image_roll,
            # "Roll",
            (rects["roll"].x, rects["roll"].y),
            (rects["roll"].width, rects["roll"].height)
        )
        if response.clicked or response.dragged:
            self.is_done_operation = True
            self.view_roll.apply(context, self.mouse_pos,
                                 self.mouse_pos - self.initial_mouse_pos)
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
        self._sync_preferences(context)
        self._update_region_size(context)
        self.mouse_pos[:] = self._event_mouse_pos(event, self.button_center)
        self.last_mouse_pos[:] = self.mouse_pos
        self._place_button_from_cursor()
        self._update_target_opacity()
        self.draw_handler.add(context, self.draw_callback)
        force_redraw(context)
        return OperatorReturn.RUNNING_MODAL

    def shutdown(self) -> None:
        """Request a clean modal shutdown from add-on unregister."""
        self.stop_requested = True
        self.draw_handler.remove()
        self.ui.ctx.reset_state()

    def finish(self, context: bpy.types.Context) -> OperatorReturnType:
        """End the shortcut operator and clear draw/timer resources."""
        self.draw_handler.remove()
        self.ui.ctx.reset_state()
        self.is_running = False
        self.press_started_on_button = False
        force_redraw(context)
        return OperatorReturn.FINISHED

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

    app = NavigationPuckShortcut()

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        if self.app.is_running:
            return OperatorReturn.CANCELLED

        if not add_modal_handler(context, self):
            return OperatorReturn.CANCELLED

        return self.app.invoke(context, event)

    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        return self.app.event_handler(context, event)


_shortcut_autostart_enabled = False


def _find_view3d_window_override() -> dict[str, typing.Any] | None:
    wm = bpy.context.window_manager
    if not wm:
        return None

    for window in wm.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for region in area.regions:
                if region.type == 'WINDOW':
                    return {
                        "window": window,
                        "screen": screen,
                        "area": area,
                        "region": region,
                    }
    return None


def _start_shortcut_operator() -> float | None:
    if not _shortcut_autostart_enabled:
        return None

    if NavigationPuckShortcutOperator.app.is_running:
        return None

    override = _find_view3d_window_override()
    if not override:
        return 1.0

    try:
        with bpy.context.temp_override(**override):
            bpy.ops.navigation_puck.shortcut('INVOKE_DEFAULT')
    except RuntimeError as ex:
        print(f"Navigation Puck shortcut autostart failed: {ex}")
        return 1.0

    return None


def register() -> None:
    global _shortcut_autostart_enabled
    _shortcut_autostart_enabled = True
    if not bpy.app.timers.is_registered(_start_shortcut_operator):
        bpy.app.timers.register(_start_shortcut_operator, first_interval=0.25)


def unregister() -> None:
    global _shortcut_autostart_enabled
    _shortcut_autostart_enabled = False
    NavigationPuckWidgetOperator.app.shutdown()
    NavigationPuckShortcutOperator.app.shutdown()
    if bpy.app.timers.is_registered(_start_shortcut_operator):
        bpy.app.timers.unregister(_start_shortcut_operator)
