# Authentication and Authorization Dependencies

from fastapi import Request, status, Depends
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from fastapi.exceptions import HTTPException
from jose import JWTError
import logging

from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Any, Optional

from src.db.redis import token_in_blocklist
from src.db.main import get_session
from src.db.models import User

from .service import UserService
from .utils import decode_token
from src.errors import (
    InvalidToken,
    RefreshTokenRequired,
    AccessTokenRequired,
    InsufficientPermission,
    AccountNotVerified
)

# Service for user-related operations
user_service = UserService()


async def get_optional_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session)
) -> Optional[User]:
    authorization: str | None = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]  # Strip "Bearer "

    try:
        token_data = decode_token(token)
        user_email = token_data["user"]["email"]
        user = await user_service.get_user_by_email(user_email, session)
        return user
    except (JWTError, KeyError):
        return None
    


class TokenBearer(HTTPBearer):
    """Base class for JWT token validation.
    Extends FastAPI's HTTPBearer to add custom token validation logic.
    """
    def __init__(self, auto_error=True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        """Validate the Bearer token from the Authorization header.
        
        Args:
            request (Request): The incoming HTTP request
            
        Returns:
            dict: Decoded token data if valid
            
        Raises:
            InvalidToken: If token is invalid or blacklisted
        """
        try:
            # Extract token from Authorization header
            creds = await super().__call__(request)
            token = creds.credentials

            # Decode and validate the token
            token_data = decode_token(token)
            if not token_data:
                raise InvalidToken()

            # Check if token has been blacklisted (e.g., after logout)
            if await token_in_blocklist(token_data.get('jti')):
                raise InvalidToken()

            # Perform token-specific validation (implemented by child classes)
            self.verify_token_data(token_data)
            
            return token_data
        except JWTError:
            raise InvalidToken()
        except Exception as e:
            logging.error(f"Token validation error: {str(e)}")
            raise InvalidToken()
    
    def token_valid(self, token: str) -> bool:
        """Check if token can be decoded successfully."""
        token_data = decode_token(token)
        return token_data is not None
    
    def verify_token_data(self, token_data):
        """Abstract method for token-specific validation logic."""
        raise NotImplementedError("Please Override this method in child classes")


class AccessTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data and token_data["refresh"]:
            raise AccessTokenRequired()


class RefreshTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data and not token_data["refresh"]:
            raise RefreshTokenRequired()
            
async def get_current_user(
    token_details: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session)
):
    user_email = token_details['user']['email']
    
    user = await user_service.get_user_by_email(user_email, session)
    
    return user

class RoleChecker:
    """Role-Based Access Control (RBAC) implementation.
    Used as a dependency to protect routes based on user roles.
    """
    def __init__(self, allowed_roles: List[str]) -> None:
        """Initialize with a list of roles that have access.
        
        Args:
            allowed_roles (List[str]): List of role names that are permitted
        """
        self.allowed_roles = allowed_roles
    
    async def __call__(self, current_user: User = Depends(get_current_user)) -> Any:
        """Check if the current user has sufficient role-based permissions.
        
        Args:
            current_user (User): The authenticated user (from JWT token)
            
        Raises:
            AccountNotVerified: If user's email is not verified
            InsufficientPermission: If user's role is not in allowed_roles
            
        Returns:
            bool: True if user has sufficient permissions
        """
        # First check if user's account is verified
        if not current_user.is_verified:
            raise AccountNotVerified()
        
        # Then check if user's role is in the allowed roles list
        if current_user.role in self.allowed_roles:
            return True
        
        raise InsufficientPermission()

class AccountNotVerified(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="الحساب غير مفعل"
        )

# Pre-configured checker for admin-only routes
admin_role_checker = RoleChecker(allowed_roles=["admin"])