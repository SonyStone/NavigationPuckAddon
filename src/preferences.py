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

    def draw(self, context: bpy.types.Context):
        """Draw Addon Preferences UI."""
        layout = self.layout
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
