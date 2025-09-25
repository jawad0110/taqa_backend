from sqlmodel import select, func, and_
from sqlmodel.ext.asyncio.session import AsyncSession
import os
from pathlib import Path
from src.db.models import Product, Order, User, OrderItem
from .schemas import OverviewStats

async def calculate_earnings(session: AsyncSession) -> dict:
    """Calculate earnings based on the formula: 
    total_earnings = sum(product_price - product_cost) - delivery_fees - discounts"""
    try:
        # Get all delivered orders with their items
        delivered_orders_query = select(Order).where(Order.status == 'delivered')
        delivered_orders_result = await session.exec(delivered_orders_query)
        delivered_orders = delivered_orders_result.all()
        
        total_revenue = 0.0
        total_costs = 0.0
        total_delivery_fees = 0.0
        total_discounts = 0.0
        
        for order in delivered_orders:
            # Add delivery fees (convert Decimal to float)
            total_delivery_fees += float(order.shipping_price or 0.0)
            
            # Add discounts (convert Decimal to float)
            total_discounts += float(order.discount or 0.0)
            
            # Add final price to revenue (convert Decimal to float)
            total_revenue += float(order.final_price or 0.0)
            
            # Calculate costs for each order item
            for item in order.items:
                if item.product:
                    # Get the cost price for this product (convert Decimal to float)
                    product_cost = float(item.product.cost_price or 0.0)
                    # Calculate total cost for this item (cost * quantity)
                    item_total_cost = product_cost * item.quantity
                    total_costs += item_total_cost
        
        # Calculate earnings: revenue - costs - delivery_fees - discounts
        # Note: revenue already includes delivery fees and excludes discounts (final_price)
        # So we need to adjust: earnings = revenue - costs - delivery_fees + discounts
        # (because discounts reduce revenue but don't affect our costs)
        total_earnings = total_revenue - total_costs - total_delivery_fees + total_discounts
        
        return {
            'total_earnings': max(0, total_earnings),  # Ensure non-negative
            'total_revenue': total_revenue,
            'total_costs': total_costs,
            'total_delivery_fees': total_delivery_fees,
            'total_discounts': total_discounts
        }
    except Exception as e:
        print(f"Error calculating earnings: {str(e)}")
        return {
            'total_earnings': 0.0,
            'total_revenue': 0.0,
            'total_costs': 0.0,
            'total_delivery_fees': 0.0,
            'total_discounts': 0.0
        }

async def get_overview_stats(session: AsyncSession) -> OverviewStats:
    try:
        # Get total products count
        total_products_result = await session.exec(select(func.count()).select_from(Product))
        total_products = total_products_result.first() or 0

        # Get total orders count
        total_orders_result = await session.exec(select(func.count()).select_from(Order))
        total_orders = total_orders_result.first() or 0

        # Get total users count
        total_users_result = await session.exec(select(func.count()).select_from(User))
        total_users = total_users_result.first() or 0

        # Get average price - handle case where price field might not exist
        try:
            avg_price_result = await session.exec(select(func.avg(Product.price)))
            average_price = avg_price_result.first() or 0.0
        except Exception:
            average_price = 0.0

        # Get low stock count
        try:
            low_stock_result = await session.exec(
                select(func.count()).where(
                    (Product.in_stock == False) | (Product.quantity == 0)
                )
            )
            low_stock_count = low_stock_result.first() or 0
        except Exception:
            low_stock_count = 0

        # Calculate total storage usage
        products_dir = Path("static/images/products/")
        total_storage_bytes = 0
        if products_dir.exists():
            total_storage_bytes = sum(
                f.stat().st_size for f in products_dir.rglob("*") if f.is_file()
            )
        total_storage_mb = total_storage_bytes / (1024 * 1024)

        # Calculate earnings
        earnings_data = await calculate_earnings(session)

        return OverviewStats(
            total_products=total_products,
            total_orders=total_orders,
            total_users=total_users,
            average_price=average_price,
            low_stock_count=low_stock_count,
            total_storage_mb=total_storage_mb,
            total_earnings=earnings_data['total_earnings'],
            total_revenue=earnings_data['total_revenue'],
            total_costs=earnings_data['total_costs'],
            total_delivery_fees=earnings_data['total_delivery_fees'],
            total_discounts=earnings_data['total_discounts']
        )
    except Exception as e:
        raise Exception(f"Error calculating statistics: {str(e)}")
