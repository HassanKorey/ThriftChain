import traceback
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Circle, User, CircleMember
from routers.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/join/{circle_slug}", response_class=HTMLResponse)
async def join_circle_page(request: Request, circle_slug: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    circle = db.query(Circle).filter(Circle.slug == circle_slug).first()
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")
    return templates.TemplateResponse(request=request, name="join.html", context={"circle": circle})

@router.post("/api/circles/{circle_slug}/join")
def join_circle(circle_slug: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    circle = db.query(Circle).filter(Circle.slug == circle_slug).first()
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")
        
    current_members_count = db.query(CircleMember).filter(CircleMember.circle_id == circle.id).count()
    if current_members_count >= circle.member_count_target:
        raise HTTPException(status_code=400, detail="Circle is already full")
        
    # Check if already joined
    existing = db.query(CircleMember).filter(CircleMember.circle_id == circle.id, CircleMember.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="You are already a member of this circle")
        
    rotation_position = current_members_count + 1

    new_member = CircleMember(
        circle_id=circle.id,
        user_id=current_user.id,
        rotation_position=rotation_position
    )
    db.add(new_member)
    db.commit()
    
    return {"status": "success", "rotation_position": rotation_position}
