from typing import Optional

from sqlmodel import Field, SQLModel

class NotificationTasks(SQLModel, table=True):
    __tablename__ = "notification_tasks"

    zid: int = Field(primary_key=True) # Foreign Key to conversations.id
    modified: Optional[int] = Field(default=None)

