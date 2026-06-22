import bpy


def _required_modal_context_members(context: bpy.types.Context) -> tuple[object | None, ...]:
    return (
        context.window_manager,
        context.window,
        context.screen,
        context.area,
    )


def _has_window_region(context: bpy.types.Context) -> bool:
    return context.region is not None and context.region.type == 'WINDOW'


def _can_add_modal_handler(context: bpy.types.Context) -> bool:
    return all(member is not None for member in _required_modal_context_members(context)) and _has_window_region(context)


def add_modal_handler(context: bpy.types.Context, operator: bpy.types.Operator) -> bool:
    """Add a modal handler when Blender has a complete UI context."""
    if not _can_add_modal_handler(context):
        return False

    try:
        context.window_manager.modal_handler_add(operator)
    except (ReferenceError, RuntimeError, TypeError):
        return False

    return True
