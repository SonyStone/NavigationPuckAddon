"""Built-in rectangle and outline geometry data."""


class OutlineVertices(list[
    tuple[float, float]
]):
    """
    Outline thickness for each side

    - outline_width = 0
    - vertices = 8 (2 floats x 8 vertices)

    `Y` - to-top `X` - to-right

    ```
    y
    ↑
    0 → x
    ```

    counter-clockwise (CCW)

    outer 
    ```
    3 ————— 2
    | 7 — 6 |
    | |   | |
    | 4 — 5 |
    0 ————— 1
    ```
    """

    def __init__(self, rect: tuple[float, float, float, float], outline_width: float) -> None:
        x, y, width, height = rect
        outer = (
            (x, y),
            (x + width, y),
            (x + width, y + height),
            (x, y + height),
        )

        inner = (
            (x + outline_width, y + outline_width),
            (x + width - outline_width, y + outline_width),
            (x + width - outline_width, y + height - outline_width),
            (x + outline_width, y + height - outline_width),
        )

        merge = (
            outer[0],
            outer[1],
            inner[1],
            inner[0],
            outer[2],
            outer[3],
            inner[3],
            inner[2],
        )

        super().__init__(merge)


class OutlineIndices(list[
    tuple[int, int, int]
]):
    """
    Outline indices for each side

    - indices = 24 (3 int x 8 triangles)
    - offset size = 8 (4 outer + 4 inner)
    """

    def __init__(self, offset: int = 0) -> None:

        indices = (
            # Bottom
            (0 + offset, 1 + offset, 2 + offset),
            (2 + offset, 3 + offset, 0 + offset),
            # Right
            (1 + offset, 4 + offset, 7 + offset),
            (7 + offset, 2 + offset, 1 + offset),
            # Top
            (4 + offset, 5 + offset, 6 + offset),
            (6 + offset, 7 + offset, 4 + offset),
            # Left
            (0 + offset, 3 + offset, 6 + offset),
            (6 + offset, 5 + offset, 0 + offset)
        )

        super().__init__(indices)

    @staticmethod
    def offset_size() -> int:
        """offset size is 8 (4 outer + 4 inner)"""
        return 8


class RectangleVertices(list[
    tuple[float, float],
]):
    """
    Fill rectangle
    
    - vertices = 4 (2 floats x 4 vertices)
    - outline_width = border
    """

    def __init__(self, rect: tuple[float, float, float, float] = (0, 0, 1, 1), border: float = 0) -> None:
        x, y, width, height = rect

        value = [
            (x + border, y + border),
            (x + width - border, y + border),
            (x + width - border, y + height - border),
            (x + border, y + height - border),
        ]
        super().__init__(value)


class RectangleIndices(list[
    tuple[int, int, int]
]):
    """
    Fill rectangle indices

    - indices = 6 (3 int x 2 triangles)
    - offset size = 4
    """

    def __init__(self, offset: int = 0) -> None:
        indices = (
            (0 + offset, 1 + offset, 2 + offset), (2 + offset, 3 + offset, 0 + offset)
        )
        super().__init__(indices)

    @staticmethod
    def offset_size() -> int:
        """offset size is 4"""
        return 4
