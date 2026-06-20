import typing
import bpy

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
        self.callback: typing.Optional[typing.Callable[..., None]] = None

    def _context_key(self, context: bpy.types.Context) -> tuple[int, int, int, int]:
        return (
            context.window.as_pointer() if context.window else 0,
            context.screen.as_pointer() if context.screen else 0,
            context.area.as_pointer() if context.area else 0,
            context.region.as_pointer() if context.region else 0,
        )

    def _draw_callback(self, *args: typing.Any) -> None:
        if self.callback:
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
            self.context_key = self._context_key(context)
            self.callback = callback
            self.handler = space_type.draw_handler_add(self._draw_callback, args, 'WINDOW', 'POST_PIXEL')

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
            self.callback = None
            
def force_redraw(context: bpy.types.Context) -> None:
    """Force redraw of the 3D view"""
    if context.area:
        context.area.tag_redraw()
