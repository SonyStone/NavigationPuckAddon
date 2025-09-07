"""
Defines the DrawCommand protocol
"""
import typing

@typing.runtime_checkable
class DrawProtocol(typing.Protocol):
    """Protocol for draw commands"""

    def draw(self) -> None:
        """Execute the draw command"""

@typing.runtime_checkable
class UnwrapProtocol(typing.Protocol):
    """Protocol for commands that can be unwrapped into another command"""

    def unwrap(self) -> DrawProtocol:  # type: ignore
        """Unwrap the command into another draw command"""
