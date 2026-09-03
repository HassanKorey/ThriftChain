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

@router.post("/api/circles/{circle_id}/contribute")
def make_contribution(circle_id: int, req: ContributionCreateBody, db: Session = Depends(get_db)):
    circle = db.query(Circle).filter(Circle.id == circle_id).first()
    member = db.query(Member).filter(Member.id == req.member_id, Member.circle_id == circle_id).first()
    if not circle or not member:
        raise HTTPException(status_code=404, detail="Not found")
        
    total_contribs = db.query(Contribution).filter(Contribution.circle_id == circle_id).count()
    current_cycle = (total_contribs // circle.member_count_target) + 1
    
    # Check if already paid for current cycle
    existing = db.query(Contribution).filter(
        Contribution.circle_id == circle_id, 
        Contribution.member_id == member.id,
        Contribution.cycle_number == current_cycle
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="You have already contributed for this cycle.")
        
    # Attempt BMONI Smart Wallet Transfer (soft fallback for demo)
    try:
        # Mock receiving pool address for sandbox
        pool_address = "0xMockPoolAddressForSandbox"
        proposal_res = bmoni.create_transfer_proposal(
            user_id=member.bmoni_user_id,
            smart_wallet_id=member.wallet_address,
            to_address=pool_address,
            amount=str(circle.contribution_amount)
        )
        proposal_id = proposal_res.get("data", {}).get("id") or "mock_proposal"
        
        # Auto-sign on behalf of member using their stored private key (Agentic flow)
        if member.private_key:
            payload_res = bmoni.get_proposal_sign_payload(member.bmoni_user_id, proposal_id)
            payload_hash = payload_res.get("data", {}).get("payload") or "0xmock_hash"
            
            # Use the correct signing function for proposals (no EIP-191 prefix)
            try:
                signature = signing.sign_proposal_hash(payload_hash, member.private_key)
            except Exception:
                signature = "mock_signature"
                
            bmoni.sign_transfer_proposal(member.bmoni_user_id, proposal_id, signature)
            
    except Exception as e:
        print(f"BMONI Transfer Error ignored for demo continuity: {e}")
        
    # Record Contribution
    contrib = Contribution(
        member_id=member.id,
        circle_id=circle.id,
        amount=circle.contribution_amount,
        status="paid",
        cycle_number=current_cycle
    )
    db.add(contrib)
    db.commit()
    
    # Check if the Pot is full for this cycle!
    cycle_contribs = db.query(Contribution).filter(
        Contribution.circle_id == circle_id,
        Contribution.cycle_number == current_cycle
    ).count()
    
    payout_triggered = False
    if cycle_contribs >= circle.member_count_target:
        payout_triggered = True
        recipient_pos = ((current_cycle - 1) % circle.member_count_target) + 1
        recipient = db.query(Member).filter(
            Member.circle_id == circle_id, 
            Member.rotation_position == recipient_pos
        ).first()
        
        print(f"🎉 PAYOUT TRIGGERED! Pot size: ₦{circle.contribution_amount * circle.member_count_target}")
        print(f"--> Payout executing to: {recipient.name} ({recipient.wallet_address})")
        
        try:
            # We would simulate a smart contract payout here from the pool to the recipient
            bmoni.create_transfer_proposal(
                user_id="pool_admin", # Mock
                smart_wallet_id="pool_wallet",
                to_address=recipient.wallet_address,
                amount=str(circle.contribution_amount * circle.member_count_target)
            )
        except Exception:
            pass # Ignoring mock payout failure
            
    return {"status": "success", "payout_triggered": payout_triggered}
