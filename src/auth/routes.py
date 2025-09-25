from fastapi import APIRouter, Depends, status, BackgroundTasks
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import timedelta, datetime

from .dependencies import RefreshTokenBearer, AccessTokenBearer, get_current_user, RoleChecker
from .schemas import UserCreateModel, UserModel, UserLoginModel, UserProductModel, EmailModel, PasswordResetRequestModel, PasswordResetConfirmModel
from .utils import ACCESS_TOKEN_EXPIRY, create_access_token, decode_token, verify_password, create_url_safe_token, decode_url_safe_token, generate_passwd_hash
from .service import UserService

from src.errors import UserAlreadyExists, InvalidCredentials, UserNotFound, InvalidToken, AccountNotVerified
from src.db.redis import add_jti_to_blocklist
from src.db.main import get_session
from src.config import Config
from src.admin_dashboard.celery_tasks import send_email


auth_router = APIRouter()
user_service = UserService()
role_checker = RoleChecker(['admin', 'user'])

REFRESH_TOKEN_EXPIRY = 2


@auth_router.post('/send_mail')
async def send_mail(emails: EmailModel, session: AsyncSession = Depends(get_session)):
    emails_list = emails.addresses
    subject = "Welcome to the app"
    
    for email in emails_list:
        user = await user_service.get_user_by_email(email, session)
        name = user.first_name if user and getattr(user, "first_name", None) else "ضيفنا الكريم"
        send_email.delay(
            recipients=[email],
            subject=subject,
            template_name="welcome.html",
            template_body={"name": name}
        )
    return {"message": "Email(s) sent successfully"}



@auth_router.post('/signup', status_code=status.HTTP_201_CREATED)
async def create_user_Account(user_data: UserCreateModel, bg_tasks: BackgroundTasks, session: AsyncSession = Depends(get_session)):
    email = user_data.email
    
    user_exists = await user_service.user_exists(email, session)
    
    if user_exists:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "User with this email already exists. Please try logging in instead."
            }
        )
    
    new_user = await user_service.create_user(user_data, session)
    
    token = create_url_safe_token({"email": email})
    
    verification_link = f"{Config.FRONTEND_URL}/verify/{token}"
    
    emails = [email]    
    subject = "Verify your email"
    
    for email in emails:
        user = await user_service.get_user_by_email(email, session)
        name = user.first_name if user and getattr(user, "first_name", None) else "ضيفنا الكريم"
        send_email.delay(
            recipients=emails,
            subject=subject,
            template_name="email_verification.html",
            template_body={"verification_link": verification_link, "name": name})
    
    return {
        "message": "Account Created Successfully! Check your email to verify your account",
        "user": new_user,
        "verification_token": token
    }


@auth_router.get('/verify/{token}')
async def verify_account(token: str, session: AsyncSession = Depends(get_session)):
    """Verify user account."""
    try:
        token_data = decode_url_safe_token(token)
        
        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token. Please request a new one."
            )

        user_email = token_data.get('email')

        if user_email:
            user = await user_service.get_user_by_email(user_email, session)
            
            if not user:
                raise UserNotFound()
            
            await user_service.update_user(user, {'is_verified': True}, session)
            
            return JSONResponse(
                content={
                    "message": "Account Verified Successfully"
                },
                status_code=status.HTTP_200_OK
            )
            
        raise HTTPException(
            detail="Error occurred during verification",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@auth_router.post('/login')
async def login_users(login_data: UserLoginModel, session: AsyncSession = Depends(get_session)):
    email = login_data.email
    password = login_data.password
    
    user = await user_service.get_user_by_email(email, session)
    
    if user is None:
        raise UserNotFound()
        
    if user is not None:
        password_valid = verify_password(password, user.password_hash)
        
        if not password_valid:
            raise InvalidCredentials()
            
        if not user.is_verified:
            raise AccountNotVerified()
                
        access_token = create_access_token(
            user_data={
                'email': user.email,
                'user_uid': str(user.uid),
                'role': user.role
            }
        )
        
        refresh_token = create_access_token(
            user_data={
                'email': user.email,
                'user_uid': str(user.uid),
                'role': user.role
            },
            refresh=True,
            expiry=timedelta(days=REFRESH_TOKEN_EXPIRY)
        )
        
        return JSONResponse(
            content={
                "message": "تم تسجيل الدخول بنجاح",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "email": user.email,
                    "uid": str(user.uid),
                    "role": user.role
                }
            }
        )


@auth_router.get('/validate_token')
async def validate_token(token_details: dict = Depends(AccessTokenBearer())):
    return JSONResponse(content={"valid": True})

@auth_router.get('/refresh_token')
async def get_new_access_token(token_details: dict = Depends(RefreshTokenBearer())):
    expiry_timestamp = token_details['exp']
    
    if datetime.fromtimestamp(expiry_timestamp) > datetime.now():
        new_access_token = create_access_token(
            user_data=token_details['user'],
            expiry=timedelta(seconds=ACCESS_TOKEN_EXPIRY)
        )
        
        return JSONResponse(content={
            "access_token": new_access_token
        })
        
    raise InvalidToken()



@auth_router.get('/me', response_model=UserProductModel)
async def get_current_user(user= Depends(get_current_user), _:bool = Depends(role_checker)):
    return user



@auth_router.get('/logout')
async def revoke_token(token_details: dict = Depends(AccessTokenBearer())):
    jti = token_details["jti"]
    
    await add_jti_to_blocklist(jti)
    
    return JSONResponse(
        content={
            "message": "Logout Successful"
        },
        status_code=status.HTTP_200_OK
    )


'''
Reset Password:
1. PROVIDE THE EMAIL -> password reset request
2. SEND A PASSWORD RESET LINK TO THE EMAIL
3. RESET THE PASSWORD -> password reset confirmation
'''


@auth_router.post('/password-reset-request')
async def password_reset_request(email_data: PasswordResetRequestModel, session: AsyncSession = Depends(get_session)):
    email = email_data.email
    
    # التحقق من وجود المستخدم
    user = await user_service.get_user_by_email(email, session)
    if not user:
        raise UserNotFound()
    
    token = create_url_safe_token({"email": email})
    link = F"{Config.FRONTEND_URL}/reset-password/{token}"
    
    emails = [email]
    subject = "إعادة تعيين كلمة المرور"
    
    name = user.first_name if user and getattr(user, "first_name", None) else "ضيفنا الكريم"
    send_email.delay(
        recipients=emails,
        subject=subject,
        template_name="password_reset.html",
        template_body={"reset_link": link, "name": name})
    
    return JSONResponse(
        content={
            "message": "تم إرسال رابط إعادة تعيين كلمة المرور بنجاح! يرجى التحقق من بريدك الإلكتروني"
        },
        status_code=status.HTTP_200_OK
    )
    

    
@auth_router.post('/password-reset-confirm/{token}')
async def reset_account_password(token: str, passwords: PasswordResetConfirmModel, session: AsyncSession = Depends(get_session)):
    new_password = passwords.new_password
    confirm_password = passwords.confirm_new_password
    
    if new_password != confirm_password:
        raise HTTPException(
            detail= {
                "message": "كلمات المرور غير متطابقة",
                "error_code": "passwords_not_match"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        token_data = decode_url_safe_token(token)
        user_email = token_data.get('email')
        
        if not user_email:
            raise InvalidToken()
            
        user = await user_service.get_user_by_email(user_email, session)
        
        if not user:
            raise UserNotFound()
        
        password_hash = generate_passwd_hash(new_password)
        await user_service.update_user(user, {'password_hash': password_hash}, session)
        
        return JSONResponse(
            content={
                "message": "تم إعادة تعيين كلمة المرور بنجاح"
            },
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        return JSONResponse(
            content={
                "message": "حدث خطأ أثناء إعادة تعيين كلمة المرور",
                "error": str(e)
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@auth_router.post('/resend-verification')
async def resend_verification(email_data: EmailModel, session: AsyncSession = Depends(get_session)):
    email = email_data.addresses[0] if email_data.addresses else None
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "البريد الإلكتروني مطلوب",
                "error_code": "email_required"
            }
        )
    
    user = await user_service.get_user_by_email(email, session)
    
    if not user:
        raise UserNotFound()
    
    if user.is_verified:
        return JSONResponse(
            content={
                "message": "الحساب مفعل بالفعل",
                "status": "already_verified"
            },
            status_code=status.HTTP_200_OK
        )
    
    token = create_url_safe_token({"email": email})
    verification_link = f"{Config.FRONTEND_URL}/verify/{token}"
    
    name = user.first_name if user and getattr(user, "first_name", None) else "ضيفنا الكريم"
    send_email.delay(
        recipients=[email],
        subject="تفعيل حسابك",
        template_name="email_verification.html",
        template_body={"verification_link": verification_link, "name": name}
    )
    
    return JSONResponse(
        content={
            "message": "تم إرسال رابط التفعيل بنجاح! يرجى التحقق من بريدك الإلكتروني",
            "status": "verification_sent"
        },
        status_code=status.HTTP_200_OK
    )
