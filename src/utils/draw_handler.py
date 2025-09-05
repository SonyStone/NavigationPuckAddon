import typing
import bpy

class DrawHandler:
    """
    Manages the Space draw_handler for the widget

    - `SpaceView3D.draw_handler_add()`
    - `SpaceView3D.draw_handler_remove()`
    
    This is crucial for efficient script execution and avoiding memory leaks, especially in add-ons that dynamically add and remove drawing elements.

    Dev Warning:
    If the draw handler was not removerd on addon reload, you might see this error:
    ```
    ReferenceError: StructRNA of type TestWidget has been removed
    ```
    For example, if you start the operator, then reload the addon without stopping the operator first.
    """
    handler: typing.Optional[typing.Any] = None

    def add(self, context: bpy.types.Context, callback: typing.Callable[[typing.Any, bpy.types.Context], None]) -> None:
        """
        Add a draw handler if not already added

        https://docs.blender.org/api/current/bpy.types.SpaceView3D.html#bpy.types.SpaceView3D.draw_handler_add

        Args:
            context (bpy.types.Context): The Blender context.
            callback (typing.Callable[[typing.Any, bpy.types.Context], None]): The draw callback function.
        """
        args = (self, context)

        if self.handler is None:
            self.handler = bpy.types.SpaceView3D.draw_handler_add(callback, args, 'WINDOW', 'POST_PIXEL')

    def remove(self) -> None:
        """
        Remove the draw handler
        
        https://docs.blender.org/api/current/bpy.types.Space.html#bpy.types.Space.draw_handler_remove
        """
        if self.handler:
            bpy.types.SpaceView3D.draw_handler_remove(self.handler, 'WINDOW')
            self.handler = None