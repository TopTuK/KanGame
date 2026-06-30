from pydantic import BaseModel
import uuid
from typing import Optional


class UserResponse(BaseModel):
    id: uuid.UUID
    email: Optional[str]
    name: Optional[str]

    class Config:
        from_attributes = True
