from sqlmodel import select
from src.db.models import Review
from src.auth.service import UserService
from src.admin_dashboard.products.service import ProductService
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi.exceptions import HTTPException
from fastapi import status
from .schemas import ReviewCreateModel, ReviewUpdateModel
from src.db.models import Review
from typing import List, Optional, Tuple
from uuid import UUID
from sqlmodel import or_
from datetime import datetime
from src.db.main import get_session
from sqlalchemy import func

class ReviewService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_service = ProductService(session)
        self.user_service = UserService()

    async def get_review_by_uid(self, review_uid: str):
        statement = select(Review).where(Review.uid == review_uid)
        result = await self.session.exec(statement)
        
        review = result.first()
        return review
    
    async def add_review_to_product(self, user_email: str, product_uid: str, review_data: ReviewCreateModel):
        try:
            product = await self.product_service.get_product(
                product_uid=product_uid,
                session=self.session
            )
            user = await self.user_service.get_user_by_email(
                email=user_email,
                session=self.session
            )
            
            review_data_dict = review_data.model_dump()
            new_review = Review(
                **review_data_dict
            )
            
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="product not found."
                )
                
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Please Login to Review the product."
                )
            
            new_review.user = user
            new_review.product = product
            self.session.add(new_review)
            await self.session.commit()
            
            return new_review
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ooops, something went wrong. Please try again later."
            )
            
    async def update_product_review(self, review_uid: str, review_data: ReviewUpdateModel, current_user):
        # Get the review by its unique identifier
        review_to_update = await self.get_review_by_uid(review_uid)
        
        # If the review is not found, raise a 404 error
        if not review_to_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found."
            )
        # Check ownership or admin
        if str(review_to_update.user_uid) != str(current_user.uid) and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to update this review."
            )
        # Update fields
        review_data_dict = review_data.model_dump()
        for k, v in review_data_dict.items():
            setattr(review_to_update, k, v)
        await self.session.commit()
        return review_to_update
    
    async def delete_product_review(self, review_uid: str, current_user):
        review_to_delete = await self.get_review_by_uid(review_uid)
        if review_to_delete is None:
            return None
        # Check ownership or admin
        if str(review_to_delete.user_uid) != str(current_user.uid) and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to delete this review."
            )
        await self.session.delete(review_to_delete)
        await self.session.commit()
        return {}
