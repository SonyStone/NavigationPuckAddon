import os
import typing

import bpy


ACTIVATION_SHORTCUT_BUTTON = 'SHORTCUT_BUTTON'
ACTIVATION_DIRECT_MENU = 'DIRECT_MENU'
ACTIVATION_HOTKEY_MENU = 'HOTKEY_MENU'
DEFAULT_ACTIVATION_MODE = ACTIVATION_HOTKEY_MENU

OVERLAY_ACTIVATION_MODES = {ACTIVATION_SHORTCUT_BUTTON, ACTIVATION_DIRECT_MENU, ACTIVATION_HOTKEY_MENU}

MODIFIER_KEY_STATE_ATTRS = {
    'LEFT_SHIFT': 'shift',
    'RIGHT_SHIFT': 'shift',
    'LEFT_CTRL': 'ctrl',
    'RIGHT_CTRL': 'ctrl',
    'LEFT_ALT': 'alt',
    'RIGHT_ALT': 'alt',
    'OSKEY': 'oskey',
}


def get_addon_preferences(context: bpy.types.Context) -> typing.Any | None:
    """Return this add-on's preferences, if Blender has them available."""
    package_name = __package__.partition(".src")[0]
    addon = context.preferences.addons.get(package_name)
    if not addon:
        return None
    return addon.preferences


def get_activation_mode(context: bpy.types.Context) -> str:
    prefs = get_addon_preferences(context)
    return str(getattr(prefs, "activation_mode", DEFAULT_ACTIVATION_MODE))


def uses_overlay_activation(context: bpy.types.Context) -> bool:
    return get_activation_mode(context) in OVERLAY_ACTIVATION_MODES


def blender_development_launch(environ: typing.Mapping[str, str] | None = None) -> bool:
    environ = environ or os.environ
    return bool(environ.get("ADDONS_TO_LOAD") and environ.get("EDITOR_PORT"))


def get_mode_menu_button_size(
    prefs: typing.Any,
    activation_mode: str,
    fallback: float,
) -> float:
    fallback = float(getattr(prefs, "menu_button_size", fallback))
    prop_name = {
        ACTIVATION_SHORTCUT_BUTTON: "shortcut_menu_button_size",
        ACTIVATION_DIRECT_MENU: "direct_menu_button_size",
        ACTIVATION_HOTKEY_MENU: "hotkey_menu_button_size",
    }.get(activation_mode, "menu_button_size")
    return max(float(getattr(prefs, prop_name, fallback)), 1.0)
