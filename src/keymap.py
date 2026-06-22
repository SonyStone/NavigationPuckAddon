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
HOTKEY_PRESS_VALUE = 'PRESS'
NO_KEY_MODIFIER = 'NONE'
HOTKEY_MODIFIER_FLAGS = ("any", "shift", "ctrl", "alt", "oskey")
MODIFIER_MATCH_CHECKS = (
    ("shift", "shift", {'LEFT_SHIFT', 'RIGHT_SHIFT'}),
    ("ctrl", "ctrl", {'LEFT_CTRL', 'RIGHT_CTRL'}),
    ("alt", "alt", {'LEFT_ALT', 'RIGHT_ALT'}),
    ("oskey", "oskey", {'OSKEY'}),
)


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


def _active_hotkey() -> bpy.types.KeyMapItem | None:
    kmi = _primary_hotkey()
    if kmi is None or not _hotkey_mode_enabled():
        return None
    return kmi


def _clear_hotkey_modifiers(kmi: bpy.types.KeyMapItem) -> None:
    for modifier_flag in HOTKEY_MODIFIER_FLAGS:
        setattr(kmi, modifier_flag, False)
    kmi.key_modifier = NO_KEY_MODIFIER


def _has_no_modifier_flags(kmi: bpy.types.KeyMapItem) -> bool:
    return all(not getattr(kmi, modifier_flag) for modifier_flag in HOTKEY_MODIFIER_FLAGS)


def _is_key_press(kmi: bpy.types.KeyMapItem, key_type: str) -> bool:
    return kmi.type == key_type and kmi.value == HOTKEY_PRESS_VALUE


def _is_plain_key_press(kmi: bpy.types.KeyMapItem | None, key_type: str) -> bool:
    if kmi is None:
        return False
    return (
        _is_key_press(kmi, key_type)
        and _has_no_modifier_flags(kmi)
        and kmi.key_modifier == NO_KEY_MODIFIER
    )


def set_hotkey(key_type: str) -> bool:
    """Set the editable hotkey row to a plain key press."""
    _ensure_hotkey_keymap()
    kmi = _primary_hotkey()
    if kmi is None:
        return False

    kmi.type = key_type
    kmi.value = HOTKEY_PRESS_VALUE
    _clear_hotkey_modifiers(kmi)
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
    return _is_plain_key_press(kmi, 'SPACE')


def hotkey_uses_space() -> bool:
    """Return True when the editable hotkey is currently set to plain Space."""
    return _is_plain_space(_primary_hotkey())


def _modifier_state_matches(event_value: bool, keymap_value: bool, ignore_state: bool) -> bool:
    return ignore_state or bool(event_value) == bool(keymap_value)


def _hotkey_modifier_states_match(event: bpy.types.Event, kmi: bpy.types.KeyMapItem) -> bool:
    return all(
        _modifier_state_matches(
            getattr(event, event_attr),
            getattr(kmi, keymap_attr),
            kmi.type in ignored_key_types,
        )
        for event_attr, keymap_attr, ignored_key_types in MODIFIER_MATCH_CHECKS
    )


def _event_matches_keymap_item(event: bpy.types.Event, kmi: bpy.types.KeyMapItem) -> bool:
    return event.type == kmi.type and event.value == kmi.value


def event_matches_hotkey(event: bpy.types.Event) -> bool:
    """Return True when a modal event matches the configured hotkey."""
    kmi = _active_hotkey()
    if kmi is None:
        return False

    if not _event_matches_keymap_item(event, kmi):
        return False

    if kmi.any:
        return True

    return _hotkey_modifier_states_match(event, kmi)


def _event_releases_hotkey(event: bpy.types.Event, kmi: bpy.types.KeyMapItem) -> bool:
    return event.type == kmi.type and event.value == 'RELEASE'


def held_modifier_hotkey_type(event: bpy.types.Event) -> str:
    """Return the configured modifier hotkey type while it is currently held."""
    kmi = _active_hotkey()
    if kmi is None:
        return ""

    modifier_attr = navigation_puck_widget.MODIFIER_KEY_STATE_ATTRS.get(kmi.type)
    if modifier_attr is None:
        return ""

    if _event_releases_hotkey(event, kmi):
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
