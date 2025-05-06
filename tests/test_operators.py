import unittest
import bpy

class TestSmartExtrude(unittest.TestCase):
    
    def setUp(self):
        # Create a test mesh
        bpy.ops.mesh.primitive_cube_add()
        self.test_object = bpy.context.object
    
    def test_smart_extrude_runs(self):
        # Switch to edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        
        # Test the operator
        result = bpy.ops.heavypoly.smart_extrude()
        
        # Check if it executed successfully
        self.assertEqual(result, {'FINISHED'})
    
    def tearDown(self):
        # Clean up
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.delete()

# To run tests:
# blender --background --python tests/test_operators.py
