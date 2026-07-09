from pydantic import BaseModel, constr
import uuid
from typing import Optional


class UserResponse(BaseModel):
    id: uuid.UUID
    email: Optional[str]
    name: Optional[str]
    username: Optional[str]

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: constr(strip_whitespace=True, min_length=1, max_length=255)
