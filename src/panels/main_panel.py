from math import pi
import typing
import bpy
from src.operators.mesh_tools import ViewOrbitOperator, ViewPanOperator, ViewRollOperator, ViewZoomOperator


class HEAVYPOLY_PT_main_panel(bpy.types.Panel):
    """Main Heavypoly Panel"""
    bl_label = "Heavypoly Tools"
    bl_idname = "HEAVYPOLY_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Heavypoly'

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        if layout is None:
            return

        row = layout.row()
        row.operator("heavypoly.smart_extrude")


def add_camera_section(layout: bpy.types.UILayout) -> None:
    col = layout.column(align=True)
    col.label(text="Camera Section")
    col.scale_y = 1.5

    row = col.row(align=True)

    # Numpad 7
    op = row.operator("view3d.view_axis", text="Top")
    op.type = 'TOP'

    # Numpad 1
    op = row.operator("view3d.view_axis", text="Front")
    op.type = 'FRONT'

    # Numpad 3
    op = row.operator("view3d.view_axis", text="Right")
    op.type = 'RIGHT'

    # Numpad 9
    prop: typing.Any = row.operator("view3d.view_orbit", text="Orbit Opposite")
    prop.type = 'ORBITRIGHT'
    prop.angle = pi

    # ---v
    row = col.row()
    row.operator("heavypoly.view_roll_modal")
    prop = row.operator("heavypoly.view_pan_modal",
                        icon='VIEW_PAN', text="Pan")

    # ---
    layout = col.row(align=True)
    layout.operator("view3d.zoom", text="Zoom In").delta = 1
    layout.operator("view3d.zoom", text="Zoom Out").delta = -1
    layout.operator("view3d.zoom_border", text="Zoom Region...")
    layout.operator("view3d.zoom_camera_1_to_1", text="Zoom Camera 1:1")

    # ---
    layout = col.row(align=True)
    layout.operator("view3d.fly")
    layout.operator("view3d.walk")


class HeavypolyViewMenu(bpy.types.Menu):
    """View menu for Heavypoly"""
    bl_label: typing.ClassVar[str] = "Heavypoly View Menu"
    bl_idname: typing.ClassVar[str] = "HEAVYPOLY_MT_view_menu"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context: bpy.types.Context) -> None:
        """Draw the pie menu UI.

        Args:
            context: The current Blender context
        """

        print("🟢 Draw")

        layout = self.layout
        if layout is None:
            return

        layout.emboss = 'NORMAL'
        layout.alignment = 'RIGHT'

        col = layout.column(align=True)
        col.scale_y = 1.5
        col.alignment = 'RIGHT'
        col.operator(ViewPanOperator.bl_idname, icon='VIEW_PAN')
        col.operator(ViewOrbitOperator.bl_idname, icon='SPHERE')
        col.operator(ViewZoomOperator.bl_idname, icon='VIEW_ZOOM')
        col.operator(ViewRollOperator.bl_idname, icon='MESH_CIRCLE')


class HeavypolyPieViewMenu(bpy.types.Menu):
    """Pie menu for Heavypoly"""
    bl_label = "Heavypoly Pie Menu"
    bl_idname = "HEAVYPOLY_MT_pie_view"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context: bpy.types.Context) -> None:
        """Draw the pie menu UI.

        Args:
            context: The current Blender context
        """

        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        if layout is None:
            return

        layout.emboss = 'NORMAL'
        layout.alignment = 'RIGHT'

        row = layout.row()
        col = row.column(align=True)
        col.scale_y = 1.5
        col.alignment = 'RIGHT'
        col.operator(ViewPanOperator.bl_idname, icon='VIEW_PAN')
        col.operator(ViewOrbitOperator.bl_idname, icon='SPHERE')
        col.operator(ViewZoomOperator.bl_idname, icon='VIEW_ZOOM')
        col.operator(ViewRollOperator.bl_idname, icon='MESH_CIRCLE')
        # add_camera_section(col)
        col = row.column(align=True)
        col.operator(ViewOrbitOperator.bl_idname, icon='SPHERE')
        col.operator(ViewPanOperator.bl_idname, icon='VIEW_PAN')
        col.operator(ViewZoomOperator.bl_idname, icon='VIEW_ZOOM')
        col.operator(ViewRollOperator.bl_idname, icon='MESH_CIRCLE')

        return

        pie = layout.menu_pie()
        # left
        pie.operator(ViewOrbitOperator.bl_idname, icon='SPHERE')
        # right
        pie.operator(ViewPanOperator.bl_idname, icon='VIEW_PAN')
        # bottom
        add_camera_section(pie)
        # top
        pie.operator(ViewZoomOperator.bl_idname, icon='VIEW_ZOOM')
        # top left
        pie.operator(ViewRollOperator.bl_idname, icon='MESH_CIRCLE')


# Add to __init__.py classes tuple
classes = (
    HEAVYPOLY_PT_main_panel,
    HeavypolyPieViewMenu,
    HeavypolyViewMenu,
)
