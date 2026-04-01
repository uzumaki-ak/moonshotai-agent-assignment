# this file composes v1 api routers
from fastapi import APIRouter

from app.api.v1.endpoints import brands, health, insights, jobs, overview, products, reviews

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(overview.router, prefix="/overview", tags=["overview"])
api_router.include_router(brands.router, prefix="/brands", tags=["brands"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
