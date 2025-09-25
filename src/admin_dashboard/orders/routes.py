from fastapi import APIRouter, Depends, Query
from typing import List
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_session
from src.auth.dependencies import AccessTokenBearer, RoleChecker
from .service import OrderService
from .schemas import OrderResponse, UpdateOrderStatus, PaginatedOrderResponse

order_router = APIRouter()
access_token_bearer = AccessTokenBearer()
admin_role_checker = Depends(RoleChecker(['admin']))
order_service = OrderService()

@order_router.get('/', response_model=PaginatedOrderResponse, dependencies=[admin_role_checker])
async def list_orders(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Number of orders per page"),
    session: AsyncSession = Depends(get_session), 
    token_details: dict = Depends(access_token_bearer)
):
    return await order_service.list_orders(session, page, per_page)

@order_router.get('/{order_uid}', response_model=OrderResponse, dependencies=[admin_role_checker])
async def read_order(order_uid: str, session: AsyncSession = Depends(get_session), token_details: dict = Depends(access_token_bearer)):
    return await order_service.get_order(session, order_uid)

@order_router.patch('/{order_uid}', response_model=OrderResponse, dependencies=[admin_role_checker])
async def update_order_status(order_uid: str, data: UpdateOrderStatus, session: AsyncSession = Depends(get_session), token_details: dict = Depends(access_token_bearer)):
    return await order_service.update_order_status(session, order_uid, data)