"""
Preferences for the Navigation Puck addon.
This module defines the addon preferences, including keybinding customization.
"""

import bpy
import rna_keymap_ui

from .panels import CURRENT_MAIN_WIDGET

from .. import __package__ as base_package


class NavigationPuckPreferences(bpy.types.AddonPreferences):
    """Preferences for the Navigation Puck addon."""
    # The `bl_idname` must match the addon module name in `bl_info`
    bl_idname = base_package # type: ignore

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
        layout.prop(self, "debug_shortcut_bounds")
        layout.prop(self, "shortcut_cursor_distance")
        layout.prop(self, "shortcut_button_size")
        layout.prop(self, "menu_button_size")
        layout.prop(self, "drag_select_threshold_radius")
        layout.prop(self, "shortcut_fade_start_inset_percent")

        wm = context.window_manager
        if wm is None:
            return
        kc = wm.keyconfigs.user

        if kc:
            km = kc.keymaps.get("3D View")
            if km:
                for kmi in km.keymap_items:
                    if kmi.idname == CURRENT_MAIN_WIDGET.bl_idname:
                        rna_keymap_ui.draw_kmi([], kc, km, kmi, layout, 0) # type: ignore


classes = (
    NavigationPuckPreferences,
)
