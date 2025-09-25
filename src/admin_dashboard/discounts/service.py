from sqlmodel import select
from src.db.models import Discount
from .schemas import DiscountCreate, DiscountUpdate
from fastapi import HTTPException
from datetime import datetime
from sqlmodel.ext.asyncio.session import AsyncSession
import uuid


    

class DiscountService:
    async def get_discount_by_code(self, session: AsyncSession, code: str) -> Discount:
        result = await session.exec(select(Discount).where(Discount.code == code))
        discount = result.first()
        if not discount:
            raise HTTPException(status_code=404, detail="Discount code not found")
        return discount
    
    
    async def create_discount(self, session: AsyncSession, data: DiscountCreate) -> Discount:
        payload = data.dict()
        # strip timezone info for expires_at if needed
        if payload.get('expires_at') and isinstance(payload['expires_at'], datetime) and payload['expires_at'].tzinfo is not None:
            payload['expires_at'] = payload['expires_at'].replace(tzinfo=None)
        discount = Discount(**payload)
        session.add(discount)
        await session.commit()
        await session.refresh(discount)
        return discount

    
    async def validate_discount(self, session: AsyncSession, code: str, order_total: float) -> Discount:
        discount = await self.get_discount_by_code(session, code)
        if not discount.is_active:
            raise HTTPException(status_code=400, detail="Discount is not active")
        if discount.expires_at and discount.expires_at < datetime.now():
            raise HTTPException(status_code=400, detail="Discount expired")
        if discount.usage_limit is not None and discount.used_count >= discount.usage_limit:
            raise HTTPException(status_code=400, detail="Usage limit reached")
        if discount.minimum_order_amount and order_total < discount.minimum_order_amount:
            raise HTTPException(status_code=400, detail="Minimum order amount not met")
        return discount

    async def list_discounts(self, session: AsyncSession) -> list[Discount]:
        results = await session.exec(select(Discount))
        return results.all()

    async def update_discount(self, session: AsyncSession, uid: uuid.UUID, data: DiscountUpdate) -> Discount:
        results = await session.exec(select(Discount).where(Discount.uid == uid))
        discount = results.first()
        if not discount:
            raise HTTPException(status_code=404, detail="Discount not found")
        update_data = data.dict(exclude_unset=True)
        # strip timezone on updated expires_at
        if 'expires_at' in update_data and isinstance(update_data['expires_at'], datetime) and update_data['expires_at'].tzinfo is not None:
            update_data['expires_at'] = update_data['expires_at'].replace(tzinfo=None)
        for k, v in update_data.items():
            setattr(discount, k, v)
        await session.commit()
        await session.refresh(discount)
        return discount

    async def delete_discount(self, session: AsyncSession, uid: uuid.UUID) -> bool:
        results = await session.exec(select(Discount).where(Discount.uid == uid))
        discount = results.first()
        if not discount:
            raise HTTPException(status_code=404, detail="Discount not found")
        await session.delete(discount)
        await session.commit()
        return True
