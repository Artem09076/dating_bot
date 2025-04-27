import enum
from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Enum, Float, ForeignKey,
                        Integer, String)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.model.meta import Base


class GenderEnum(enum.Enum):
    male = "Мужской"
    female = "Женский"
    other = "Другое"


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(nullable=False)
    gender: Mapped[GenderEnum] = mapped_column(Enum(GenderEnum), nullable=False)
    city: Mapped[str] = mapped_column(nullable=True)
    interests: Mapped[str] = mapped_column(nullable=True)
    profile_filled: Mapped[bool] = mapped_column(default=False)
    photo: Mapped[str] = mapped_column(String(255))
    preferred_age_min: Mapped[int] = mapped_column()
    preferred_age_max: Mapped[int] = mapped_column()
    preferred_gender: Mapped[GenderEnum] = mapped_column(Enum(GenderEnum))
    preferred_city: Mapped[str] = mapped_column(nullable=True)

    invited_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("public.user.id"), nullable=True
    )
    invited_users = relationship("User", backref="invited_by", remote_side=[id])

    primary_rating = relationship("PrimaryRating", back_populates="user", uselist=False)
    behavior_rating = relationship(
        "BehaviorRating", back_populates="user", uselist=False
    )
    combined_rating = relationship(
        "CombinedRating", back_populates="user", uselist=False
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "age": str(self.age),
            "gender": str(self.gender.value) if self.gender else None,
            "city": self.city,
            "interests": self.interests,
            "profile_filled": self.profile_filled,
            "photo": self.photo,
            "preferred_age_min": self.preferred_age_min,
            "preferred_age_max": self.preferred_age_max,
            "preferred_gender": (
                self.preferred_gender.value if self.preferred_gender else None
            ),
            "preferred_city": self.preferred_city,
        }


class PrimaryRating(Base):
    __tablename__ = "primary_ratings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("public.user.id", ondelete="CASCADE"), unique=True
    )
    completeness_score: Mapped[float] = mapped_column(default=0.0)
    photo_score: Mapped[float] = mapped_column(default=0.0)
    preference_match_score: Mapped[float] = mapped_column(default=0.0)

    user = relationship("User", back_populates="primary_rating")


class BehaviorRating(Base):
    __tablename__ = "behavior_ratings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("public.user.id", ondelete="CASCADE"), unique=True
    )
    likes_received: Mapped[int] = mapped_column(default=0)
    likes_skipped_ratio: Mapped[float] = mapped_column(default=0.0)
    mutual_likes: Mapped[int] = mapped_column(default=0)
    post_match_conversations: Mapped[int] = mapped_column(default=0)
    active_hours_score: Mapped[float] = mapped_column(default=0.0)

    user = relationship("User", back_populates="behavior_rating")


class CombinedRating(Base):
    __tablename__ = "combined_ratings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("public.user.id", ondelete="CASCADE"), unique=True
    )
    score: Mapped[float] = mapped_column(default=0.0)

    user = relationship("User", back_populates="combined_rating")


class Like(Base):
    __tablename__ = "likes"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_user_id: Mapped[int] = mapped_column(
        ForeignKey("public.user.id", ondelete="CASCADE")
    )
    to_user_id: Mapped[int] = mapped_column(
        ForeignKey("public.user.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    is_mutual: Mapped[bool] = mapped_column(nullable=True)

    from_user = relationship("User", foreign_keys=[from_user_id])
    to_user = relationship("User", foreign_keys=[to_user_id])


class Conversation(Base):
    __tablename__ = "conversation"

    id: Mapped[int] = mapped_column(primary_key=True)
    user1_id: Mapped[int] = mapped_column(
        ForeignKey("public.user.id", ondelete="CASCADE")
    )
    user2_id: Mapped[int] = mapped_column(
        ForeignKey("public.user.id", ondelete="CASCADE")
    )
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user1 = relationship("User", foreign_keys=[user1_id])
    user2 = relationship("User", foreign_keys=[user2_id])
