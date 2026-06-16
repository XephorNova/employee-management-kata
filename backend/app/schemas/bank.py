from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class BankDetailCreate(BaseModel):
    bank_name: str
    account_number: str
    account_type: str = "savings"
    routing_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    swift_code: Optional[str] = None
    is_primary: bool = True


class BankDetailUpdate(BaseModel):
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_type: Optional[str] = None
    routing_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    swift_code: Optional[str] = None
    is_primary: Optional[bool] = None


class BankDetailOut(BaseModel):
    id: int
    employee_id: int
    bank_name: str
    account_number: str
    account_type: str
    routing_number: Optional[str]
    ifsc_code: Optional[str]
    swift_code: Optional[str]
    is_primary: bool
    created_at: datetime
    model_config = {"from_attributes": True}
