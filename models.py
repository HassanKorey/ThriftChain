from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import ForeignKey, String, Float, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Circle(Base):
    __tablename__ = "circles"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String, index=True)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    contribution_amount: Mapped[float] = mapped_column(Float)
    member_count_target: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Pool Wallet fields for BMONI
    pool_bmoni_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pool_wallet_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pool_private_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    admin: Mapped["User"] = relationship(back_populates="circles_admin")
    members: Mapped[List["CircleMember"]] = relationship(back_populates="circle", cascade="all, delete-orphan")
    contributions: Mapped[List["Contribution"]] = relationship(back_populates="circle", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    phone: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column(String)
    
    # BMONI specific fields (populated during onboarding)
    bmoni_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    wallet_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    private_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    circles_admin: Mapped[List["Circle"]] = relationship(back_populates="admin")
    circle_memberships: Mapped[List["CircleMember"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    contributions: Mapped[List["Contribution"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class CircleMember(Base):
    __tablename__ = "circle_members"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    circle_id: Mapped[int] = mapped_column(ForeignKey("circles.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    # Rotation position determines who gets paid when (1, 2, 3...)
    rotation_position: Mapped[int] = mapped_column(Integer)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    circle: Mapped["Circle"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="circle_memberships")


class Contribution(Base):
    __tablename__ = "contributions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    circle_id: Mapped[int] = mapped_column(ForeignKey("circles.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    amount: Mapped[float] = mapped_column(Float)
    cycle_number: Mapped[int] = mapped_column(Integer)
    
    # BMONI proposal ID for the transfer
    proposal_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, completed
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    circle: Mapped["Circle"] = relationship(back_populates="contributions")
    user: Mapped["User"] = relationship(back_populates="contributions")
