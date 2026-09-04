import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base, declared_attr


class CustomBase:
    """Base model class with automatic tablename generation and audit timestamps."""

    @declared_attr
    def __tablename__(cls) -> str:
        # Convert CamelCase model name to lowercase plural
        name = cls.__name__.lower()
        if not name.endswith("s"):
            return f"{name}s"
        return name

    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )


Base = declarative_base(cls=CustomBase)
