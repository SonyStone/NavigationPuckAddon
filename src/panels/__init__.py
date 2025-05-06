import bpy

from . import view_tools_widget
from . import main_panel

classes = (
    *main_panel.classes,
    *view_tools_widget.classes,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
