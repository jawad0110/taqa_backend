from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, desc, and_, or_, func
from sqlalchemy.orm import joinedload, selectinload
from typing import List, Optional, Tuple
from src.admin_dashboard.users.schemas import (
    UserCreate, UserUpdate, UserVerificationUpdate,
    UserResponse, UserDetailResponse, UserListResponse, UserStatsResponse
)
from src.db.models import User, Profile, Order, Review, Cart, Wishlist
from src.auth.utils import generate_passwd_hash
import uuid
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self):
        pass

    async def get_all_users(
        self, 
        session: AsyncSession, 
        page: int = 1, 
        limit: int = 10,
        search: Optional[str] = None,
        role_filter: Optional[str] = None,
        verification_filter: Optional[str] = None
    ) -> UserListResponse:
        """Get all users with pagination and filtering"""
        try:
            # Build query
            query = select(User).options(selectinload(User.profile))
            
            # Apply filters
            conditions = []
            
            if search:
                search_condition = or_(
                    User.first_name.ilike(f"%{search}%"),
                    User.last_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                    User.username.ilike(f"%{search}%")
                )
                conditions.append(search_condition)
            
            if role_filter and role_filter != "all":
                conditions.append(User.role == role_filter)
            
            if verification_filter and verification_filter != "all":
                if verification_filter == "verified":
                    conditions.append(User.is_verified == True)
                elif verification_filter == "unverified":
                    conditions.append(User.is_verified == False)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Get total count
            count_query = select(func.count(User.uid))
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            total_result = await session.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination
            offset = (page - 1) * limit
            query = query.offset(offset).limit(limit).order_by(desc(User.created_at))
            
            result = await session.execute(query)
            users = result.scalars().all()
            
            # Convert to response models
            user_responses = [UserResponse.model_validate(user) for user in users]
            
            total_pages = (total + limit - 1) // limit
            
            return UserListResponse(
                users=user_responses,
                total=total,
                page=page,
                limit=limit,
                total_pages=total_pages
            )
            
        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve users"
            )

    async def get_user_by_uid(self, session: AsyncSession, user_uid: str) -> UserDetailResponse:
        """Get a specific user by UID with detailed information"""
        try:
            query = select(User).options(
                selectinload(User.profile),
                selectinload(User.orders),
                selectinload(User.reviews),
                selectinload(User.cart_items),
                selectinload(User.wishlist_items)
            ).where(User.uid == user_uid)
            
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Get additional statistics
            total_orders = len(user.orders) if user.orders else 0
            total_reviews = len(user.reviews) if user.reviews else 0
            total_cart_items = len(user.cart_items) if user.cart_items else 0
            total_wishlist_items = len(user.wishlist_items) if user.wishlist_items else 0
            
            # Prepare profile data
            profile_data = None
            if user.profile:
                profile_data = {
                    "phone_number": user.profile.phone_number,
                    "address": user.profile.address,
                    "city": user.profile.city,
                    "country": user.profile.country,
                    "postal_code": user.profile.postal_code,
                    "created_at": user.profile.created_at,
                    "updated_at": user.profile.updated_at
                }
            
            return UserDetailResponse(
                uid=user.uid,
                username=user.username,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role,
                is_verified=user.is_verified,
                created_at=user.created_at,
                updated_at=user.updated_at,
                profile=profile_data,
                total_orders=total_orders,
                total_reviews=total_reviews,
                total_cart_items=total_cart_items,
                total_wishlist_items=total_wishlist_items
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting user by UID: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user details"
            )

    async def create_user(self, session: AsyncSession, user_data: UserCreate) -> UserResponse:
        """Create a new user"""
        try:
            # Check if user already exists
            existing_user_query = select(User).where(
                or_(User.email == user_data.email, User.username == user_data.username)
            )
            existing_user_result = await session.execute(existing_user_query)
            existing_user = existing_user_result.scalar_one_or_none()
            
            if existing_user:
                if existing_user.email == user_data.email:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username already taken"
                    )
            
            # Hash password
            hashed_password = generate_passwd_hash(user_data.password)
            
            # Create user
            user = User(
                username=user_data.username,
                email=user_data.email,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                role=user_data.role,
                is_verified=user_data.is_verified,
                password_hash=hashed_password
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            return UserResponse.model_validate(user)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )

    async def update_user(self, session: AsyncSession, user_uid: str, user_data: UserUpdate) -> UserResponse:
        """Update an existing user"""
        try:
            query = select(User).where(User.uid == user_uid)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Check for email/username conflicts if they're being updated
            if user_data.email or user_data.username:
                conflict_query = select(User).where(
                    and_(
                        User.uid != user_uid,
                        or_(
                            User.email == user_data.email if user_data.email else False,
                            User.username == user_data.username if user_data.username else False
                        )
                    )
                )
                conflict_result = await session.execute(conflict_query)
                conflict_user = conflict_result.scalar_one_or_none()
                
                if conflict_user:
                    if conflict_user.email == user_data.email:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Email already registered"
                        )
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Username already taken"
                        )
            
            # Update user fields
            update_data = user_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(user, field, value)
            
            user.updated_at = datetime.now()
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            return UserResponse.model_validate(user)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user"
            )

    async def update_user_verification(self, session: AsyncSession, user_uid: str, verification_data: UserVerificationUpdate) -> UserResponse:
        """Update user verification status"""
        try:
            query = select(User).where(User.uid == user_uid)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            user.is_verified = verification_data.is_verified
            user.updated_at = datetime.now()
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            return UserResponse.model_validate(user)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating user verification: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user verification"
            )

    async def delete_user(self, session: AsyncSession, user_uid: str) -> bool:
        """Delete a user (soft delete by deactivating)"""
        try:
            query = select(User).where(User.uid == user_uid)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # For safety, we'll just deactivate the user instead of hard delete
            user.is_verified = False
            user.updated_at = datetime.now()
            
            session.add(user)
            await session.commit()
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user"
            )

    async def get_user_stats(self, session: AsyncSession) -> UserStatsResponse:
        """Get user statistics for dashboard"""
        try:
            # Total users
            total_users_query = select(func.count(User.uid))
            total_users_result = await session.execute(total_users_query)
            total_users = total_users_result.scalar()
            
            # Verified users
            verified_users_query = select(func.count(User.uid)).where(User.is_verified == True)
            verified_users_result = await session.execute(verified_users_query)
            verified_users = verified_users_result.scalar()
            
            # Unverified users
            unverified_users = total_users - verified_users
            
            # Admin users
            admin_users_query = select(func.count(User.uid)).where(User.role == "admin")
            admin_users_result = await session.execute(admin_users_query)
            admin_users = admin_users_result.scalar()
            
            # Regular users
            regular_users = total_users - admin_users
            
            # Recent registrations (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_registrations_query = select(func.count(User.uid)).where(User.created_at >= thirty_days_ago)
            recent_registrations_result = await session.execute(recent_registrations_query)
            recent_registrations = recent_registrations_result.scalar()
            
            return UserStatsResponse(
                total_users=total_users,
                verified_users=verified_users,
                unverified_users=unverified_users,
                admin_users=admin_users,
                regular_users=regular_users,
                recent_registrations=recent_registrations
            )
            
        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user statistics"
            )
