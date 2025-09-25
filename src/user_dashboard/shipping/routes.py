from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Dict, List, Any

from src.db.main import get_session
from src.auth.dependencies import get_current_user
from src.db.models import User, ShippingRate
from sqlmodel import select

user_shipping_router = APIRouter()

@user_shipping_router.get("/rates")
async def get_shipping_rates(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get all shipping rates grouped by country.
    Returns a list of countries with their available cities and rates.
    """
    # Fetch all shipping rates
    stmt = select(ShippingRate)
    result = await session.exec(stmt)
    shipping_rates = result.all()
    
    if not shipping_rates:
        return []
    
    # Group shipping rates by country
    grouped_rates = {}
    
    for rate in shipping_rates:
        country = rate.country
        
        if country not in grouped_rates:
            grouped_rates[country] = {
                "country": country,
                "cities": [],
                "rates": {}
            }
        
        city = rate.city
        grouped_rates[country]["cities"].append({
            "name": city,
            "price": float(rate.price)
        })
        
        # Store rate by city for easy lookup
        grouped_rates[country]["rates"][city] = {
            "uid": str(rate.uid),
            "price": float(rate.price)
        }
    
    # Convert to list for API response
    result = [value for _, value in grouped_rates.items()]
    
    return result
