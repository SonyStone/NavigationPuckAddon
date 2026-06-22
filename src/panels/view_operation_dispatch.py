import typing

import bpy
import mathutils

from .editor_context import RegionLocalEvent


def handle_view_operation_events(
    view_ops: typing.Any,
    owner_context: typing.Any,
    context: bpy.types.Context,
    local_event: RegionLocalEvent,
    *,
    is_view2d_editor: bool,
) -> bool:
    handled_view_event = False
    for view_handler in view_ops.handlers(is_view2d_editor):
        handled_view_event = owner_context.run(
            context,
            lambda owner_context, handler=view_handler: handler.event_handler(owner_context, local_event),
        ) or handled_view_event
    return handled_view_event


def apply_view_action(
    view_ops: typing.Any,
    owner_context: typing.Any,
    context: bpy.types.Context,
    action: str,
    delta: mathutils.Vector,
    mouse_pos: mathutils.Vector,
    pointer_offset: mathutils.Vector,
    *,
    is_view2d_editor: bool,
    shift: bool = False,
) -> None:
    owner_context.run(
        context,
        lambda context_override: view_ops.apply_action(
            context_override,
            action,
            delta,
            mouse_pos,
            pointer_offset,
            is_view2d_editor,
            shift=shift,
        ),
    )
