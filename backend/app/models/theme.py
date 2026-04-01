# this file stores extracted theme insights
from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin


class Theme(TimestampMixin, Base):
    # this model tracks praise and complaint themes
    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[Optional[int]] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=True, index=True)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)

    theme_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    aspect: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    mention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_sentiment: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sample_quotes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    product = relationship("Product", back_populates="themes")
