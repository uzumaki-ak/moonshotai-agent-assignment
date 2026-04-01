# this file stores brand level computed metrics
from datetime import date
from typing import Optional

from sqlalchemy import Date, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin


class BrandMetric(TimestampMixin, Base):
    # this model keeps daily benchmark metrics per brand
    __tablename__ = "brand_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    avg_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_discount_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_reviews: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    premium_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value_for_money: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    brand = relationship("Brand", back_populates="metrics")
