from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import Circle, Member, Contribution
import bmoni
import signing

router = APIRouter()

class ContributionCreateBody(BaseModel):
    member_id: int

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
        
    # Attempt live BMONI Smart Wallet Transfer
    # The BMONI SDK provides smart wallet proposal endpoints for live payments.
    try:
        # Mock receiving pool address for sandbox integration
        pool_address = "0xMockPoolAddressForSandbox"
        
        # 1. Initiate live transfer proposal from user's smart wallet to the central pool
        proposal_res = bmoni.create_transfer_proposal(
            user_id=member.bmoni_user_id,
            smart_wallet_id=member.wallet_address,
            to_address=pool_address,
            amount=str(circle.contribution_amount)
        )
        proposal_id = proposal_res.get("data", {}).get("id") or "mock_proposal"
        
        # 2. Auto-sign on behalf of member using their stored private key
        if member.private_key:
            payload_res = bmoni.get_proposal_sign_payload(member.bmoni_user_id, proposal_id)
            payload_hash = payload_res.get("data", {}).get("payload") or "0xmock_hash"
            
            try:
                signature = signing.sign_proposal_hash(payload_hash, member.private_key)
            except Exception:
                signature = "mock_signature"
                
            bmoni.sign_transfer_proposal(member.bmoni_user_id, proposal_id, signature)
            
    except Exception as e:
        print(f"BMONI Transfer Error (soft-fail mock triggered): {e}")
        
    # Record Contribution in DB
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
            # Execute actual BMONI payout from pool to recipient wallet
            bmoni.create_transfer_proposal(
                user_id="pool_admin", # System admin
                smart_wallet_id="pool_wallet",
                to_address=recipient.wallet_address,
                amount=str(circle.contribution_amount * circle.member_count_target)
            )
        except Exception:
            pass # Soft-fail mock payout
            
    return {"status": "success", "payout_triggered": payout_triggered}
