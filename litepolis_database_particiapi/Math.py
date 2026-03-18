import datetime
from typing import Optional, Dict, Any

from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB

class MathMain(SQLModel, table=True):
    __tablename__ = "math_main"

    zid: Optional[int] = Field(default=None, primary_key=True) # Foreign Key to conversations.id
    data: str = Field(nullable=False) # JSON string
    last_vote_timestamp: int = Field(nullable=False)
    modified: int = Field(default_factory=lambda: int(datetime.datetime.now().timestamp() * 1000))