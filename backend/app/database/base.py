from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    SQLAlchemy 2.x Declarative Base.
    All future database models will inherit from this class.
    """
    pass
