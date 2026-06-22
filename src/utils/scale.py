import typing


def _positive_float(value: typing.Any, fallback: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return fallback
    if result <= 0.0:
        return fallback
    return result


def interface_scale(context: typing.Any) -> float:
    """Return Blender's user-facing UI scale for custom overlay geometry."""
    preferences = getattr(context, "preferences", None)
    view_preferences = getattr(preferences, "view", None)
    view_scale = _positive_float(getattr(view_preferences, "ui_scale", 1.0), 1.0)
    if view_scale != 1.0:
        return view_scale

    system_preferences = getattr(preferences, "system", None)
    return _positive_float(getattr(system_preferences, "ui_scale", view_scale), view_scale)
