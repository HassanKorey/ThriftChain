from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Circle
from schemas import CircleCreate, CircleResponse

router = APIRouter()
templates = Jinja2Templates(directory="templates")

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
