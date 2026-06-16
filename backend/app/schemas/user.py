from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole
    employee_id: Optional[int] = None


class UserUpdate(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    employee_id: Optional[int] = None


class UserOut(BaseModel):
    id: int
    email: str
    role: UserRole
    employee_id: Optional[int]
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}
