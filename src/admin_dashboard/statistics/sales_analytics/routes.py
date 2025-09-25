from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_session
from .service import get_sales_analytics
from .schemas import SalesAnalytics

sales_analytics_router = APIRouter()

@sales_analytics_router.get("/sales", response_model=SalesAnalytics)
async def get_sales_statistics(
    session: AsyncSession = Depends(get_session)
) -> SalesAnalytics:
    """
    Get sales analytics data including:
    - Yearly sales for last 12 months
    - Monthly sales for last 30 days
    - Weekly sales for last 7 days
    - Total revenue
    - Conversion rate
    """
    try:
        return await get_sales_analytics(session)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching sales analytics: {str(e)}"
        )
