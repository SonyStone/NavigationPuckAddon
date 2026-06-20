import typing
import bpy
import gpu

class DrawHandler:
    """
    Manages the Space draw_handler for the widget

    - `Space*.draw_handler_add()`
    - `Space*.draw_handler_remove()`
    
    This is crucial for efficient script execution and avoiding memory leaks, especially in add-ons that dynamically add and remove drawing elements.

    Dev Warning:
    If the draw handler was not removerd on addon reload, you might see this error:
    ```
    ReferenceError: StructRNA of type TestWidget has been removed
    ```
    For example, if you start the operator, then reload the addon without stopping the operator first.
    """
    
    def __init__(self):
        self.handler: typing.Optional[typing.Any] = None
        self.space_type: typing.Optional[type] = None
        self.context_key: typing.Optional[tuple[int, int, int, int]] = None
        self.viewport_rects: tuple[tuple[int, int, int, int], ...] = ()
        self.region_data_pointer: int | None = None
        self.callback: typing.Optional[typing.Callable[..., None]] = None

    def _context_key(self, context: bpy.types.Context) -> tuple[int, int, int, int]:
        return (
            context.window.as_pointer() if context.window else 0,
            context.screen.as_pointer() if context.screen else 0,
            context.area.as_pointer() if context.area else 0,
            context.region.as_pointer() if context.region else 0,
        )

    def _context_viewport_rects(self, context: bpy.types.Context) -> tuple[tuple[int, int, int, int], ...]:
        if context.region is None:
            return ()
        local_rect = (
            0,
            0,
            int(context.region.width),
            int(context.region.height),
        )
        screen_rect = (
            int(context.region.x),
            int(context.region.y),
            int(context.region.width),
            int(context.region.height),
        )
        if screen_rect == local_rect:
            return (local_rect,)
        return (local_rect, screen_rect)

    def _current_state_rect(self, getter_name: str) -> tuple[int, int, int, int] | None:
        try:
            rect = getattr(gpu.state, getter_name)()
        except (AttributeError, ReferenceError, RuntimeError):
            return None
        return tuple(int(round(float(value))) for value in rect)

    def _current_viewport_rects(self) -> tuple[tuple[int, int, int, int], ...]:
        rects: list[tuple[int, int, int, int]] = []
        for getter_name in ("scissor_get", "viewport_get"):
            rect = self._current_state_rect(getter_name)
            if rect is not None and rect not in rects:
                rects.append(rect)
        return tuple(rects)

    def _rect_matches(
        self,
        current_rect: tuple[int, int, int, int],
        owner_rect: tuple[int, int, int, int],
    ) -> bool:
        return all(abs(current - owner) <= 2 for current, owner in zip(current_rect, owner_rect))

    def _current_region_data_pointer(self) -> int | None:
        region_data = getattr(bpy.context, "region_data", None)
        if region_data is None:
            return None
        try:
            return int(region_data.as_pointer())
        except (AttributeError, ReferenceError, RuntimeError):
            return None

    def _region_data_matches(self) -> bool | None:
        if self.region_data_pointer is None:
            return None

        current_region_data_pointer = self._current_region_data_pointer()
        if current_region_data_pointer is None:
            return None

        return current_region_data_pointer == self.region_data_pointer

    def _viewport_matches(self) -> bool:
        region_data_match = self._region_data_matches()
        if region_data_match is not None:
            return region_data_match

        if not self.viewport_rects:
            return True

        current_rects = self._current_viewport_rects()
        if not current_rects:
            return True

        return any(
            self._rect_matches(current_rect, owner_rect)
            for current_rect in current_rects
            for owner_rect in self.viewport_rects
        )

    def update_context(
        self,
        context: bpy.types.Context,
        viewport_rects: tuple[tuple[int, int, int, int], ...] | None = None,
        region_data: bpy.types.RegionView3D | None = None,
    ) -> None:
        self.context_key = self._context_key(context)
        self.viewport_rects = viewport_rects if viewport_rects is not None else self._context_viewport_rects(context)
        try:
            self.region_data_pointer = int(region_data.as_pointer()) if region_data is not None else None
        except (AttributeError, ReferenceError, RuntimeError):
            self.region_data_pointer = None

    def _draw_callback(self, *args: typing.Any) -> None:
        if not self.callback or not self._viewport_matches():
            return
        self.callback(*args)

    def add(self, context: bpy.types.Context, callback: typing.Callable[[typing.Any, bpy.types.Context], None]) -> None:
        """
        Add a draw handler if not already added

        https://docs.blender.org/api/current/bpy.types.Space.html#bpy.types.Space.draw_handler_add

        Args:
            context (bpy.types.Context): The Blender context.
            callback (typing.Callable[[typing.Any, bpy.types.Context], None]): The draw callback function.
        """
        if context.space_data is None:
            return

        args = (self, context)
        space_type = type(context.space_data)

        if self.handler is None:
            self.space_type = space_type
            self.update_context(context)
            self.callback = callback
            self.handler = space_type.draw_handler_add(self._draw_callback, args, 'WINDOW', 'POST_PIXEL')
        else:
            self.update_context(context)
            self.callback = callback

    def remove(self) -> None:
        """
        Remove the draw handler
        
        https://docs.blender.org/api/current/bpy.types.Space.html#bpy.types.Space.draw_handler_remove
        """
        if self.handler:
            try:
                if self.space_type:
                    self.space_type.draw_handler_remove(self.handler, 'WINDOW')
            except (AttributeError, ReferenceError, ValueError):
                pass
            self.handler = None
            self.space_type = None
            self.context_key = None
            self.viewport_rects = ()
            self.region_data_pointer = None
            self.callback = None
            
def force_redraw(context: bpy.types.Context) -> None:
    """Force redraw of the 3D view"""
    if context.area:
        context.area.tag_redraw()
