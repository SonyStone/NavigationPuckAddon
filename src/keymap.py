"""
Keymap registration for the addon.
This module handles the registration and unregistration of keymaps for the addon.
"""

import bpy

addon_keymaps: list[tuple[bpy.types.KeyMap, bpy.types.KeyMapItem]] = []


def register_keymaps():
    """Register keymaps for the addon."""
    # The viewport shortcut is always available, so the old "press V to summon"
    # keymap is intentionally not registered.


def unregister_keymaps():
    """Unregister keymaps for the addon."""
    # Remove all keymaps when the addon is disabled
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)

    addon_keymaps.clear()
