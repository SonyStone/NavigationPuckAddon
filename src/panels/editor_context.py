import typing

import bpy
import mathutils


SUPPORTED_EDITOR_TYPES = {'VIEW_3D', 'IMAGE_EDITOR', 'NODE_EDITOR'}
VIEW2D_EDITOR_TYPES = {'IMAGE_EDITOR', 'NODE_EDITOR'}

ViewportRect = tuple[int, int, int, int]
QuadWindowRegionEntry = tuple[ViewportRect, bpy.types.Region]


def context_editor_type(context: bpy.types.Context) -> str | None:
    if context.area is None:
        return None
    return context.area.type


def context_key(context: bpy.types.Context) -> tuple[int, int, int, int]:
    return (
        context.window.as_pointer() if context.window else 0,
        context.screen.as_pointer() if context.screen else 0,
        context.area.as_pointer() if context.area else 0,
        context.region.as_pointer() if context.region else 0,
    )


def context_area_key(context: bpy.types.Context) -> tuple[int, int, int]:
    return context_key(context)[:3]


def _rect_variants(context: bpy.types.Context, rect: ViewportRect) -> tuple[ViewportRect, ...]:
    rects = [rect]
    if context.region:
        screen_rect = (
            int(context.region.x) + rect[0],
            int(context.region.y) + rect[1],
            rect[2],
            rect[3],
        )
        if screen_rect != rect:
            rects.append(screen_rect)
    return tuple(rects)


def _full_region_rect(context: bpy.types.Context) -> ViewportRect:
    if not context.region:
        return (0, 0, 1, 1)
    return (0, 0, int(context.region.width), int(context.region.height))


def _area_origin_and_size(context: bpy.types.Context) -> tuple[int, int, int, int]:
    return (
        int(getattr(context.area, "x", 0)),
        int(getattr(context.area, "y", 0)),
        int(getattr(context.area, "width", 0)),
        int(getattr(context.area, "height", 0)),
    )


def _is_quad_window_region_candidate(region: bpy.types.Region) -> bool:
    return region.type == 'WINDOW' and region.width > 1 and region.height > 1


def _region_rect_relative_to_area(region: bpy.types.Region, area_x: int, area_y: int) -> ViewportRect:
    return (
        int(region.x) - area_x,
        int(region.y) - area_y,
        int(region.width),
        int(region.height),
    )


def _rect_covers_area(rect: ViewportRect, area_width: int, area_height: int) -> bool:
    return area_width > 1 and area_height > 1 and rect[2] >= area_width and rect[3] >= area_height


def _append_unique_quad_region_entry(
    entries: list[QuadWindowRegionEntry],
    rect: ViewportRect,
    region: bpy.types.Region,
) -> None:
    if not any(existing_rect == rect for existing_rect, _region in entries):
        entries.append((rect, region))


def _quad_window_region_entries(context: bpy.types.Context) -> tuple[QuadWindowRegionEntry, ...]:
    if context.area is None:
        return ()

    area_x, area_y, area_width, area_height = _area_origin_and_size(context)
    entries: list[QuadWindowRegionEntry] = []
    for region in context.area.regions:
        if not _is_quad_window_region_candidate(region):
            continue
        rect = _region_rect_relative_to_area(region, area_x, area_y)
        if _rect_covers_area(rect, area_width, area_height):
            continue
        _append_unique_quad_region_entry(entries, rect, region)
    if len(entries) < 4:
        return ()
    return tuple(entries)


def _quad_window_region_rects(context: bpy.types.Context) -> tuple[ViewportRect, ...]:
    return tuple(rect for rect, _region in _quad_window_region_entries(context))


def _quad_rect_by_corner(
    rects: tuple[ViewportRect, ...],
    area_width: int,
    area_height: int,
    *,
    left: bool,
    top: bool,
) -> ViewportRect | None:
    mid_x = float(area_width) * 0.5
    mid_y = float(area_height) * 0.5
    candidates: list[ViewportRect] = []
    for rect in rects:
        x, y, width, height = rect
        center_x = x + (width * 0.5)
        center_y = y + (height * 0.5)
        if left != (center_x < mid_x):
            continue
        if top != (center_y >= mid_y):
            continue
        candidates.append(rect)

    if not candidates:
        return None
    return max(candidates, key=lambda rect: rect[2] * rect[3])


def _quad_window_region_for_rect(
    context: bpy.types.Context,
    rect: ViewportRect,
) -> bpy.types.Region | None:
    for candidate_rect, region in _quad_window_region_entries(context):
        if candidate_rect == rect:
            return region
    return None


def _fallback_quad_view_rects(context: bpy.types.Context) -> tuple[ViewportRect, ViewportRect, ViewportRect, ViewportRect]:
    width = int(getattr(context.area, "width", 0)) if context.area else 0
    height = int(getattr(context.area, "height", 0)) if context.area else 0
    if width <= 1 or height <= 1:
        width = int(context.region.width) * 2 if context.region else 2
        height = int(context.region.height) * 2 if context.region else 2

    mid_x = max(width // 2, 1)
    mid_y = max(height // 2, 1)
    right_width = max(width - mid_x, 1)
    top_height = max(height - mid_y, 1)
    return (
        (0, mid_y, mid_x, top_height),
        (mid_x, mid_y, right_width, top_height),
        (0, 0, mid_x, mid_y),
        (mid_x, 0, right_width, mid_y),
    )


def _has_quad_view_context(context: bpy.types.Context) -> bool:
    return (
        context.area is not None
        and context.area.type == 'VIEW_3D'
        and context.region is not None
        and context.space_data is not None
    )


def _quad_view_rects(context: bpy.types.Context, window_rects: tuple[ViewportRect, ...]) -> tuple[ViewportRect, ...]:
    area_width = int(getattr(context.area, "width", 0))
    area_height = int(getattr(context.area, "height", 0))
    fallback_top_left, fallback_top_right, fallback_bottom_left, fallback_bottom_right = _fallback_quad_view_rects(context)

    return (
        _quad_rect_by_corner(window_rects, area_width, area_height, left=True, top=True) or fallback_top_left,
        _quad_rect_by_corner(window_rects, area_width, area_height, left=False, top=True) or fallback_top_right,
        _quad_rect_by_corner(window_rects, area_width, area_height, left=True, top=False) or fallback_bottom_left,
        _quad_rect_by_corner(window_rects, area_width, area_height, left=False, top=False) or fallback_bottom_right,
    )


def _quad_view_entries(context: bpy.types.Context) -> tuple[tuple[ViewportRect, bpy.types.RegionView3D], ...]:
    if not _has_quad_view_context(context):
        return ()

    quadviews = tuple(getattr(context.space_data, "region_quadviews", ()))
    if len(quadviews) < 4:
        return ()

    window_rects = _quad_window_region_rects(context)
    top_left, top_right, bottom_left, bottom_right = _quad_view_rects(context, window_rects)
    region_3d = getattr(context.space_data, "region_3d", None) or quadviews[3]

    return (
        (top_left, quadviews[1]),
        (top_right, region_3d),
        (bottom_left, quadviews[0]),
        (bottom_right, quadviews[2]),
    )


def _quad_view_entry_at(
    context: bpy.types.Context,
    position: mathutils.Vector | None,
) -> tuple[ViewportRect, bpy.types.RegionView3D] | None:
    if position is None:
        return None

    for rect, region_data in _quad_view_entries(context):
        x, y, width, height = rect
        if x <= position.x < x + width and y <= position.y < y + height:
            return rect, region_data
    return None


def viewport_local_rect_for_position(
    context: bpy.types.Context,
    position: mathutils.Vector | None = None,
) -> ViewportRect:
    quad_entry = _quad_view_entry_at(context, position)
    return quad_entry[0] if quad_entry else _full_region_rect(context)


def window_region_for_position(
    context: bpy.types.Context,
    position: mathutils.Vector | None = None,
) -> bpy.types.Region | None:
    quad_entry = _quad_view_entry_at(context, position)
    if quad_entry:
        return _quad_window_region_for_rect(context, quad_entry[0]) or context.region
    return context.region


def _context_is_view3d(context: bpy.types.Context) -> bool:
    return bool(context.area and context.area.type == 'VIEW_3D' and context.space_data)


def _context_region_view3d(context: bpy.types.Context) -> bpy.types.RegionView3D | None:
    region_data = getattr(context, "region_data", None)
    if region_data is not None and hasattr(region_data, "view_matrix"):
        return region_data
    return None


def region_view3d_for_position(
    context: bpy.types.Context,
    position: mathutils.Vector | None = None,
) -> bpy.types.RegionView3D | None:
    if not _context_is_view3d(context):
        return None

    quad_entry = _quad_view_entry_at(context, position)
    if quad_entry:
        return quad_entry[1]

    region_data = _context_region_view3d(context)
    if region_data is not None:
        return region_data

    return getattr(context.space_data, "region_3d", None)


def viewport_rects_for_position(
    context: bpy.types.Context,
    position: mathutils.Vector | None = None,
) -> tuple[ViewportRect, ...]:
    return _rect_variants(context, viewport_local_rect_for_position(context, position))


def event_region_position(event: bpy.types.Event, fallback: mathutils.Vector) -> mathutils.Vector:
    x = getattr(event, "mouse_region_x", fallback.x)
    y = getattr(event, "mouse_region_y", fallback.y)
    return mathutils.Vector((x, y))


def _quad_region_area_offset(context: bpy.types.Context) -> tuple[int, int] | None:
    if not _quad_view_entries(context) or context.area is None or context.region is None:
        return None
    return int(context.region.x) - int(context.area.x), int(context.region.y) - int(context.area.y)


def _position_is_region_local(context: bpy.types.Context, position: mathutils.Vector) -> bool:
    if context.region is None:
        return False
    return position.x <= float(context.region.width) + 2.0 and position.y <= float(context.region.height) + 2.0


def event_area_position(
    context: bpy.types.Context,
    event: bpy.types.Event,
    fallback: mathutils.Vector,
) -> mathutils.Vector:
    position = event_region_position(event, fallback)
    region_offset = _quad_region_area_offset(context)
    if region_offset is None:
        return position

    region_x, region_y = region_offset
    if region_x == 0 and region_y == 0:
        return position

    if _position_is_region_local(context, position):
        return mathutils.Vector((position.x + region_x, position.y + region_y))

    return position


def event_window_position(event: bpy.types.Event) -> mathutils.Vector | None:
    x = getattr(event, "mouse_x", None)
    y = getattr(event, "mouse_y", None)
    if x is None or y is None:
        return None
    return mathutils.Vector((x, y))


def event_position_in_context(
    context: bpy.types.Context,
    event: bpy.types.Event,
    fallback: mathutils.Vector,
) -> mathutils.Vector:
    window_position = event_window_position(event)
    if window_position is None or context.region is None:
        return event_area_position(context, event, fallback)

    if _quad_view_entries(context) and context.area is not None:
        return mathutils.Vector((
            window_position.x - int(context.area.x),
            window_position.y - int(context.area.y),
        ))

    return mathutils.Vector((
        window_position.x - int(context.region.x),
        window_position.y - int(context.region.y),
    ))


def _region_contains_window_position(region: bpy.types.Region, position: mathutils.Vector) -> bool:
    return (
        int(region.x) <= position.x < int(region.x) + int(region.width)
        and int(region.y) <= position.y < int(region.y) + int(region.height)
    )


def _active_supported_space(area: bpy.types.Area) -> typing.Any | None:
    if area.type not in SUPPORTED_EDITOR_TYPES:
        return None

    space = area.spaces.active
    if space is None or space.type not in SUPPORTED_EDITOR_TYPES:
        return None

    return space


def _window_screen(window: bpy.types.Window) -> bpy.types.Screen | None:
    try:
        return window.screen
    except (ReferenceError, RuntimeError, TypeError):
        return None


def _context_window_screen(context: bpy.types.Context) -> tuple[bpy.types.Window, bpy.types.Screen] | None:
    if context.window is None:
        return None

    screen = context.screen or getattr(context.window, "screen", None)
    if screen is None:
        return None

    return context.window, screen


def _supported_area_spaces(screen: bpy.types.Screen) -> typing.Iterator[tuple[bpy.types.Area, typing.Any]]:
    for area in screen.areas:
        try:
            space = _active_supported_space(area)
        except (ReferenceError, RuntimeError, TypeError):
            continue

        if space is not None:
            yield area, space


def _window_regions(area: bpy.types.Area) -> typing.Iterator[bpy.types.Region]:
    try:
        regions = tuple(area.regions)
    except (ReferenceError, RuntimeError, TypeError):
        return

    for region in regions:
        try:
            if region.type == 'WINDOW':
                yield region
        except (ReferenceError, RuntimeError, TypeError):
            continue


def _editor_override_for_region(
    window: bpy.types.Window,
    screen: bpy.types.Screen,
    area: bpy.types.Area,
    region: bpy.types.Region,
    space: typing.Any,
    *,
    require_view3d_region_data: bool = False,
) -> dict[str, typing.Any] | None:
    if region.type != 'WINDOW':
        return None

    override: dict[str, typing.Any] = {
        "window": window,
        "screen": screen,
        "area": area,
        "region": region,
        "space_data": space,
    }
    if area.type == 'VIEW_3D':
        region_data = getattr(space, "region_3d", None)
        if region_data is None and require_view3d_region_data:
            return None
        if region_data is not None:
            override["region_data"] = region_data
    return override


def _editor_override_at_position(
    window: bpy.types.Window,
    screen: bpy.types.Screen,
    area: bpy.types.Area,
    space: typing.Any,
    position: mathutils.Vector,
) -> dict[str, typing.Any] | None:
    region = _window_region_at_position(area, position)
    if region is None:
        return None
    return _editor_override_for_region(window, screen, area, region, space)


def _window_region_at_position(area: bpy.types.Area, position: mathutils.Vector) -> bpy.types.Region | None:
    for region in _window_regions(area):
        if _region_contains_window_position(region, position):
            return region
    return None


def _first_editor_override_for_area(
    window: bpy.types.Window,
    screen: bpy.types.Screen,
    area: bpy.types.Area,
    space: typing.Any,
    *,
    require_view3d_region_data: bool = False,
) -> dict[str, typing.Any] | None:
    for region in _window_regions(area):
        override = _editor_override_for_region(
            window,
            screen,
            area,
            region,
            space,
            require_view3d_region_data=require_view3d_region_data,
        )
        if override is not None:
            return override
    return None


def editor_context_override_at_event(
    context: bpy.types.Context,
    event: bpy.types.Event,
) -> dict[str, typing.Any] | None:
    window_position = event_window_position(event)
    window_screen = _context_window_screen(context)
    if window_position is None or window_screen is None:
        return None

    window, screen = window_screen
    for area, space in _supported_area_spaces(screen):
        override = _editor_override_at_position(window, screen, area, space, window_position)
        if override is not None:
            return override

    return None


def editor_context_key(override: dict[str, typing.Any]) -> tuple[int, int, int, int]:
    return (
        override["window"].as_pointer(),
        override["screen"].as_pointer(),
        override["area"].as_pointer(),
        override["region"].as_pointer(),
    )


def find_supported_editor_overrides(
    window_manager: bpy.types.WindowManager | None,
) -> list[dict[str, typing.Any]]:
    if not window_manager:
        return []

    overrides: list[dict[str, typing.Any]] = []
    for window in window_manager.windows:
        overrides.extend(_supported_editor_overrides_for_window(window))
    return overrides


def _supported_editor_overrides_for_window(window: bpy.types.Window) -> list[dict[str, typing.Any]]:
    screen = _window_screen(window)
    if screen is None:
        return []

    overrides: list[dict[str, typing.Any]] = []
    for area, space in _supported_area_spaces(screen):
        override = _first_editor_override_for_area(
            window,
            screen,
            area,
            space,
            require_view3d_region_data=True,
        )
        if override is not None:
            overrides.append(override)
    return overrides


def event_window_position_is_in_context_area(
    context: bpy.types.Context,
    event: bpy.types.Event,
) -> bool:
    window_position = event_window_position(event)
    if window_position is None:
        return True

    if context.area is None:
        return False

    return _window_region_at_position(context.area, window_position) is not None


def local_viewport_position(context: bpy.types.Context, position: mathutils.Vector) -> mathutils.Vector:
    x, y, _width, _height = viewport_local_rect_for_position(context, position)
    return mathutils.Vector((position.x - x, position.y - y))


class RegionLocalEvent:
    """Event proxy with mouse_region coordinates localized to the selected viewport."""

    def __init__(self, event: bpy.types.Event, position: mathutils.Vector) -> None:
        self._event = event
        self.mouse_region_x = position.x
        self.mouse_region_y = position.y

    def __getattr__(self, name: str) -> typing.Any:
        return getattr(self._event, name)


def make_context_override(
    context: bpy.types.Context,
    position: mathutils.Vector | None = None,
) -> dict[str, typing.Any] | None:
    if not _has_override_context_members(context):
        return None

    owner_region = window_region_for_position(context, position)

    override: dict[str, typing.Any] = {
        "window": context.window,
        "screen": context.screen,
        "area": context.area,
        "region": owner_region or context.region,
        "space_data": context.space_data,
    }
    region_data = region_view3d_for_position(context, position)
    if region_data is not None:
        override["region_data"] = region_data
    return override


def _has_override_context_members(context: bpy.types.Context) -> bool:
    return bool(context.window and context.screen and context.area and context.region and context.space_data)


def _area_is_supported(area: bpy.types.Area | None) -> bool:
    return bool(area and area.type in SUPPORTED_EDITOR_TYPES)


def _region_is_window(region: bpy.types.Region | None) -> bool:
    return bool(region and region.type == 'WINDOW')


def _space_is_supported(space_data: typing.Any | None) -> bool:
    return bool(space_data and space_data.type in SUPPORTED_EDITOR_TYPES)


def is_supported_editor_context(context: bpy.types.Context) -> bool:
    return bool(
        context.window
        and context.screen
        and _area_is_supported(context.area)
        and _region_is_window(context.region)
        and _space_is_supported(context.space_data)
    )
