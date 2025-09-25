from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_session
from .service import get_overview_stats
from .schemas import OverviewStats

overview_router = APIRouter()

@overview_router.get("/overview", response_model=OverviewStats)
async def get_overview(
    session: AsyncSession = Depends(get_session)
) -> OverviewStats:
    try:
        return await get_overview_stats(session)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching overview statistics: {str(e)}"
        )
