import traceback
import uuid
import re
import string
import random
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import Circle, User, CircleMember, Contribution
from schemas import CircleCreate, CircleResponse
from routers.auth import get_current_user
import bmoni
import signing

router = APIRouter()
templates = Jinja2Templates(directory="templates")

class ContributionCreateBody(BaseModel):
    member_id: int

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request=request, name="index.html")

@router.post("/api/circles", response_model=CircleResponse)
def create_circle(circle: CircleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    base_slug = re.sub(r'[^a-z0-9\-]', '', circle.name.lower().replace(' ', '-'))
    base_slug = re.sub(r'-+', '-', base_slug).strip('-')
    if not base_slug:
        base_slug = "circle"
        
    slug = base_slug
    while db.query(Circle).filter(Circle.slug == slug).first():
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=3))
        slug = f"{base_slug}-{suffix}"

    db_circle = Circle(
        admin_id=current_user.id,
        name=circle.name,
        slug=slug,
        contribution_amount=circle.contribution_amount,
        member_count_target=circle.member_count_target
    )
    
    # Add creator as the first member
    db_circle.members.append(CircleMember(user_id=current_user.id, rotation_position=1))
    
    # Provision Pool Wallet for the Circle
    try:
        pool_email = f"pool_{uuid.uuid4().hex[:8]}@ajochain.local"
        user_res = bmoni.create_user(f"Circle {circle.name}", pool_email, "+2340000000000")
        bmoni_user_id = (
            user_res.get("id") or 
            user_res.get("userId") or 
            user_res.get("data", {}).get("id") or 
            user_res.get("data", {}).get("userId")
        )
        if bmoni_user_id:
            # Dummy KYC
            bmoni.submit_kyc(bmoni_user_id, "1990-01-01", "Male", {"street": "Pool St", "city": "Lagos", "state": "Lagos", "country": "Nigeria"})
            # Challenge & Sign
            challenge_res = bmoni.get_owner_proof_challenge(bmoni_user_id)
            challenge_text = challenge_res.get("challenge") or challenge_res.get("data", {}).get("challenge")
            priv_key, wallet_address = signing.generate_account()
            signature = signing.sign_owner_proof(challenge_text, priv_key)
            # Create Managed Wallet
            bmoni.create_managed_wallet(bmoni_user_id, signature)
            
            db_circle.pool_bmoni_user_id = bmoni_user_id
            db_circle.pool_wallet_address = wallet_address
            db_circle.pool_private_key = priv_key
    except Exception as e:
        print(f"Error provisioning pool wallet: {e}")
        traceback.print_exc()
        # Fallback to mock for sandbox testing
        priv_key, wallet_address = signing.generate_account()
        db_circle.pool_bmoni_user_id = f"mock_pool_{uuid.uuid4().hex[:8]}"
        db_circle.pool_wallet_address = wallet_address
        db_circle.pool_private_key = priv_key

    db.add(db_circle)
    db.commit()
    db.refresh(db_circle)
    return db_circle

@router.delete("/api/circles/{circle_id}")
def delete_circle(circle_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    circle = db.query(Circle).filter(Circle.id == circle_id).first()
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")
        
    if circle.admin_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the circle admin can delete the circle")
        
    db.delete(circle)
    db.commit()
    
    return {"status": "success", "detail": "Circle deleted successfully"}

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    balance = current_user.wallet_balance
    memberships = db.query(CircleMember).filter(CircleMember.user_id == current_user.id).all()
    
    return templates.TemplateResponse(
        request=request, 
        name="dashboard.html", 
        context={
            "current_user": current_user,
            "balance": balance,
            "memberships": memberships
        }
    )

    # Removed to payments.py
