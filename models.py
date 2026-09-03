from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import ForeignKey, String, Float, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Circle(Base):
    __tablename__ = "circles"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    contribution_amount: Mapped[float] = mapped_column(Float)
    member_count_target: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    members: Mapped[List["Member"]] = relationship(back_populates="circle", cascade="all, delete-orphan")
    contributions: Mapped[List["Contribution"]] = relationship(back_populates="circle", cascade="all, delete-orphan")


class Member(Base):
    __tablename__ = "members"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    circle_id: Mapped[int] = mapped_column(ForeignKey("circles.id"))
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    phone: Mapped[str] = mapped_column(String)
    
    # BMONI specific fields (populated during onboarding)
    bmoni_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    wallet_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    private_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Rotation position determines who gets paid when (1, 2, 3...)
    rotation_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    circle: Mapped["Circle"] = relationship(back_populates="members")
    contributions: Mapped[List["Contribution"]] = relationship(back_populates="member", cascade="all, delete-orphan")


class Contribution(Base):
    __tablename__ = "contributions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    circle_id: Mapped[int] = mapped_column(ForeignKey("circles.id"))
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    
    amount: Mapped[float] = mapped_column(Float)
    cycle_number: Mapped[int] = mapped_column(Integer)
    
    # BMONI proposal ID for the transfer
    proposal_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, completed
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    circle: Mapped["Circle"] = relationship(back_populates="contributions")
    member: Mapped["Member"] = relationship(back_populates="contributions")
