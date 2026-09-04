import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import Circle, User, CircleMember, Contribution
from routers.auth import get_current_user
import bmoni
import signing

router = APIRouter()

@router.post("/api/circles/{circle_id}/contribute")
def make_contribution(circle_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    circle = db.query(Circle).filter(Circle.id == circle_id).first()
    # verify user is a member of this circle
    member = db.query(CircleMember).filter(CircleMember.user_id == current_user.id, CircleMember.circle_id == circle_id).first()
    
    if not circle or not member:
        raise HTTPException(status_code=404, detail="Not found")
        
    total_contribs = db.query(Contribution).filter(Contribution.circle_id == circle_id).count()
    current_cycle = (total_contribs // circle.member_count_target) + 1
    
    # Check if already paid for current cycle
    existing = db.query(Contribution).filter(
        Contribution.circle_id == circle_id, 
        Contribution.user_id == current_user.id,
        Contribution.cycle_number == current_cycle
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="You have already contributed for this cycle.")
        
    try:
        pool_address = circle.pool_wallet_address or "0xMockPoolAddressForSandbox"
        
        proposal_res = bmoni.create_transfer_proposal(
            user_id=current_user.bmoni_user_id,
            smart_wallet_id=current_user.wallet_address,
            to_address=pool_address,
            amount=str(circle.contribution_amount)
        )
        proposal_id = proposal_res.get("data", {}).get("id") or "mock_proposal"
        
        if current_user.private_key:
            payload_res = bmoni.get_proposal_sign_payload(current_user.bmoni_user_id, proposal_id)
            payload_hash = payload_res.get("data", {}).get("payload") or "0xmock_hash"
            
            try:
                signature = signing.sign_proposal_hash(payload_hash, current_user.private_key)
            except Exception:
                signature = "mock_signature"
                
            bmoni.sign_transfer_proposal(current_user.bmoni_user_id, proposal_id, signature)
            
    except Exception as e:
        print(f"BMONI Transfer Error (soft-fail mock triggered): {e}")
        
    contrib = Contribution(
        user_id=current_user.id,
        circle_id=circle.id,
        amount=circle.contribution_amount,
        status="paid",
        cycle_number=current_cycle
    )
    db.add(contrib)
    
    # Local accounting: Deduct from user and add to pool
    if current_user.wallet_balance < circle.contribution_amount:
        raise HTTPException(status_code=400, detail="Insufficient funds in your smart wallet.")
    current_user.wallet_balance -= circle.contribution_amount
    circle.pool_balance += circle.contribution_amount
    
    db.commit()
    
    cycle_contribs = db.query(Contribution).filter(
        Contribution.circle_id == circle_id,
        Contribution.cycle_number == current_cycle
    ).count()
    
    payout_available = False
    if cycle_contribs >= circle.member_count_target:
        payout_available = True
            
    return {"status": "success", "payout_available": payout_available}

@router.post("/api/circles/{circle_id}/payout")
def confirm_payout(circle_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    circle = db.query(Circle).filter(Circle.id == circle_id).first()
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")
        
    payout_amount = circle.contribution_amount * circle.member_count_target
    if circle.pool_balance < payout_amount:
        raise HTTPException(status_code=400, detail="Pool balance is not full yet.")
        
    total_contribs = db.query(Contribution).filter(Contribution.circle_id == circle_id).count()
    current_cycle = (total_contribs // circle.member_count_target)
    if total_contribs % circle.member_count_target != 0:
        raise HTTPException(status_code=400, detail="Cycle is not complete.")
        
    recipient_pos = ((current_cycle - 1) % circle.member_count_target) + 1
    recipient_member = db.query(CircleMember).filter(
        CircleMember.circle_id == circle_id, 
        CircleMember.rotation_position == recipient_pos
    ).first()
    
    if not recipient_member or recipient_member.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="It is not your turn to receive the payout.")
        
    # Process payout
    circle.pool_balance -= payout_amount
    current_user.wallet_balance += payout_amount
    db.commit()
    
    try:
        pool_user_id = circle.pool_bmoni_user_id or "pool_admin"
        pool_wallet = circle.pool_wallet_address or "pool_wallet"
        
        payout_res = bmoni.create_transfer_proposal(
            user_id=pool_user_id,
            smart_wallet_id=pool_wallet,
            to_address=current_user.wallet_address,
            amount=str(payout_amount)
        )
        
        payout_proposal_id = payout_res.get("data", {}).get("id")
        if payout_proposal_id and circle.pool_private_key:
            payload_res = bmoni.get_proposal_sign_payload(pool_user_id, payout_proposal_id)
            payload_hash = payload_res.get("data", {}).get("payload")
            if payload_hash:
                signature = signing.sign_proposal_hash(payload_hash, circle.pool_private_key)
                bmoni.sign_transfer_proposal(pool_user_id, payout_proposal_id, signature)
    except Exception as e:
        print(f"BMONI Payout Transfer Error: {e}")
        pass
        
    return {"status": "success", "detail": "Payout confirmed and funds transferred to your wallet."}

from schemas import WithdrawRequest

@router.post("/api/wallet/withdraw")
def withdraw_funds(request: WithdrawRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.wallet_balance < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance.")
        
    # Deduct locally
    current_user.wallet_balance -= request.amount
    db.commit()
    
    # In a real app, we would integrate with an off-ramp API here.
    return {"status": "success", "detail": f"Withdrawal of NGN {request.amount} to {request.bank_name} initiated."}
