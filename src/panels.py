class MyPanel(bpy.types.Panel):
    bl_label = "My Panel"
    bl_idname = "PT_MyPanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Hello, Blender Addon!")
        # Add more UI elements here as needed

def register():
    bpy.utils.register_class(MyPanel)

def unregister():
    bpy.utils.unregister_class(MyPanel)