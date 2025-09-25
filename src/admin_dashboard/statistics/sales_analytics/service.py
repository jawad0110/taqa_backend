from sqlmodel import select, func, and_, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from typing import List, Tuple
from src.db.models import Order, OrderItem, Product
from .schemas import MonthlySales, DailySales, WeeklySales, SalesAnalytics, TopSellingProduct

async def get_yearly_sales(session: AsyncSession) -> List[MonthlySales]:
    """Get sales data for the last 12 months"""
    twelve_months_ago = datetime.now() - timedelta(days=365)
    
    # Get all delivered orders from the last 12 months
    query = (
        select(Order)
        .where(
            and_(
                Order.created_at >= twelve_months_ago,
                Order.status == 'delivered'
            )
        )
    )
    
    result = await session.execute(query)
    orders = result.scalars().all()
    
    # Group orders by month
    monthly_data = {}
    for order in orders:
        month = order.created_at.month
        if month not in monthly_data:
            monthly_data[month] = {'orders': 0, 'revenue': 0.0}
        monthly_data[month]['orders'] += 1
        monthly_data[month]['revenue'] += float(order.final_price or 0)
    
    # Convert to MonthlySales objects
    return [
        MonthlySales(
            month=month,
            orders=data['orders'],
            revenue=data['revenue']
        )
        for month, data in sorted(monthly_data.items())
    ]

async def get_monthly_sales(session: AsyncSession) -> List[DailySales]:
    """Get sales data for the last 30 days"""
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # Get all delivered orders from the last 30 days
    query = (
        select(Order)
        .where(
            and_(
                Order.created_at >= thirty_days_ago,
                Order.status == 'delivered'
            )
        )
    )
    
    result = await session.execute(query)
    orders = result.scalars().all()
    
    # Group orders by day
    daily_data = {}
    for order in orders:
        day = order.created_at.day
        if day not in daily_data:
            daily_data[day] = {'orders': 0, 'revenue': 0.0}
        daily_data[day]['orders'] += 1
        daily_data[day]['revenue'] += float(order.final_price or 0)
    
    # Convert to DailySales objects
    return [
        DailySales(
            day=day,
            orders=data['orders'],
            revenue=data['revenue']
        )
        for day, data in sorted(daily_data.items())
    ]

async def get_weekly_sales(session: AsyncSession) -> List[WeeklySales]:
    """Get sales data for the last 7 days"""
    seven_days_ago = datetime.now() - timedelta(days=7)
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Get all delivered orders from the last 7 days
    query = (
        select(Order)
        .where(
            and_(
                Order.created_at >= seven_days_ago,
                Order.status == 'delivered'
            )
        )
    )
    
    result = await session.execute(query)
    orders = result.scalars().all()
    
    # Group orders by day of week
    weekly_data = {}
    for order in orders:
        day_of_week = order.created_at.weekday()  # 0 = Monday, 6 = Sunday
        day_name = days_of_week[day_of_week]
        if day_name not in weekly_data:
            weekly_data[day_name] = {'orders': 0, 'revenue': 0.0}
        weekly_data[day_name]['orders'] += 1
        weekly_data[day_name]['revenue'] += float(order.final_price or 0)
    
    # Convert to WeeklySales objects, ensure all days are included
    return [
        WeeklySales(
            day_of_week=day_name,
            orders=weekly_data.get(day_name, {'orders': 0, 'revenue': 0.0})['orders'],
            revenue=weekly_data.get(day_name, {'orders': 0, 'revenue': 0.0})['revenue']
        )
        for day_name in days_of_week
    ]

async def get_total_revenue(session: AsyncSession) -> float:
    """Get total revenue from all completed orders"""
    query = (
        select(func.sum(Order.final_price))
        .where(Order.status == 'delivered')
    )
    result = await session.execute(query)
    return float(result.scalar() or 0)

async def get_conversion_rate(session: AsyncSession) -> float:
    """Calculate conversion rate: delivered_orders / total_orders"""
    delivered_orders_query = (
        select(func.count())
        .select_from(Order)
        .where(Order.status == 'delivered')
    )
    total_orders_query = select(func.count()).select_from(Order)
    
    delivered_orders = await session.execute(delivered_orders_query)
    total_orders = await session.execute(total_orders_query)
    
    delivered_orders_count = delivered_orders.scalar() or 0
    total_orders_count = total_orders.scalar() or 0
    
    return delivered_orders_count / total_orders_count if total_orders_count > 0 else 0

async def get_top_selling_products(session: AsyncSession, limit: int = 10) -> List[TopSellingProduct]:
    """Get top selling products by quantity sold"""
    # Get all delivered orders with their items - use a simpler approach
    delivered_orders_query = (
        select(Order)
        .where(Order.status == 'delivered')
    )
    
    result = await session.execute(delivered_orders_query)
    delivered_orders = result.scalars().all()
    
    # Track product sales
    product_sales = {}
    
    for order in delivered_orders:
        # Get order items for each order
        items_query = select(OrderItem).where(OrderItem.order_uid == order.uid)
        items_result = await session.execute(items_query)
        items = items_result.scalars().all()
        
        for item in items:
            product_uid = str(item.product_uid)
            if product_uid not in product_sales:
                product_sales[product_uid] = 0
            product_sales[product_uid] += item.quantity
    
    # Sort by sales and get top products
    sorted_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    # Get product details for the top selling products
    top_products = []
    for product_uid, total_sold in sorted_products:
        product_query = select(Product).where(Product.uid == product_uid)
        product_result = await session.execute(product_query)
        product = product_result.scalar_one_or_none()
        
        if product:
            top_products.append(TopSellingProduct(
                id=str(product.uid),
                name=product.title,
                price=float(product.price or 0),
                stock=int(product.stock or 0),
                is_active=bool(product.is_active),
                sales=int(total_sold)
            ))
    
    return top_products

async def get_sales_analytics(session: AsyncSession) -> SalesAnalytics:
    """Get complete sales analytics data"""
    yearly_sales = await get_yearly_sales(session)
    monthly_sales = await get_monthly_sales(session)
    weekly_sales = await get_weekly_sales(session)
    total_revenue = await get_total_revenue(session)
    conversion_rate = await get_conversion_rate(session)
    top_selling_products = await get_top_selling_products(session)
    
    return SalesAnalytics(
        yearly_sales=yearly_sales,
        monthly_sales=monthly_sales,
        weekly_sales=weekly_sales,
        total_revenue=total_revenue,
        conversion_rate=conversion_rate,
        top_selling_products=top_selling_products
    )