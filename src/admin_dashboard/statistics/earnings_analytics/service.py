from sqlmodel import select, func, and_
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Sequence
from src.db.models import Order, OrderItem, Product
from .schemas import (
    MonthlyEarnings, DailyEarnings, WeeklyEarnings, 
    EarningsBreakdown, EarningsAnalytics,
    FinancialMetricPoint, FinancialMetricsResponse, TimeFilter
)

async def get_financial_metrics_with_time_filter(
    session: AsyncSession,
    time_filter: TimeFilter,
    selected_date: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> FinancialMetricsResponse:
    """Get financial metrics with dynamic time filtering"""
    
    # Parse dates
    base_date = datetime.now()
    if selected_date:
        try:
            base_date = datetime.strptime(selected_date, "%Y-%m-%d")
        except ValueError:
            base_date = datetime.now()
    
    # Determine date range based on filter
    if time_filter == TimeFilter.WEEK:
        # 7-day window centered on selected date
        start_date = base_date - timedelta(days=3)
        end_date = base_date + timedelta(days=3)
        period_name = f"Week of {base_date.strftime('%B %d, %Y')}"
        
    elif time_filter == TimeFilter.MONTH:
        # Full month of selected date
        start_date = base_date.replace(day=1)
        # Get last day of month
        if base_date.month == 12:
            end_date = base_date.replace(year=base_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = base_date.replace(month=base_date.month + 1, day=1) - timedelta(days=1)
        period_name = base_date.strftime('%B %Y')
        
    elif time_filter == TimeFilter.YEAR:
        # Full year of selected date
        start_date = base_date.replace(month=1, day=1)
        end_date = base_date.replace(month=12, day=31)
        period_name = str(base_date.year)
        
    elif time_filter == TimeFilter.CUSTOM:
        if not from_date or not to_date:
            raise ValueError("Custom range requires both from_date and to_date")
        try:
            start_date = datetime.strptime(from_date, "%Y-%m-%d")
            end_date = datetime.strptime(to_date, "%Y-%m-%d")
            period_name = f"{from_date} to {to_date}"
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD")
    else:
        raise ValueError(f"Invalid time filter: {time_filter}")
    
    # Get orders for the date range
    query = (
        select(Order)
        .where(
            and_(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status == 'delivered'
            )
        )
    )
    
    result = await session.exec(query)
    orders = result.all()
    
    # Calculate metrics for grouped time periods
    metrics = []
    
    if time_filter == TimeFilter.WEEK:
        # Group by day
        daily_groups = {}
        current_date = start_date
        while current_date <= end_date:
            daily_groups[current_date.date()] = []
            current_date += timedelta(days=1)
        
        for order in orders:
            order_date = order.created_at.date()
            if order_date in daily_groups:
                daily_groups[order_date].append(order)
        
        for date_key, day_orders in daily_groups.items():
            day_metrics = await calculate_day_metrics(session, day_orders)
            arabic_weekday = get_arabic_weekday(date_key.weekday())
            metrics.append(FinancialMetricPoint(
                period=arabic_weekday,
                date=date_key.strftime('%Y-%m-%d'),
                **day_metrics
            ))
    
    elif time_filter == TimeFilter.MONTH:
        # Group by day
        daily_groups = {}
        current_date = start_date
        while current_date <= end_date:
            daily_groups[current_date.date()] = []
            current_date += timedelta(days=1)
        
        for order in orders:
            order_date = order.created_at.date()
            if order_date in daily_groups:
                daily_groups[order_date].append(order)
        
        for date_key, day_orders in daily_groups.items():
            day_metrics = await calculate_day_metrics(session, day_orders)
            metrics.append(FinancialMetricPoint(
                period=f"{date_key.day}",
                date=date_key.strftime('%Y-%m-%d'),
                **day_metrics
            ))
    
    elif time_filter == TimeFilter.YEAR:
        # Group by month
        monthly_groups = {}
        for i in range(1, 13):
            monthly_groups[i] = []
        
        for order in orders:
            month = order.created_at.month
            monthly_groups[month].append(order)
        
        arabic_months = [
            'كانون الثاني', 'شباط', 'آذار', 'نيسان', 'أيار', 'حزيران',
            'تموز', 'آب', 'أيلول', 'تشرين الأول', 'تشرين الثاني', 'كانون الأول'
        ]
        
        for month, month_orders in monthly_groups.items():
            month_metrics = await calculate_day_metrics(session, month_orders)
            month_date = start_date.replace(month=month, day=1)
            metrics.append(FinancialMetricPoint(
                period=arabic_months[month - 1],
                date=month_date.strftime('%Y-%m-%d'),
                **month_metrics
            ))
    
    elif time_filter == TimeFilter.CUSTOM:
        # Determine grouping based on date range
        date_diff = (end_date - start_date).days
        
        if date_diff <= 7:
            # Group by day for short ranges
            daily_groups = {}
            current_date = start_date
            while current_date <= end_date:
                daily_groups[current_date.date()] = []
                current_date += timedelta(days=1)
            
            for order in orders:
                order_date = order.created_at.date()
                if order_date in daily_groups:
                    daily_groups[order_date].append(order)
            
            for date_key, day_orders in daily_groups.items():
                day_metrics = await calculate_day_metrics(session, day_orders)
                metrics.append(FinancialMetricPoint(
                    period=date_key.strftime('%m/%d'),
                    date=date_key.strftime('%Y-%m-%d'),
                    **day_metrics
                ))
        else:
            # Group by month for longer ranges
            monthly_groups = {}
            current_date = start_date.replace(day=1)
            while current_date <= end_date:
                month_key = current_date.strftime('%Y-%m')
                monthly_groups[month_key] = {'orders': [], 'date': current_date}
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
            
            for order in orders:
                month_key = order.created_at.strftime('%Y-%m')
                if month_key in monthly_groups:
                    monthly_groups[month_key]['orders'].append(order)
            
            for month_key, month_data in monthly_groups.items():
                month_metrics = await calculate_day_metrics(session, month_data['orders'])
                metrics.append(FinancialMetricPoint(
                    period=month_data['date'].strftime('%b %Y'),
                    date=month_data['date'].strftime('%Y-%m-%d'),
                    **month_metrics
                ))
    
    # Calculate summary for the entire period
    summary_data = await calculate_day_metrics(session, list(orders))
    profit_margin = 0.0
    if summary_data['total_revenue'] > 0:
        profit_margin = (summary_data['total_earnings'] / summary_data['total_revenue']) * 100
    
    summary = EarningsBreakdown(
        total_earnings=summary_data['total_earnings'],
        total_revenue=summary_data['total_revenue'],
        total_costs=summary_data['total_costs'],
        total_delivery_fees=summary_data['delivery_fees'],
        total_discounts=summary_data['discounts'],
        profit_margin=profit_margin
    )
    
    period_info = {
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d'),
        "period_name": period_name,
        "total_days": (end_date - start_date).days + 1
    }
    
    return FinancialMetricsResponse(
        metrics=metrics,
        time_filter=time_filter,
        summary=summary,
        period_info=period_info
    )

async def calculate_day_metrics(session: AsyncSession, orders: Sequence[Order]) -> Dict[str, Any]:
    """Calculate financial metrics for a list of orders"""
    total_revenue = 0.0
    total_costs = 0.0
    total_delivery_fees = 0.0
    total_discounts = 0.0
    orders_count = len(orders)
    
    for order in orders:
        # Add delivery fees (convert Decimal to float)
        total_delivery_fees += float(order.shipping_price or 0.0)
        
        # Add discounts (convert Decimal to float)
        total_discounts += float(order.discount or 0.0)
        
        # Add final price to revenue (convert Decimal to float)
        total_revenue += float(order.final_price or 0.0)
        
        # Get order items and calculate costs
        items_query = select(OrderItem).where(OrderItem.order_uid == order.uid)
        items_result = await session.exec(items_query)
        items = items_result.all()
        
        for item in items:
            # Get product for cost price
            product_query = select(Product).where(Product.uid == item.product_uid)
            product_result = await session.exec(product_query)
            product = product_result.first()
            
            if product:
                # Get the cost price for this product (convert Decimal to float)
                product_cost = float(product.cost_price or 0.0)
                # Calculate total cost for this item (cost * quantity)
                item_total_cost = product_cost * item.quantity
                total_costs += item_total_cost
    
    # Calculate earnings: revenue - costs - delivery_fees + discounts
    total_earnings = total_revenue - total_costs - total_delivery_fees + total_discounts
    
    return {
        'total_earnings': max(0, total_earnings),
        'total_revenue': total_revenue,
        'total_costs': total_costs,
        'delivery_fees': total_delivery_fees,
        'discounts': total_discounts,
        'orders_count': orders_count
    }

def get_arabic_weekday(weekday: int) -> str:
    """Convert weekday number to Arabic day name"""
    arabic_days = ['الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
    return arabic_days[weekday]