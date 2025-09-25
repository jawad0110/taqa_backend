from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional
from src.admin_dashboard.users.service import UserService
from src.admin_dashboard.users.schemas import (
    UserCreate, UserUpdate, UserVerificationUpdate,
    UserResponse, UserDetailResponse, UserListResponse, UserStatsResponse
)
from src.auth.dependencies import admin_role_checker
from src.db.main import get_session
import logging

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

user_router = APIRouter()
user_service = UserService()


@user_router.get(
    "/",
    response_model=UserListResponse,
    summary="Get all users with pagination and filtering",
    responses={
        200: {"description": "Users retrieved successfully."},
        400: {"description": "Invalid query parameters."},
        500: {"description": "Internal server error."}
    }
)
async def get_all_users(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Number of users per page"),
    search: Optional[str] = Query(None, description="Search by name, email, or username"),
    role_filter: Optional[str] = Query(None, description="Filter by role (admin, user)"),
    verification_filter: Optional[str] = Query(None, description="Filter by verification status (verified, unverified)"),
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    Get all users with pagination and filtering options.
    
    - **page**: Page number (default: 1)
    - **limit**: Number of users per page (default: 10, max: 100)
    - **search**: Search by first name, last name, email, or username
    - **role_filter**: Filter by user role (admin, user)
    - **verification_filter**: Filter by verification status (verified, unverified)
    """
    try:
        result = await user_service.get_all_users(
            session=session,
            page=page,
            limit=limit,
            search=search,
            role_filter=role_filter,
            verification_filter=verification_filter
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_all_users endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@user_router.get(
    "/stats",
    response_model=UserStatsResponse,
    summary="Get user statistics for dashboard",
    responses={
        200: {"description": "User statistics retrieved successfully."},
        500: {"description": "Internal server error."}
    }
)
async def get_user_stats(
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    Get user statistics for the admin dashboard.
    
    Returns:
    - Total users count
    - Verified/unverified users count
    - Admin/regular users count
    - Recent registrations (last 30 days)
    """
    try:
        stats = await user_service.get_user_stats(session=session)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_user_stats endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user statistics"
        )


@user_router.get(
    "/{user_uid}",
    response_model=UserDetailResponse,
    summary="Get user details by UID",
    responses={
        200: {"description": "User details retrieved successfully."},
        404: {"description": "User not found."},
        500: {"description": "Internal server error."}
    }
)
async def get_user_by_uid(
    user_uid: str,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    Get detailed information about a specific user.
    
    - **user_uid**: The unique identifier of the user
    
    Returns detailed user information including:
    - Basic user data
    - Profile information
    - Order count
    - Review count
    - Cart items count
    - Wishlist items count
    """
    try:
        user = await user_service.get_user_by_uid(session=session, user_uid=user_uid)
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_user_by_uid endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user details"
        )


@user_router.post(
    "/",
    response_model=UserResponse,
    summary="Create a new user",
    responses={
        201: {"description": "User created successfully."},
        400: {"description": "Validation error or user already exists."},
        500: {"description": "Internal server error."}
    }
)
async def create_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    Create a new user account.
    
    - **username**: Unique username
    - **email**: Unique email address
    - **first_name**: User's first name
    - **last_name**: User's last name
    - **password**: User's password (minimum 8 characters)
    - **role**: User role (admin, user)
    - **is_verified**: Whether the user is verified
    """
    try:
        user = await user_service.create_user(session=session, user_data=user_data)
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_user endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@user_router.put(
    "/{user_uid}",
    response_model=UserResponse,
    summary="Update user information",
    responses={
        200: {"description": "User updated successfully."},
        400: {"description": "Validation error or conflict."},
        404: {"description": "User not found."},
        500: {"description": "Internal server error."}
    }
)
async def update_user(
    user_uid: str,
    user_data: UserUpdate,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    Update user information.
    
    - **user_uid**: The unique identifier of the user
    - **user_data**: Updated user information (all fields optional)
    """
    try:
        user = await user_service.update_user(session=session, user_uid=user_uid, user_data=user_data)
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_user endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@user_router.patch(
    "/{user_uid}/verification",
    response_model=UserResponse,
    summary="Update user verification status",
    responses={
        200: {"description": "User verification status updated successfully."},
        404: {"description": "User not found."},
        500: {"description": "Internal server error."}
    }
)
async def update_user_verification(
    user_uid: str,
    verification_data: UserVerificationUpdate,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    Update user verification status.
    
    - **user_uid**: The unique identifier of the user
    - **verification_data**: New verification status
    """
    try:
        user = await user_service.update_user_verification(
            session=session, 
            user_uid=user_uid, 
            verification_data=verification_data
        )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_user_verification endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user verification"
        )


@user_router.delete(
    "/{user_uid}",
    summary="Delete user (deactivate)",
    responses={
        200: {"description": "User deactivated successfully."},
        404: {"description": "User not found."},
        500: {"description": "Internal server error."}
    }
)
async def delete_user(
    user_uid: str,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    Delete a user (soft delete by deactivating).
    
    - **user_uid**: The unique identifier of the user
    
    Note: This performs a soft delete by deactivating the user account
    rather than permanently removing the user data.
    """
    try:
        success = await user_service.delete_user(session=session, user_uid=user_uid)
        if success:
            return {"message": "User deactivated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate user"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_user endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )
