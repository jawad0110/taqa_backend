from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status
from uuid import UUID

from src.db.models import ShippingRate
from .schemas import ShippingRateCreate, ShippingRateUpdate

class ShippingRateService:
    async def list_rates(self, session: AsyncSession) -> list[ShippingRate]:
        results = await session.exec(select(ShippingRate))
        return results.all()

    async def get_rate(self, session: AsyncSession, uid: UUID) -> ShippingRate:
        result = await session.exec(select(ShippingRate).where(ShippingRate.uid == uid))
        rate = result.one_or_none()
        if not rate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipping rate not found")
        return rate

    async def create_rate(self, session: AsyncSession, data: ShippingRateCreate) -> ShippingRate:
        payload = data.dict()
        rate = ShippingRate(**payload)
        session.add(rate)
        await session.commit()
        await session.refresh(rate)
        return rate

    async def update_rate(self, session: AsyncSession, uid: UUID, data: ShippingRateUpdate) -> ShippingRate:
        rate = await self.get_rate(session, uid)
        update_data = data.dict(exclude_unset=True)
        for k, v in update_data.items():
            setattr(rate, k, v)
        session.add(rate)
        await session.commit()
        await session.refresh(rate)
        return rate

    async def delete_rate(self, session: AsyncSession, uid: UUID) -> bool:
        rate = await self.get_rate(session, uid)
        await session.delete(rate)
        await session.commit()
        return True
