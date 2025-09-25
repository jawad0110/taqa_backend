from fastapi import APIRouter, Depends, status
from typing import List
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.main import get_session
from src.auth.dependencies import AccessTokenBearer, RoleChecker
from .service import ShippingRateService
from .schemas import ShippingRateCreate, ShippingRateUpdate, ShippingRateResponse

shipping_rate_router = APIRouter()
access_token_bearer = AccessTokenBearer()
admin_role_checker = Depends(RoleChecker(['admin']))
shipping_rate_service = ShippingRateService()

@shipping_rate_router.get('/', response_model=List[ShippingRateResponse], dependencies=[admin_role_checker])
async def list_shipping_rates(session: AsyncSession = Depends(get_session), token_details: dict = Depends(access_token_bearer)):
    return await shipping_rate_service.list_rates(session)

@shipping_rate_router.get('/{uid}', response_model=ShippingRateResponse, dependencies=[admin_role_checker])
async def get_shipping_rate(uid: UUID, session: AsyncSession = Depends(get_session), token_details: dict = Depends(access_token_bearer)):
    return await shipping_rate_service.get_rate(session, uid)

@shipping_rate_router.post('/', response_model=ShippingRateResponse, status_code=status.HTTP_201_CREATED, dependencies=[admin_role_checker])
async def create_shipping_rate(data: ShippingRateCreate, session: AsyncSession = Depends(get_session), token_details: dict = Depends(access_token_bearer)):
    return await shipping_rate_service.create_rate(session, data)

@shipping_rate_router.put('/{uid}', response_model=ShippingRateResponse, dependencies=[admin_role_checker])
async def update_shipping_rate(uid: UUID, data: ShippingRateUpdate, session: AsyncSession = Depends(get_session), token_details: dict = Depends(access_token_bearer)):
    return await shipping_rate_service.update_rate(session, uid, data)

@shipping_rate_router.delete('/{uid}', status_code=status.HTTP_200_OK, dependencies=[admin_role_checker])
async def delete_shipping_rate(uid: UUID, session: AsyncSession = Depends(get_session), token_details: dict = Depends(access_token_bearer)):
    await shipping_rate_service.delete_rate(session, uid)
    return {"message": "Shipping rate deleted successfully"}
