class MyCustomProperties(bpy.types.PropertyGroup):
    my_string: bpy.props.StringProperty(
        name="My String",
        description="A custom string property",
        default="Hello, Blender!"
    )
    
    my_int: bpy.props.IntProperty(
        name="My Integer",
        description="A custom integer property",
        default=42,
        min=0,
        max=100
    )
    
    my_float: bpy.props.FloatProperty(
        name="My Float",
        description="A custom float property",
        default=3.14,
        min=0.0,
        max=10.0
    )

def register():
    bpy.utils.register_class(MyCustomProperties)
    bpy.types.Scene.my_custom_properties = bpy.props.PointerProperty(type=MyCustomProperties)

def unregister():
    del bpy.types.Scene.my_custom_properties
    bpy.utils.unregister_class(MyCustomProperties)