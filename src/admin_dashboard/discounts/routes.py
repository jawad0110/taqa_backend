from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession
from uuid import UUID
from typing import List
from src.db.main import get_session
from . import schemas
from .service import DiscountService
from src.auth.dependencies import AccessTokenBearer, RoleChecker

discount_router = APIRouter()
access_token_bearer = AccessTokenBearer()
admin_role_checker = Depends(RoleChecker(['admin']))
discount_service = DiscountService()

@discount_router.get("/", response_model=List[schemas.DiscountResponse], dependencies=[admin_role_checker])
async def list_discounts(session: AsyncSession = Depends(get_session), token_details: dict = Depends(access_token_bearer)):
    return await discount_service.list_discounts(session)

@discount_router.get("/{code}", response_model=schemas.DiscountResponse, dependencies=[admin_role_checker])
async def read_discount(code: str, session: AsyncSession = Depends(get_session), token_details: dict = Depends(access_token_bearer)):
    return await discount_service.get_discount_by_code(session, code)

@discount_router.post("/", response_model=schemas.DiscountResponse, status_code=status.HTTP_201_CREATED, dependencies=[admin_role_checker])
async def create_discount(data: schemas.DiscountCreate, session: AsyncSession = Depends(get_session), token_details: dict = Depends(access_token_bearer)):
    return await discount_service.create_discount(session, data)

@discount_router.put("/{uid}", response_model=schemas.DiscountResponse, dependencies=[admin_role_checker])
async def update_discount(uid: UUID, data: schemas.DiscountUpdate, session: AsyncSession = Depends(get_session), token_details: dict = Depends(access_token_bearer)):
    return await discount_service.update_discount(session, uid, data)

@discount_router.delete("/{uid}", status_code=status.HTTP_200_OK, dependencies=[admin_role_checker])
async def delete_discount(uid: UUID, session: AsyncSession = Depends(get_session), token_details: dict = Depends(access_token_bearer)):
    await discount_service.delete_discount(session, uid)
    return {"message": "Discount deleted successfully"}
