from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_session
from .service import get_financial_metrics_with_time_filter
from .schemas import FinancialMetricsResponse, TimeFilter
from typing import Optional
from datetime import date

earnings_router = APIRouter()

@earnings_router.get("/financial-metrics", response_model=FinancialMetricsResponse)
async def get_financial_metrics(
    time_filter: TimeFilter = Query(TimeFilter.YEAR, description="Time filter period"),
    selected_date: Optional[str] = Query(None, description="Selected date for centered view (YYYY-MM-DD format)"),
    from_date: Optional[str] = Query(None, description="Start date for custom range (YYYY-MM-DD format)"),
    to_date: Optional[str] = Query(None, description="End date for custom range (YYYY-MM-DD format)"),
    session: AsyncSession = Depends(get_session)
) -> FinancialMetricsResponse:
    """
    Get financial metrics with time filtering support.
    
    Time filters:
    - WEEK: 7-day window centered on selected_date (or current date if none)
    - MONTH: Daily data for selected month or current month
    - YEAR: Monthly data for selected year or current year
    - CUSTOM: Custom date range using from_date and to_date
    """
    try:
        return await get_financial_metrics_with_time_filter(
            session=session,
            time_filter=time_filter,
            selected_date=selected_date,
            from_date=from_date,
            to_date=to_date
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching financial metrics: {str(e)}"
        )

