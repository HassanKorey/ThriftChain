from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CircleCreate(BaseModel):
    name: str
    contribution_amount: float
    member_count_target: int
    frequency: str
    contribution_day: str

class CircleResponse(BaseModel):
    id: int
    name: str
    slug: str
    contribution_amount: float
    member_count_target: int
    frequency: str
    contribution_day: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    name: str
    email: str
    phone: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class WithdrawRequest(BaseModel):
    amount: float
    bank_name: str
    account_number: str
