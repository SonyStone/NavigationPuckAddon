class MyOperator(bpy.types.Operator):
    bl_idname = "heavypoly_addon.my_operator"
    bl_label = "My Operator"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Implement the functionality of the operator here
        self.report({'INFO'}, "My Operator executed")
        return {'FINISHED'}