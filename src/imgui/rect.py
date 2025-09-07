class Rect(tuple[float, float, float, float]):
    """Rectangle with position and size (x, y, width, height)"""

    def __new__(cls, x: float, y: float, width: float, height: float) -> 'Rect':
        return super(Rect, cls).__new__(cls, (x, y, width, height))

    @property
    def x(self) -> float:
        """X position of the rectangle"""
        return self[0]

    @property
    def y(self) -> float:
        """Y position of the rectangle"""
        return self[1]

    @property
    def width(self) -> float:
        """Width of the rectangle"""
        return self[2]

    @property
    def height(self) -> float:
        """Height of the rectangle"""
        return self[3]

    def contains(self, x: float, y: float) -> bool:
        """Check if point is inside rectangle"""
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)

    def center(self) -> tuple[float, float]:
        """Get center point of rectangle"""
        return (self.x + self.width * 0.5, self.y + self.height * 0.5)

    def expand(self, amount: float) -> 'Rect':
        """Return expanded rectangle"""
        return Rect(
            self.x - amount,
            self.y - amount,
            self.width + amount * 2,
            self.height + amount * 2
        )

