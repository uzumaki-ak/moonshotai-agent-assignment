# this file exports all model modules for metadata registration
from app.models.brand import Brand
from app.models.insight import Insight
from app.models.job import PipelineJob
from app.models.metric import BrandMetric
from app.models.product import Product
from app.models.review import Review
from app.models.theme import Theme

__all__ = [
    "Brand",
    "Product",
    "Review",
    "BrandMetric",
    "Theme",
    "PipelineJob",
    "Insight",
]
