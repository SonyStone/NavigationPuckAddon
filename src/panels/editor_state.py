import bpy

from .editor_context import (
    SUPPORTED_EDITOR_TYPES,
    VIEW2D_EDITOR_TYPES,
    context_editor_type,
    region_view3d_for_position,
)
from .shortcut_layout import supports_puck_action


class EditorState:
    """Supported editor type and action capability state for a modal overlay."""

    def __init__(self) -> None:
        self.editor_type: str | None = None
        self.is_camera_view = False
        self.is_camera_view_locked = False

    def update(
        self,
        context: bpy.types.Context,
        region_data: bpy.types.RegionView3D | None = None,
    ) -> None:
        editor_type = context_editor_type(context)
        if editor_type in SUPPORTED_EDITOR_TYPES:
            self.editor_type = editor_type

        self.is_camera_view = False
        self.is_camera_view_locked = False
        if self.editor_type != 'VIEW_3D':
            return

        rv3d = region_data or region_view3d_for_position(context)
        if rv3d is None:
            return

        self.is_camera_view = rv3d.view_perspective == 'CAMERA'
        self.is_camera_view_locked = self.is_camera_view and bool(getattr(context.space_data, "lock_camera", False))

    def is_view2d_editor(self) -> bool:
        return self.editor_type in VIEW2D_EDITOR_TYPES

    def supports_action(self, action: str) -> bool:
        return supports_puck_action(
            action,
            is_view2d_editor=self.is_view2d_editor(),
            is_camera_view=self.is_camera_view,
            is_camera_view_locked=self.is_camera_view_locked,
        )
