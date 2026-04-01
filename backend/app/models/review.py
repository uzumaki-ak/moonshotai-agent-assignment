# this file stores product review rows
from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin


class Review(TimestampMixin, Base):
    # this model stores each scraped review
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)

    review_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    review_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    verified_purchase: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    helpful_votes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    product = relationship("Product", back_populates="reviews")
