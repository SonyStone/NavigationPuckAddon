class UniqueID:
    """Simple unique ID generator"""
    _id = 0
    
    @classmethod
    def reset(cls) -> None:
        """Reset ID counter to zero"""
        cls._id = 0
    
    @classmethod
    def get_id(cls) -> str:
        """Return a new unique ID as a string"""
        cls._id += 1
        return str(cls._id)