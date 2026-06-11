"""Products endpoints."""
from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbDep, CurrentUser
from app.models.orm import Product


router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
async def list_products(db: DbDep, _: CurrentUser):
    result = await db.execute(
        select(Product).where(Product.is_active == True).order_by(Product.sort_order)
    )
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "slug": p.slug,
            "category": p.category,
            "description": p.description,
        }
        for p in result.scalars()
    ]
