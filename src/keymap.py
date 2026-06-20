"""
Keymap registration for the addon.
This module handles hotkey settings and registration for the addon.
"""

import bpy

from .panels import navigation_puck_widget


addon_keymaps: list[tuple[bpy.types.KeyMap, bpy.types.KeyMapItem]] = []
DEFAULT_HOTKEY = 'LEFT_ALT'
HOTKEY_OPERATOR_ID = navigation_puck_widget.NavigationPuckHotkeyOperator.bl_idname
HOTKEY_KEYMAP_NAME = "Window"


def _get_addon_preferences():
    package_name = __package__.partition(".src")[0]
    addon = bpy.context.preferences.addons.get(package_name)
    if not addon:
        return None
    return addon.preferences


def _hotkey_mode_enabled() -> bool:
    prefs = _get_addon_preferences()
    return getattr(prefs, "activation_mode", 'SHORTCUT_BUTTON') == 'HOTKEY_MENU'


def _ensure_hotkey_keymap() -> None:
    if addon_keymaps:
        return

    wm = bpy.context.window_manager
    if wm is None:
        return

    kc = wm.keyconfigs.addon
    if kc is None:
        return

    km = kc.keymaps.new(name=HOTKEY_KEYMAP_NAME, space_type='EMPTY')
    kmi = km.keymap_items.new(HOTKEY_OPERATOR_ID, DEFAULT_HOTKEY, 'PRESS')
    addon_keymaps.append((km, kmi))


def _primary_hotkey() -> bpy.types.KeyMapItem | None:
    if not addon_keymaps:
        return None
    return addon_keymaps[0][1]


def set_hotkey(key_type: str) -> bool:
    """Set the editable hotkey row to a plain key press."""
    _ensure_hotkey_keymap()
    kmi = _primary_hotkey()
    if kmi is None:
        return False

    kmi.type = key_type
    kmi.value = 'PRESS'
    kmi.any = False
    kmi.shift = False
    kmi.ctrl = False
    kmi.alt = False
    kmi.oskey = False
    kmi.key_modifier = 'NONE'
    kmi.active = _hotkey_mode_enabled()
    return True


def refresh_keymaps() -> None:
    """Enable the hotkey keymap only when the hotkey activation mode is selected."""
    enabled = _hotkey_mode_enabled()
    if enabled:
        _ensure_hotkey_keymap()

    for _km, kmi in addon_keymaps:
        kmi.active = enabled


def get_hotkey_keymaps() -> tuple[tuple[bpy.types.KeyMap, bpy.types.KeyMapItem], ...]:
    """Return the hotkey keymap for drawing in add-on preferences."""
    if _hotkey_mode_enabled():
        _ensure_hotkey_keymap()
    return tuple(addon_keymaps)


def _is_plain_space(kmi: bpy.types.KeyMapItem | None) -> bool:
    if kmi is None:
        return False
    return (
        kmi.type == 'SPACE'
        and kmi.value == 'PRESS'
        and not kmi.any
        and not kmi.shift
        and not kmi.ctrl
        and not kmi.alt
        and not kmi.oskey
        and kmi.key_modifier == 'NONE'
    )


def hotkey_uses_space() -> bool:
    """Return True when the editable hotkey is currently set to plain Space."""
    return _is_plain_space(_primary_hotkey())


def event_matches_hotkey(event: bpy.types.Event) -> bool:
    """Return True when a modal event matches the configured hotkey."""
    kmi = _primary_hotkey()
    if kmi is None or not _hotkey_mode_enabled():
        return False

    if event.type != kmi.type or event.value != kmi.value:
        return False

    if kmi.any:
        return True

    ignore_shift = kmi.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'}
    ignore_ctrl = kmi.type in {'LEFT_CTRL', 'RIGHT_CTRL'}
    ignore_alt = kmi.type in {'LEFT_ALT', 'RIGHT_ALT'}
    ignore_oskey = kmi.type in {'OSKEY'}

    return (
        (ignore_shift or bool(event.shift) == bool(kmi.shift))
        and (ignore_ctrl or bool(event.ctrl) == bool(kmi.ctrl))
        and (ignore_alt or bool(event.alt) == bool(kmi.alt))
        and (ignore_oskey or bool(event.oskey) == bool(kmi.oskey))
    )


def held_modifier_hotkey_type(event: bpy.types.Event) -> str:
    """Return the configured modifier hotkey type while it is currently held."""
    kmi = _primary_hotkey()
    if kmi is None or not _hotkey_mode_enabled():
        return ""

    modifier_attr = navigation_puck_widget.MODIFIER_KEY_STATE_ATTRS.get(kmi.type)
    if modifier_attr is None:
        return ""

    if event.type == kmi.type and event.value == 'RELEASE':
        return ""

    return kmi.type if bool(getattr(event, modifier_attr, False)) else ""


def event_holds_modifier_hotkey(event: bpy.types.Event) -> bool:
    """Return True while the configured hotkey is a modifier key currently held."""
    return bool(held_modifier_hotkey_type(event))


def register_keymaps():
    """Register keymaps for the addon."""
    refresh_keymaps()


def unregister_keymaps():
    """Unregister keymaps for the addon."""
    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except (ReferenceError, RuntimeError):
            pass

    addon_keymaps.clear()
