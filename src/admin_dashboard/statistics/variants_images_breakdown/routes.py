from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.main import get_session
from src.admin_dashboard.statistics.variants_images_breakdown.service import get_variants_images_breakdown
from src.admin_dashboard.statistics.variants_images_breakdown.schemas import BreakdownStats

variants_images_breakdown_router = APIRouter()

@variants_images_breakdown_router.get("/variants-images", response_model=BreakdownStats)
async def get_variants_images_stats(
    db: AsyncSession = Depends(get_session)
) -> BreakdownStats:
    try:
        return await get_variants_images_breakdown(db)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch variants and images breakdown: {str(e)}"
        )
