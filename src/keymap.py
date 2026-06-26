"""
Keymap registration for the addon.
"""

import bpy


addon_keymaps: list[tuple[bpy.types.KeyMap, bpy.types.KeyMapItem]] = []
HOTKEY_OPERATOR_ID = "navigation_puck.hotkey"
HOTKEY_KEYMAPS = (
    ("3D View", 'VIEW_3D'),
    ("Image", 'IMAGE_EDITOR'),
    ("Node Editor", 'NODE_EDITOR'),
)
DEFAULT_HOTKEY = 'V'


def register_keymaps():
    """Register keymaps for the addon."""
    if addon_keymaps:
        return

    wm = bpy.context.window_manager
    if wm is None:
        return

    kc = wm.keyconfigs.addon
    if kc is None:
        return

    for keymap_name, space_type in HOTKEY_KEYMAPS:
        km = kc.keymaps.new(name=keymap_name, space_type=space_type)
        kmi = km.keymap_items.new(HOTKEY_OPERATOR_ID, DEFAULT_HOTKEY, 'PRESS')
        addon_keymaps.append((km, kmi))


def unregister_keymaps():
    """Unregister keymaps for the addon."""
    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except (ReferenceError, RuntimeError):
            pass

    addon_keymaps.clear()
