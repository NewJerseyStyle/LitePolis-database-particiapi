import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class ParticiapiUser(SQLModel, table=True):
    __tablename__ = "participants"
    pid: Optional[int] = Field(default=None, primary_key=True)
    uid: int = Field(nullable=False)
    zid: int = Field(nullable=False)
    vote_count: int = Field(default=0, nullable=False)
    last_interaction: int = Field(default=0, nullable=False)
    subscribed: int = Field(default=0, nullable=False)
    last_notified: Optional[int] = Field(default=0)
    nsli: int = Field(default=0, nullable=False)
    mod: int = Field(default=0, nullable=False)
    created: int = Field(default_factory=lambda: int(datetime.datetime.now().timestamp() * 1000))

    __table_args__ = {"extend_existing": True}

# Extension table 'participants_extended'
# This table extends the core Polis participants table.
class ParticipantExtended(SQLModel, table=True):
    __tablename__ = "participants_extended"

    uid: int = Field(foreign_key="users.id", primary_key=True)
    zid: int = Field(primary_key=True)  # Assuming Foreign Key to conversations.zid (Polis table)
    referrer: Optional[str] = Field(default=None, max_length=9999)
    parent_url: Optional[str] = Field(default=None, max_length=9999)
    created: int = Field(default_factory=lambda: int(datetime.datetime.now().timestamp() * 1000))
    modified: int = Field(default_factory=lambda: int(datetime.datetime.now().timestamp() * 1000))
    subscribe_email: Optional[str] = Field(default=None, max_length=256)
    show_translation_activated: Optional[bool] = Field(default=None)
    permanent_cookie: Optional[str] = Field(default=None, max_length=32)
    origin: Optional[str] = Field(default=None, max_length=9999)

    __table_args__ = (UniqueConstraint("zid", "uid"),)

    # Relationships can be added here, e.g., linkage to User and Conversation (Polis table)
