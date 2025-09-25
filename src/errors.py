from typing import Any, Callable
from fastapi import FastAPI, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import HTTPException, status

# --- Product Image Management Exceptions ---
class MissingMainImageError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail="Main image is required.")

class InvalidImageTypeError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image type or extension.")

class TooManyAdditionalImagesError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail="Too many additional images (max 4 allowed).")

class DeletionConstraintError(HTTPException):
    def __init__(self, message="Cannot delete image due to business constraints."):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

class TaqaException(Exception):
    """This is the base class for all Taqa errors"""
    pass


class InvalidToken(TaqaException):
    """User has been provided an invalid or expired token"""
    pass


class RevokedToken(TaqaException):
    """User has been provided a token that has been revoked"""
    pass


class AccessTokenRequired(TaqaException):
    """User has been provided a refresh token when an access token is needed"""
    pass


class RefreshTokenRequired(TaqaException):
    """User has been provided an access token when an access token is needed"""
    pass


class UserAlreadyExists(TaqaException):
    """User has been provided an email for a user who exists during sign up."""
    def __init__(self):
        super().__init__("البريد الإلكتروني مسجل مسبقاً. يرجى تسجيل الدخول بدلاً من ذلك.")


class UserNotFound(TaqaException):
    """User not found."""
    def __init__(self):
        super().__init__("حسابك غير موجود، يرجى إنشاء حساب جديد")


class AccountNotVerified(TaqaException):
    """Account not verified yet."""
    def __init__(self):
        super().__init__("حسابك غير مفعل، يرجى تفعيل حسابك")


class InvalidCredentials(TaqaException):
    """User has been provided wrong email password during login."""
    def __init__(self):
        super().__init__("كلمة المرور خاطئة، يرجى إدخال كلمة المرور الصحيحة")


class InsufficientPermission(TaqaException):
    """User has been provided a refresh token when an access token is needed"""
    pass


class ProductNotFound(TaqaException):
    """Product not found."""
    pass

class VariantGroupNotFound(TaqaException):
    """Variant group not found."""
    pass

class VariantChoiceNotFound(TaqaException):
    """Variant choice not found."""
    pass

class InvalidVariantGroup(TaqaException):
    """Variant group must have at least one choice."""
    pass


class UserNotFound(TaqaException):
    """User not found."""
    def __init__(self):
        super().__init__("لم يتم العثور على حساب بهذا البريد الإلكتروني. يرجى التحقق من البريد الإلكتروني أو إنشاء حساب جديد.")


class AccountNotVerified(TaqaException):
    """Account not verified yet."""
    def __init__(self):
        super().__init__("الحساب غير مفعل. يرجى التحقق من بريدك الإلكتروني للحصول على رابط التفعيل.")


def create_exception_handler(status_code: int, initial_detail: Any) -> Callable[[Request, Exception], JSONResponse]:
    async def exception_handler(request: Request, exc: TaqaException):
        return JSONResponse(
            content=initial_detail,
            status_code=status_code
        )
        
    return exception_handler



def register_all_errors(app: FastAPI):
    #  User Already Exists
    app.add_exception_handler(
        UserAlreadyExists,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "البريد الإلكتروني مسجل مسبقاً",
                "error_code": "user_exists",
                "resolution": "يرجى تسجيل الدخول بدلاً من ذلك"
            }
        )
    )

    #  Product Not Found
    app.add_exception_handler(
        ProductNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "Product not found",
                "error_code": "Product_does_not_exists"
            }
        )
    )
    
    # User Not Found
    app.add_exception_handler(
        UserNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "حسابك غير موجود، يرجى إنشاء حساب جديد",
                "error_code": "user_does_not_exists",
                "resolution": "يرجى التحقق من البريد الإلكتروني أو إنشاء حساب جديد"
            }
        )
    )

    # Account Not Verified (remove duplicate)
    app.add_exception_handler(
        AccountNotVerified,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "حسابك غير مفعل، يرجى تفعيل حسابك",
                "error_code": "account_not_verified",
                "resolution": "يرجى التحقق من بريدك الإلكتروني للحصول على رابط التفعيل",
                "can_resend": True
            }
        )
    )

    # Access Token Required
    app.add_exception_handler(
        AccessTokenRequired,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "Access token is required",
                "error_code": "access_token_required"
            }
        )
    )

    # Invalid Token
    app.add_exception_handler(
        InvalidToken,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "you provided an invalid or expired token",
                "error_code": "invalid_token"
            }
        )
    )

    # Refresh Token Required
    app.add_exception_handler(
        RefreshTokenRequired,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "Refresh token is required",
                "error_code": "refresh_token_required"
            }
        )
    )

    # Revoked Token
    app.add_exception_handler(
        RevokedToken,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "you provided a revoked token",
                "error_code": "rekoved_token"
            }
        )
    )

    # Invalid Credentials
    app.add_exception_handler(
        InvalidCredentials,
        create_exception_handler(
            status_code=status.HTTP_400_BAD_REQUEST,
            initial_detail={
                "message": "كلمة المرور خاطئة، يرجى إدخال كلمة المرور الصحيحة",
                "error_code": "invalid_credentials",
                "resolution": "يرجى التحقق من كلمة المرور والمحاولة مرة أخرى"
            }
        )
    )

    # Insufficient Permission
    app.add_exception_handler(
        InsufficientPermission,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "You do not have sufficient permission",
                "error_code": "insufficient_permission"
            }
        )
    )

    @app.exception_handler(500)
    async def enternal_server_error_handler(request, exc):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Opps, Something went wrong. Please try again later",
                "error_code": "server_error"
            }
        )

    @app.exception_handler(404)
    async def not_found_error_handler(request, exc):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "message": "الخدمة غير متوفرة",
                "error_code": "service_unavailable",
                "resolution": "يرجى التحقق من الرابط أو الاتصال بالدعم الفني"
            }
        )

