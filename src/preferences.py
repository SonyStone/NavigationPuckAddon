"""
Preferences for the Navigation Puck addon.
This module defines the addon preferences, including keybinding customization.
"""

import bpy
import rna_keymap_ui

from .. import __package__ as base_package # type: ignore
from .panels.view_tools_widget import NavigationPuckViewToolsWidget


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
                    if kmi.idname == NavigationPuckViewToolsWidget.bl_idname:
                        rna_keymap_ui.draw_kmi([], kc, km, kmi, layout, 0) # type: ignore


classes = (
    NavigationPuckPreferences,
)


def register():
    """Register classes."""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister classes."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
