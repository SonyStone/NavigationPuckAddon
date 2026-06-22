import typing

import bpy

from ..activation import blender_development_launch, uses_overlay_activation
from .editor_context import editor_context_key, find_supported_editor_overrides


SHORTCUT_AUTOSTART_INITIAL_DELAY = 1.0
SHORTCUT_AUTOSTART_INTERVAL = 0.5

_shortcut_autostart_enabled = False
_shortcut_operator_type: typing.Any | None = None
_allow_blender_development_runtime = False


def configure(shortcut_operator_type: typing.Any) -> None:
    global _shortcut_operator_type
    _shortcut_operator_type = shortcut_operator_type


def refresh_activation_runtime(
    context: bpy.types.Context | None = None,
    *,
    allow_blender_development: bool = False,
) -> None:
    """Start or stop cursor-driven overlay operators for the selected activation mode."""
    global _shortcut_autostart_enabled, _allow_blender_development_runtime

    if _shortcut_operator_type is None:
        return

    context = context or bpy.context
    _allow_blender_development_runtime = allow_blender_development
    if bpy.app.background or (blender_development_launch() and not _allow_blender_development_runtime):
        _shortcut_autostart_enabled = False
        _unregister_start_timer()
        _shortcut_operator_type.shutdown_all()
        return

    _shortcut_autostart_enabled = uses_overlay_activation(context)
    if _shortcut_autostart_enabled:
        if not bpy.app.timers.is_registered(_start_shortcut_operator):
            bpy.app.timers.register(_start_shortcut_operator, first_interval=SHORTCUT_AUTOSTART_INITIAL_DELAY)
        return

    _shortcut_operator_type.shutdown_all()
    _unregister_start_timer()


def shutdown() -> None:
    global _shortcut_autostart_enabled, _allow_blender_development_runtime

    _shortcut_autostart_enabled = False
    _allow_blender_development_runtime = False
    _unregister_start_timer()
    if _shortcut_operator_type is not None:
        _shortcut_operator_type.shutdown_all()


def _unregister_start_timer() -> None:
    if bpy.app.timers.is_registered(_start_shortcut_operator):
        bpy.app.timers.unregister(_start_shortcut_operator)


def _editor_context_keys(
    overrides: typing.Iterable[dict[str, typing.Any]],
) -> set[tuple[int, int, int, int]]:
    existing_keys: set[tuple[int, int, int, int]] = set()
    for override in overrides:
        try:
            existing_keys.add(editor_context_key(override))
        except (ReferenceError, RuntimeError, TypeError):
            continue
    return existing_keys


def _refresh_or_start_shortcut(override: dict[str, typing.Any]) -> None:
    if _shortcut_operator_type is None:
        return

    try:
        key = editor_context_key(override)
        app = _shortcut_operator_type.get_app(key)
        with bpy.context.temp_override(**override):
            if app and app.is_running:
                app.refresh_context(bpy.context)
            else:
                bpy.ops.navigation_puck.shortcut('INVOKE_DEFAULT')
    except (ReferenceError, RuntimeError, TypeError) as ex:
        print(f"Navigation Puck shortcut autostart failed: {ex}")


def _start_shortcut_operator() -> float | None:
    if _shortcut_operator_type is None or bpy.app.background:
        return None

    if blender_development_launch() and not _allow_blender_development_runtime:
        _shortcut_operator_type.shutdown_all()
        return None

    if not _shortcut_autostart_enabled or not uses_overlay_activation(bpy.context):
        _shortcut_operator_type.shutdown_all()
        return None

    overrides = find_supported_editor_overrides(bpy.context.window_manager)
    if not overrides:
        _shortcut_operator_type.shutdown_all()
        return SHORTCUT_AUTOSTART_INTERVAL

    _shortcut_operator_type.prune_missing(_editor_context_keys(overrides))

    for override in overrides:
        _refresh_or_start_shortcut(override)

    return SHORTCUT_AUTOSTART_INTERVAL
