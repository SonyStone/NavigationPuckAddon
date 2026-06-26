"""
Preferences for the Navigation Puck addon.
This module defines the addon preferences.
"""

import typing

import bpy

from .. import __package__ as base_package
from .activation import (
    ACTIVATION_DIRECT_MENU,
    ACTIVATION_HOTKEY_MENU,
    ACTIVATION_SHORTCUT_BUTTON,
    DEFAULT_ACTIVATION_MODE,
)

KEYMAP_HOTKEY_SEARCH_TEXT = "Navigation Puck Hotkey"


def _refresh_activation_mode(self: typing.Any, context: bpy.types.Context) -> None:
    try:
        from .panels import activation_runtime

        activation_runtime.refresh_activation_runtime(context, allow_blender_development=True)
    except Exception as ex:
        print(f"Navigation Puck failed to refresh activation mode: {ex}")


def _iter_preference_areas(context: bpy.types.Context | None = None) -> typing.Iterator[bpy.types.Area]:
    seen: set[int] = set()

    area = getattr(context, "area", None) if context else None
    if area and area.type == 'PREFERENCES':
        seen.add(area.as_pointer())
        yield area

    window_manager = (context.window_manager if context else bpy.context.window_manager)
    for window in window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type != 'PREFERENCES':
                continue
            area_pointer = area.as_pointer()
            if area_pointer in seen:
                continue
            seen.add(area_pointer)
            yield area


def _show_keymap_hotkey_filter(context: bpy.types.Context | None = None) -> bool:
    updated = False
    for area in _iter_preference_areas(context):
        for space in area.spaces:
            if space.type != 'PREFERENCES' or not hasattr(space, "filter_text"):
                continue
            space.filter_type = 'NAME'
            space.filter_text = KEYMAP_HOTKEY_SEARCH_TEXT
            area.tag_redraw()
            updated = True
    return updated


def _show_keymap_hotkey_filter_once() -> None:
    _show_keymap_hotkey_filter()


class NavigationPuckOpenKeymapPreferencesOperator(bpy.types.Operator):
    """Open Blender's Keymap preferences."""

    bl_idname = "navigation_puck.open_keymap_preferences"
    bl_label = "Edit Navigation Puck Hotkey"
    bl_options = {'INTERNAL'}

    def execute(self, context: bpy.types.Context):
        try:
            bpy.ops.screen.userpref_show('INVOKE_DEFAULT', section='KEYMAP')
        except RuntimeError as ex:
            self.report({'WARNING'}, f"Could not open keymap preferences: {ex}")
            return {'CANCELLED'}

        if not _show_keymap_hotkey_filter(context):
            bpy.app.timers.register(_show_keymap_hotkey_filter_once, first_interval=0.1)
        return {'FINISHED'}


class NavigationPuckPreferences(bpy.types.AddonPreferences):
    """Preferences for the Navigation Puck addon."""
    # The `bl_idname` must match the addon module name in `bl_info`
    bl_idname = base_package # type: ignore

    activation_mode: bpy.props.EnumProperty( # type: ignore
        name="Activation mode",
        description="Choose how the Navigation Puck Menu opens",
        items=(
            (ACTIVATION_SHORTCUT_BUTTON, "Shortcut Button", "Show a small shortcut button near the cursor"),
            (ACTIVATION_DIRECT_MENU, "Menu Near Cursor", "Show the Navigation Puck Menu near the cursor"),
            (ACTIVATION_HOTKEY_MENU, "Hotkey", "Open the Navigation Puck Menu from a keyboard shortcut"),
        ),
        default=DEFAULT_ACTIVATION_MODE,
        update=_refresh_activation_mode,
    )
    debug_shortcut_bounds: bpy.props.BoolProperty( # type: ignore
        name="Debug mode",
        description="Show shortcut bounds and puck drag-select debug values",
        default=False,
    )
    shortcut_cursor_distance: bpy.props.FloatProperty( # type: ignore
        name="Shortcut cursor distance",
        description="Distance in pixels from the cursor to the shortcut button center",
        default=80.0,
        min=24.0,
        max=240.0,
        subtype='PIXEL',
    )
    shortcut_cursor_position: bpy.props.EnumProperty( # type: ignore
        name="Shortcut position",
        description="Position of the shortcut button relative to the cursor",
        items=(
            ('TOP_LEFT', "Top Left", "Place the shortcut above and left of the cursor"),
            ('TOP', "Top", "Place the shortcut above the cursor"),
            ('TOP_RIGHT', "Top Right", "Place the shortcut above and right of the cursor"),
            ('LEFT', "Left", "Place the shortcut left of the cursor"),
            ('RIGHT', "Right", "Place the shortcut right of the cursor"),
            ('BOTTOM_LEFT', "Bottom Left", "Place the shortcut below and left of the cursor"),
            ('BOTTOM', "Bottom", "Place the shortcut below the cursor"),
            ('BOTTOM_RIGHT', "Bottom Right", "Place the shortcut below and right of the cursor"),
        ),
        default='BOTTOM_LEFT',
    )
    shortcut_button_size: bpy.props.FloatProperty( # type: ignore
        name="Shortcut button size",
        description="Size in pixels of the small shortcut button",
        default=45.0,
        min=18.0,
        max=96.0,
        subtype='PIXEL',
    )
    menu_button_size: bpy.props.FloatProperty( # type: ignore
        name="Menu button size",
        description="Size in pixels of each Navigation Puck Menu button",
        default=55.0,
        min=32.0,
        max=128.0,
        subtype='PIXEL',
    )
    shortcut_menu_button_size: bpy.props.FloatProperty( # type: ignore
        name="Menu button size",
        description="Size in pixels of each Navigation Puck Menu button opened from the shortcut button",
        default=55.0,
        min=32.0,
        max=128.0,
        subtype='PIXEL',
    )
    direct_menu_button_size: bpy.props.FloatProperty( # type: ignore
        name="Menu button size",
        description="Size in pixels of each Navigation Puck Menu Near Cursor button",
        default=55.0,
        min=32.0,
        max=128.0,
        subtype='PIXEL',
    )
    hotkey_menu_button_size: bpy.props.FloatProperty( # type: ignore
        name="Menu button size",
        description="Size in pixels of each Navigation Puck Menu button opened from the hotkey",
        default=55.0,
        min=32.0,
        max=128.0,
        subtype='PIXEL',
    )
    drag_select_threshold_radius: bpy.props.FloatProperty( # type: ignore
        name="Drag-select threshold radius",
        description="Radius in pixels before a held shortcut drag can activate a menu action",
        default=30.0,
        min=0.0,
        max=120.0,
        subtype='PIXEL',
    )
    shortcut_fade_start_inset_percent: bpy.props.FloatProperty( # type: ignore
        name="Fade-start inset",
        description="How much smaller the orange fade-start circle is than the shortcut follow zone",
        default=40.0,
        min=0.0,
        max=80.0,
        subtype='PERCENTAGE',
    )
    def draw(self, context: bpy.types.Context):
        """Draw Addon Preferences UI."""
        layout = self.layout
        layout.prop(self, "activation_mode")

        if self.activation_mode == ACTIVATION_DIRECT_MENU:
            self._draw_direct_menu_settings(layout)
        elif self.activation_mode == ACTIVATION_HOTKEY_MENU:
            self._draw_hotkey_settings(context, layout)
        else:
            self._draw_shortcut_button_settings(layout)

    def _draw_shortcut_button_settings(self, layout: bpy.types.UILayout) -> None:
        box = layout.box()
        box.label(text="Shortcut Button")
        box.prop(self, "shortcut_cursor_distance")
        box.prop(self, "shortcut_cursor_position")
        box.prop(self, "shortcut_button_size")
        box.prop(self, "shortcut_menu_button_size")
        box.prop(self, "drag_select_threshold_radius")
        box.prop(self, "shortcut_fade_start_inset_percent")
        box.prop(self, "debug_shortcut_bounds")

    def _draw_direct_menu_settings(self, layout: bpy.types.UILayout) -> None:
        box = layout.box()
        box.label(text="Menu Near Cursor")
        box.prop(self, "shortcut_cursor_distance", text="Menu cursor distance")
        box.prop(self, "shortcut_cursor_position", text="Menu position")
        box.prop(self, "direct_menu_button_size")
        box.prop(self, "debug_shortcut_bounds")

    def _draw_hotkey_settings(self, context: bpy.types.Context, layout: bpy.types.UILayout) -> None:
        box = layout.box()
        box.label(text="Hotkey")
        box.prop(self, "hotkey_menu_button_size")
        box.operator(NavigationPuckOpenKeymapPreferencesOperator.bl_idname)


classes = (
    NavigationPuckOpenKeymapPreferencesOperator,
    NavigationPuckPreferences,
)
