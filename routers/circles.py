from typing import Optional
from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import Circle, Member, Contribution
from schemas import CircleCreate, CircleResponse
import bmoni
import signing

router = APIRouter()
templates = Jinja2Templates(directory="templates")

class ContributionCreateBody(BaseModel):
    member_id: int

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@router.post("/api/circles", response_model=CircleResponse)
def create_circle(circle: CircleCreate, db: Session = Depends(get_db)):
    db_circle = Circle(
        name=circle.name,
        contribution_amount=circle.contribution_amount,
        member_count_target=circle.member_count_target
    )
    db.add(db_circle)
    db.commit()
    db.refresh(db_circle)
    return db_circle

@router.get("/dashboard/{circle_id}", response_class=HTMLResponse)
async def dashboard_page(request: Request, circle_id: int, member_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    circle = db.query(Circle).filter(Circle.id == circle_id).first()
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")
    
    members = db.query(Member).filter(Member.circle_id == circle_id).order_by(Member.rotation_position).all()
    transactions = db.query(Contribution).filter(Contribution.circle_id == circle_id).order_by(Contribution.id.desc()).all()
    
    total_contribs = len(transactions)
    current_cycle = (total_contribs // circle.member_count_target) + 1
    recipient_pos = ((current_cycle - 1) % circle.member_count_target) + 1
    
    current_member = None
    balance = 0.0
    if member_id:
        current_member = next((m for m in members if m.id == member_id), None)
        if current_member:
            balance = bmoni.get_balance(current_member.bmoni_user_id)
            
    return templates.TemplateResponse(
        request=request, 
        name="dashboard.html", 
        context={
            "circle": circle, 
            "members": members,
            "current_member": current_member,
            "balance": balance,
            "transactions": transactions,
            "current_cycle": current_cycle,
            "recipient_pos": recipient_pos
        }
    )

    # Removed to payments.py
