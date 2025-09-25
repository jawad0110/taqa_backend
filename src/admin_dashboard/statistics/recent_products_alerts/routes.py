from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from src.db.main import get_session
from .schemas import RecentProduct, Alerts
from . import service

recent_products_alerts_router = APIRouter()

@recent_products_alerts_router.get("/recent-products", response_model=List[RecentProduct])
async def get_recent_products(db: AsyncSession = Depends(get_session)):
    try:
        products = await service.get_recent_products(db)
        if not products:
            raise HTTPException(status_code=404, detail="No products found")
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@recent_products_alerts_router.get("/alerts", response_model=Alerts)
async def get_alerts(db: AsyncSession = Depends(get_session)):
    try:
        alerts = await service.get_alerts(db)
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
