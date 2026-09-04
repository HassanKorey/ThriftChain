import os
import uuid
import traceback
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt

from database import get_db
from models import User
from schemas import UserCreate, UserLogin, Token
import bmoni
import signing

router = APIRouter()
templates = Jinja2Templates(directory="templates")

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-for-ajolink-hackathon-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 1 week

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        if request.url.path.startswith("/api/"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/login"})
        
    # Remove Bearer prefix if present
    if token.startswith("Bearer "):
        token = token.split(" ")[1]
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise ValueError("Token missing sub")
        user_id = int(user_id_str)
    except Exception:
        if request.url.path.startswith("/api/"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/login"})
        
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        if request.url.path.startswith("/api/"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/login"})
    return user


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@router.get("/logout")
async def logout(response: Response):
    res = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    res.delete_cookie(key="access_token")
    return res

@router.post("/api/auth/register", response_model=Token)
def register_user(user_in: UserCreate, response: Response, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    bmoni_user_id = None
    wallet_address = None
    priv_key = None
    
    try:
        # 1. Create User
        user_res = bmoni.create_user(user_in.name, user_in.email, user_in.phone)
        bmoni_user_id = (
            user_res.get("id") or 
            user_res.get("userId") or 
            user_res.get("data", {}).get("id") or 
            user_res.get("data", {}).get("userId") or
            (user_res.get("user") or {}).get("id") or
            (user_res.get("data") and user_res["data"].get("user") and user_res["data"]["user"].get("id"))
        )
        if not bmoni_user_id:
            raise ValueError(f"Failed to parse user ID: {user_res}")
            
        # 2. Submit Dummy KYC
        address = {"street": "1 Main St", "city": "Lagos", "state": "Lagos", "country": "Nigeria"}
        bmoni.submit_kyc(bmoni_user_id, "1990-01-01", "Male", address)
        
        # 3. Owner Proof Challenge
        challenge_res = bmoni.get_owner_proof_challenge(bmoni_user_id)
        challenge_text = challenge_res.get("challenge") or challenge_res.get("data", {}).get("challenge")
        
        # 4. Sign Challenge
        priv_key, wallet_address = signing.generate_account()
        signature = signing.sign_owner_proof(challenge_text, priv_key)
        
        # 5. Create Managed Wallet
        bmoni.create_managed_wallet(bmoni_user_id, signature)
        
    except Exception as e:
        print(f"BMONI API Error on Register: {str(e)}")
        traceback.print_exc()
        if not bmoni_user_id:
            bmoni_user_id = f"mock_user_{user_in.phone.replace('+', '')}_{uuid.uuid4().hex[:4]}"
        if not priv_key:
            priv_key, wallet_address = signing.generate_account()

    hashed_pw = get_password_hash(user_in.password)
    
    new_user = User(
        name=user_in.name,
        email=user_in.email,
        phone=user_in.phone,
        password_hash=hashed_pw,
        bmoni_user_id=bmoni_user_id,
        wallet_address=wallet_address,
        private_key=priv_key
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(new_user.id)}, expires_delta=access_token_expires
    )
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/api/auth/login", response_model=Token)
def login_user(user_in: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    
    return {"access_token": access_token, "token_type": "bearer"}
