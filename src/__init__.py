# File: /my_blender_addon/my_blender_addon/src/__init__.py

bl_info = {
    "name": "My Blender Addon",
    "blender": (2, 82, 0),
    "category": "Object",
}

import bpy
from .operators import MyOperator
from .panels import MyPanel
from .properties import MyProperties

def register():
    bpy.utils.register_class(MyOperator)
    bpy.utils.register_class(MyPanel)
    MyProperties.register()

def unregister():
    bpy.utils.unregister_class(MyOperator)
    bpy.utils.unregister_class(MyPanel)
    MyProperties.unregister()

if __name__ == "__main__":
    register()