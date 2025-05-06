"""
Keymap registration for the addon.
This module handles the registration and unregistration of keymaps for the addon.
"""

import bpy

addon_keymaps: list[tuple[bpy.types.KeyMap, bpy.types.KeyMapItem]] = []


def register_keymaps():
    """Register keymaps for the addon."""

    wm = bpy.context.window_manager
    if wm is None:
        return
    kc = wm.keyconfigs.addon

    if kc:
        # Create a new keymap for 3D View
        km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")

        # Add a new keymap item - Alt+Q to open pie menu
        # Change key and modifiers as desired
        kmi = km.keymap_items.new(
            "heavypoly.view_tools_widget",
            type="V",
            value="PRESS",
        )

        # Set the pie menu to call
        if kmi.properties is None:
            return

        # Store the keymap to remove it later
        addon_keymaps.append((km, kmi))


def unregister_keymaps():
    """Unregister keymaps for the addon."""
    # Remove all keymaps when the addon is disabled
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)

    addon_keymaps.clear()
