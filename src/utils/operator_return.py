"""
Enum-like class for bpy.stub_internal.rna_enums.OperatorReturnItems
"""

import typing

OperatorReturnType = typing.Set[typing.Literal[
    'RUNNING_MODAL', # Running Modal. Keep the operator running with blender.
    'CANCELLED', # Cancelled.The operator exited without doing anything, so no undo entry should be pushed.
    'FINISHED', # Finished.The operator exited after completing its action.
    'PASS_THROUGH', # Pass Through.Do nothing and pass the event on.
    'INTERFACE' # Interface.Handled but not executed (popup menus).
]]

class OperatorReturn:
    """Enum-like class for modal return types"""
    RUNNING_MODAL: OperatorReturnType = { 'RUNNING_MODAL' }
    CANCELLED: OperatorReturnType = { 'CANCELLED' }
    FINISHED: OperatorReturnType = { 'FINISHED' }
    PASS_THROUGH: OperatorReturnType = { 'PASS_THROUGH' }
    INTERFACE: OperatorReturnType = { 'INTERFACE' }
