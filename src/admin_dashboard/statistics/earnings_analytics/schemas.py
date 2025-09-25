from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

class TimeFilter(str, Enum):
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    CUSTOM = "custom"

class EarningsPeriod(BaseModel):
    orders: int
    revenue: float
    costs: float
    delivery_fees: float
    discounts: float
    earnings: float

class MonthlyEarnings(EarningsPeriod):
    month: int

class DailyEarnings(EarningsPeriod):
    day: int

class WeeklyEarnings(EarningsPeriod):
    day_of_week: str

class EarningsBreakdown(BaseModel):
    total_earnings: float
    total_revenue: float
    total_costs: float
    total_delivery_fees: float
    total_discounts: float
    profit_margin: float  # earnings / revenue * 100

class EarningsAnalytics(BaseModel):
    yearly_earnings: List[MonthlyEarnings]
    monthly_earnings: List[DailyEarnings]
    weekly_earnings: List[WeeklyEarnings]
    breakdown: EarningsBreakdown

# New schemas for financial metrics chart
class FinancialMetricPoint(BaseModel):
    period: str  # The time period label (e.g., "January", "15 Jan", "Monday")
    date: str    # The actual date (YYYY-MM-DD format)
    total_earnings: float
    total_revenue: float
    total_costs: float
    delivery_fees: float
    discounts: float
    orders_count: int

class FinancialMetricsResponse(BaseModel):
    metrics: List[FinancialMetricPoint]
    time_filter: TimeFilter
    summary: EarningsBreakdown
    period_info: dict  # Contains info about the time period (start_date, end_date, period_name)

