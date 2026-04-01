# this file stores brand entities
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin


class Brand(TimestampMixin, Base):
    # this model stores each luggage brand
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)

    products = relationship("Product", back_populates="brand", cascade="all, delete-orphan")
    metrics = relationship("BrandMetric", back_populates="brand", cascade="all, delete-orphan")
