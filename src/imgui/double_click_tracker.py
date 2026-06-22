import typing

from .input_event import PointerEvent

class DoubleClickTracker:
    """
    Utility class to track double clicks
    
    example
    ```
    self.double_click = DoubleClickTracker()

    if event.event_type == EventType.POINTER_DOWN:
    
        if self.double_click.is_double_click(self.hovered_id, event):
            print("Double click detected!")
            pass

    ```
    """

    def __init__(self, double_click_time: float = 0.5):
        self.last_click_time: float | None = None
        self.last_click_pos: tuple[float, float] | None = None
        self.last_click_id: typing.Optional[str] = None
        self.double_click_time = double_click_time  # seconds
        self.double_click_distance = 5  # pixels

    def _has_previous_click(self) -> bool:
        return bool(self.last_click_time and self.last_click_pos and self.last_click_id)

    def _remember_click(self, widget_id: str | None, event: PointerEvent) -> None:
        self.last_click_time = event.timestamp
        self.last_click_pos = event.position
        self.last_click_id = widget_id

    def _matches_previous_click(self, widget_id: str | None, event: PointerEvent) -> bool:
        return (
            self.last_click_id == widget_id
            and event.timestamp - self.last_click_time < self.double_click_time
            and (
                (event.position[0] - self.last_click_pos[0]) ** 2
                + (event.position[1] - self.last_click_pos[1]) ** 2
            ) < self.double_click_distance ** 2
        )

    def is_double_click(self, widget_id: str | None, event: PointerEvent) -> bool:
        """Check if the current click is a double click"""
        if not self._has_previous_click():
            self._remember_click(widget_id, event)
            return False

        if self._matches_previous_click(widget_id, event):
            self.last_click_time = event.timestamp
            return True

        self._remember_click(widget_id, event)
        return False
