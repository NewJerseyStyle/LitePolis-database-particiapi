import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ParticiapiIssuer(SQLModel, table=True):
    issid: Optional[int] = Field(default=None, primary_key=True)
    issuer: str = Field(nullable=False, unique=True)
    modified: int = Field(default_factory=lambda: int(datetime.datetime.now().timestamp() * 1000))
    created: int = Field(default_factory=lambda: int(datetime.datetime.now().timestamp() * 1000))
