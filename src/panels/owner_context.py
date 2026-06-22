import typing

import bpy
import mathutils

from .editor_context import (
    ViewportRect,
    _quad_view_entries,
    context_area_key,
    context_key,
    is_supported_editor_context,
    make_context_override,
    region_view3d_for_position,
    viewport_local_rect_for_position,
    viewport_rects_for_position,
)
from .puck_invocation import _run_with_context_override


class OwnerContext:
    """Editor context captured by a modal overlay."""

    def __init__(self) -> None:
        self.clear()

    def clear(self) -> None:
        self.context_key: tuple[int, int, int, int] | None = None
        self.context_override: dict[str, typing.Any] | None = None
        self.viewport_rects: tuple[ViewportRect, ...] = ()
        self.viewport_rect: ViewportRect = (0, 0, 1, 1)
        self.region_data: bpy.types.RegionView3D | None = None

    def set(
        self,
        context: bpy.types.Context,
        position: mathutils.Vector | None = None,
        *,
        update_key: bool,
    ) -> None:
        if update_key:
            self.context_key = context_key(context)
        self.context_override = make_context_override(context, position)
        self.viewport_rect = viewport_local_rect_for_position(context, position)
        self.viewport_rects = viewport_rects_for_position(context, position)
        self.region_data = region_view3d_for_position(context, position)

    def update_draw_handler(self, draw_handler: typing.Any, context: bpy.types.Context) -> None:
        draw_handler.update_context(context, self.viewport_rects, self.region_data)

    def local_position(self, position: mathutils.Vector) -> mathutils.Vector:
        return mathutils.Vector((
            position.x - self.viewport_rect[0],
            position.y - self.viewport_rect[1],
        ))

    def region_position(self, position: mathutils.Vector) -> mathutils.Vector:
        return mathutils.Vector((
            position.x + self.viewport_rect[0],
            position.y + self.viewport_rect[1],
        ))

    def run(
        self,
        context: bpy.types.Context,
        callback: typing.Callable[[bpy.types.Context], typing.Any],
    ) -> typing.Any:
        return _run_with_context_override(context, self.context_override, callback)

    def matches_menu_context(self, context: bpy.types.Context) -> bool:
        if self.context_key is None:
            return True

        current_key = context_key(context)
        if current_key == self.context_key:
            return True

        # In Quad View Blender can deliver modal events through a different
        # WINDOW region than the one that owns the drawn menu.
        return bool(_quad_view_entries(context) and context_area_key(context) == self.context_key[:3])

    def matches_supported_context(self, context: bpy.types.Context) -> bool:
        return is_supported_editor_context(context) and context_key(context) == self.context_key
