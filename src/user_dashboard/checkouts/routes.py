from fastapi import APIRouter, Depends, status
from typing import List
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import BackgroundTasks

from src.db.main import get_session
from src.auth.dependencies import get_current_user
from src.db.models import User
from .schemas import CheckoutCreate, CheckoutResponse
from .service import CheckoutService

user_checkout_router = APIRouter()


@user_checkout_router.post("/", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def create_checkout(
    cmd: CheckoutCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    service = CheckoutService(session)
    return await service.create_order(str(current_user.uid), cmd, background_tasks)

@user_checkout_router.get("/", response_model=List[CheckoutResponse])
async def list_my_orders(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    service = CheckoutService(session)
    return await service.list_orders_for_user(str(current_user.uid))

@user_checkout_router.get("/{order_uid}", response_model=CheckoutResponse)
async def get_order(
    order_uid: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    service = CheckoutService(session)
    return await service.get_order_for_user(str(current_user.uid), order_uid)

@user_checkout_router.delete("/{order_uid}", response_model=CheckoutResponse, status_code=status.HTTP_200_OK)
async def cancel_order(
    order_uid: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    service = CheckoutService(session)
    return await service.cancel_order(str(current_user.uid), order_uid)