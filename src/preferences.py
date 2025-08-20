import bpy  # type: ignore
from .panels.view_tools_widget import NAVIGATION_PUCK_OT_view_tools_widget
from .. import __package__  as base_package
import rna_keymap_ui

class NavigationPuckPreferences(bpy.types.AddonPreferences):
    """Preferences for the Navigation Puck addon."""
    # The `bl_idname` must match the addon module name in `bl_info`
    bl_idname = base_package 

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        kc = wm.keyconfigs.user

        if kc:
            km = kc.keymaps.get("3D View")
            if km:
                for kmi in km.keymap_items:
                    if kmi.idname == NAVIGATION_PUCK_OT_view_tools_widget.bl_idname:
                        rna_keymap_ui.draw_kmi([], kc, km, kmi, layout, 0)


classes = (
    NavigationPuckPreferences,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
