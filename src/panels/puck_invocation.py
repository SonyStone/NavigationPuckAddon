import typing

import bpy
import mathutils

from ..utils.operator_return import OperatorReturnType


def _call_navigation_puck_widget(
    anchor: mathutils.Vector,
    *,
    drag_select: bool,
    dismiss_on_key_release: bool,
    dismiss_key_type: str,
) -> OperatorReturnType:
    return bpy.ops.navigation_puck.widget(
        'INVOKE_DEFAULT',
        follow_mouse=False,
        drag_select=drag_select,
        anchor_x=anchor.x,
        anchor_y=anchor.y,
        dismiss_on_key_release=dismiss_on_key_release,
        dismiss_key_type=dismiss_key_type,
    )


def _invoke_navigation_puck_widget(
    context: bpy.types.Context,
    anchor: mathutils.Vector,
    *,
    drag_select: bool,
    dismiss_on_key_release: bool,
    dismiss_key_type: str,
    context_override: dict[str, typing.Any] | None = None,
) -> OperatorReturnType:
    if context_override:
        with context.temp_override(**context_override):
            return _call_navigation_puck_widget(
                anchor,
                drag_select=drag_select,
                dismiss_on_key_release=dismiss_on_key_release,
                dismiss_key_type=dismiss_key_type,
            )
    return _call_navigation_puck_widget(
        anchor,
        drag_select=drag_select,
        dismiss_on_key_release=dismiss_on_key_release,
        dismiss_key_type=dismiss_key_type,
    )


def _run_with_context_override(
    context: bpy.types.Context,
    context_override: dict[str, typing.Any] | None,
    callback: typing.Callable[[bpy.types.Context], typing.Any],
) -> typing.Any:
    if not context_override:
        return callback(context)

    try:
        with context.temp_override(**context_override):
            return callback(bpy.context)
    except (ReferenceError, RuntimeError, TypeError):
        return callback(context)
