from sqlalchemy import TypeDecorator, String
from enum import Enum

class CaseInsensitiveEnum(TypeDecorator):
    """Case-insensitive enum type for SQLAlchemy"""
    impl = String(50)

    def __init__(self, enum_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enum_type = enum_type

    def process_bind_param(self, value, dialect):
        if value is not None:
            # Handle enum instances
            if isinstance(value, Enum):
                value = value.value
            # Convert to lowercase string for consistency
            if isinstance(value, str):
                value = value.lower()
            return str(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return self.enum_type(value.lower())
            except ValueError:
                return None
        return None
