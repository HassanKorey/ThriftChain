from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CircleCreate(BaseModel):
    name: str
    contribution_amount: float
    member_count_target: int

class CircleResponse(BaseModel):
    id: int
    name: str
    contribution_amount: float
    member_count_target: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class MemberCreate(BaseModel):
    name: str
    email: str
    phone: str
    bvn: str
    dob: str
    gender: str
    street: str
    city: str
    state: str
    country: str

class MemberResponse(BaseModel):
    id: int
    circle_id: int
    name: str
    bmoni_user_id: Optional[str]
    wallet_address: Optional[str]
    rotation_position: Optional[int]
    joined_at: datetime
    
    class Config:
        from_attributes = True
