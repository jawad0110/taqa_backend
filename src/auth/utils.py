# Authentication and JWT Utilities

from passlib.context import CryptContext
from datetime import timedelta, datetime
from src.errors import InvalidToken
from src.config import Config
from itsdangerous import URLSafeTimedSerializer  # For creating secure URL-safe tokens
import jwt  # JSON Web Token implementation
import uuid
import logging

# Password hashing configuration using bcrypt
passwd_context = CryptContext(
    schemes=["bcrypt"]
)

# Token expiry times in seconds
ACCESS_TOKEN_EXPIRY = Config.ACCESS_TOKEN_EXPIRY_DAYS * 24 * 60 * 60  # 7 days
REFRESH_TOKEN_EXPIRY = Config.REFRESH_TOKEN_EXPIRY_DAYS * 24 * 60 * 60  # 30 days


def generate_passwd_hash(password: str) -> str:
    hash = passwd_context.hash(password)
    
    return hash

def verify_password(password: str, hash: str) -> bool:
    return passwd_context.verify(password, hash)

def create_access_token(user_data: dict, expiry: timedelta = None, refresh: bool = False):
    """Create a JWT access token for authentication.
    
    Args:
        user_data (dict): User information to encode in the token
        expiry (timedelta, optional): Custom expiration time. Defaults to ACCESS_TOKEN_EXPIRY
        refresh (bool, optional): Whether this is a refresh token. Defaults to False
    
    Returns:
        str: Encoded JWT token
    """
    payload = {
        'user': user_data,  # User information (typically email, id, etc)
        'exp': datetime.now() + (expiry if expiry is not None else timedelta(seconds=REFRESH_TOKEN_EXPIRY if refresh else ACCESS_TOKEN_EXPIRY)),  # Token expiration
        'jti': str(uuid.uuid4()),  # Unique token identifier for blacklisting
        'refresh': refresh  # Whether this is a refresh token
    }
    
    # Encode the token using the secret key and specified algorithm
    token = jwt.encode(
        payload = payload,
        key = Config.JWT_SECRET,
        algorithm = Config.JWT_ALGORITHM
    )
    
    return token

def decode_token(token: str) -> dict:
    """Decode and verify a JWT token.
    
    Args:
        token (str): The JWT token to decode
    
    Returns:
        dict: Decoded token payload if valid, None if invalid
    """
    try:
        if not token:
            return None
            
        # Verify and decode the token using the same secret key and algorithm
        token_data = jwt.decode(
            jwt = token,
            key = Config.JWT_SECRET,
            algorithms = [Config.JWT_ALGORITHM],
            options={"verify_exp": False}  # Don't verify expiration for now
        )
        
        # Check if token is expired
        if "exp" in token_data:
            exp_time = datetime.fromtimestamp(token_data["exp"])
            if exp_time < datetime.now():
                logging.warning(f"Token has expired: {token_data.get('jti')}")
                raise jwt.ExpiredSignatureError("Token has expired")
                
        return token_data
    
    except jwt.ExpiredSignatureError as e:
        logging.error(f"Token expired: {str(e)}")
        raise InvalidToken("التوكن منتهي الصلاحية")
    except jwt.PyJWTError as e:
        logging.error(f"JWT error: {str(e)}")
        raise InvalidToken("خطأ في التوكن")
    except Exception as e:
        logging.error(f"Token decoding error: {str(e)}")
        raise InvalidToken("فشل في تحليل التوكن")

serializer = URLSafeTimedSerializer(
    secret_key = Config.JWT_SECRET,
    salt = "email-configuration"
)

def create_url_safe_token(data: dict):
    token = serializer.dumps(data)
    return token

def decode_url_safe_token(token: str):
    try:
        token_data = serializer.loads(token)
        return token_data
    
    except Exception as e:
        logging.error(str(e))