from fastapi import APIRouter, Depends, HTTPException, status, Query
from src.db.models import User
from src.db.main import get_session
from src.auth.dependencies import get_current_user
from sqlmodel.ext.asyncio.session import AsyncSession
from .schemas import (
    ReviewCreateModel,
    ReviewUpdateModel,
)
from .service import ReviewService
from typing import Optional
from uuid import UUID

review_router = APIRouter()

@review_router.post('/product/{product_uid}')
async def add_review_to_products(
    product_uid: str,
    review_data: ReviewCreateModel,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    service = ReviewService(session)
    new_review = await service.add_review_to_product(
        user_email=current_user.email,
        review_data=review_data,
        product_uid=product_uid
    )
    
    return new_review


from src.auth.dependencies import admin_role_checker

@review_router.patch('/{review_uid}')
async def update_review_by_uid(
    review_uid: str,
    review_data: ReviewUpdateModel,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    service = ReviewService(session)
    update_review_by_uid = await service.update_product_review(review_uid, review_data, current_user)
    return update_review_by_uid

@review_router.delete('/{review_uid}')
async def delete_review_by_uid(
    review_uid: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    service = ReviewService(session)
    delete_review_by_uid = await service.delete_product_review(review_uid, current_user)
    if delete_review_by_uid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="product Review not found"
        )
    return {"message": "Review Deleted Successfully"}
