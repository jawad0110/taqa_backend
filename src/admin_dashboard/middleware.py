from fastapi import FastAPI, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from datetime import datetime, timedelta
import time
import logging

from src.auth.utils import decode_token, create_access_token

logger = logging.getLogger('uvicorn.access')
logger.disabled = True

def register_middleware(app: FastAPI):
    
    @app.middleware("https")
    async def custom_logging(request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        processing_time = time.time() - start_time
        
        message = f"{request.client.host}: {request.client.port} - {request.method} - {request.url.path} - {response.status_code} completed after {processing_time}s"

        logger.info(message)        
        return response
    
    @app.middleware("https")
    async def session_middleware(request: Request, call_next):
        # Skip session check for login and refresh endpoints
        if request.url.path in ['/auth/login', '/auth/refresh']:
            return await call_next(request)

        response = await call_next(request)
        
        # Check if user is authenticated
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.info(f"No auth header found for request to {request.url.path}")
            return response

        token = auth_header[7:]  # Remove "Bearer " prefix
        
        try:
            # Try to decode the access token
            token_data = decode_token(token)
            logger.info(f"Successfully decoded token for user {token_data.get('user', {}).get('email', 'unknown')}")
            
            # Check if token is about to expire (within 5 minutes)
            exp = token_data.get("exp")
            if exp and datetime.fromtimestamp(exp) - datetime.now() < timedelta(minutes=5):
                logger.info("Token is about to expire, attempting refresh")
                # Token is about to expire, try to refresh it
                refresh_token = request.cookies.get("refresh_token")
                if refresh_token:
                    try:
                        refresh_data = decode_token(refresh_token)
                        new_access_token = create_access_token({
                            "email": refresh_data["user"]["email"],
                            "user_uid": refresh_data["user"]["user_uid"],
                            "role": refresh_data["user"]["role"]
                        })
                        
                        logger.info(f"Successfully refreshed token for user {refresh_data['user']['email']}")
                        
                        # Set the new access token in the response
                        response.set_cookie(
                            "access_token",
                            new_access_token,
                            httponly=True,
                            secure=True,
                            samesite="lax",
                            max_age=60 * 60 * 24 * 7  # 7 days
                        )
                    except Exception as e:
                        logger.error(f"Error refreshing token: {str(e)}")
                        # Clear invalid tokens
                        response.delete_cookie("access_token")
                        response.delete_cookie("refresh_token")
                        response.delete_cookie("is_logged_in")
                        logger.info("Cleared invalid tokens due to refresh failure")
                        
        except Exception as e:
            logger.error(f"Error in session middleware: {str(e)}")
            logger.info("Clearing tokens due to session middleware error")
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            response.delete_cookie("is_logged_in")
            
        return response
    
    # Configure CORS middleware
    origins = ["http://192.168.0.10:8000", "http://localhost:8000", "http://localhost:3000", "http://192.168.0.10:3000", "http://localhost:3000", "http://192.168.1.18:8000", "http://192.168.1.16:3000", "http://127.0.0.1:8000", "http://localhost:3000", "http://172.31.48.1:3000"]
    
    # Allowed headers for CORS
    allowed_headers = [
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Accept",
        "Accept-Encoding",
        "Accept-Language",
        "Cache-Control",
        "Connection",
        "DNT",
        "Host",
        "Origin",
        "Pragma",
        "Referer",
        "User-Agent"
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=600  # Cache preflight requests for 10 minutes
    )

    
    """ This is a simple example of a middleware that checks if the Authorization header is present in the request. 
        If it is not present, it returns a 401 status code with a message.
        
    ***
    @app.middleware("http")
    async def authorization(request: Request, call_next):
        if "Authorization" in request.headers:
            return JSONResponse(
                content={
                    "message": "Not authorized",
                    "resolution": "Please provide the right credentials to proceed"
                },
                status_code=status.HTTP_401_UNAUTHORIZED
            )
            
        response = await call_next(request)
        return response
    ***
    
    """
