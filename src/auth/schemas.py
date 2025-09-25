from pydantic import BaseModel, Field
from src.admin_dashboard.products.schemas import Product
from src.admin_dashboard.reviews.schemas import ReviewModel
import uuid
from datetime import datetime
from typing import List

class UserCreateModel(BaseModel):
    first_name: str = Field(max_length=25)
    last_name: str = Field(max_length=25)
    username: str = Field(max_length=8)
    email: str = Field(max_length=40)
    password: str = Field(min_length=6)
    
class UserModel(BaseModel):
    __tablename__ = 'users'
    uid : uuid.UUID
    username : str
    email : str
    first_name : str
    last_name : str
    is_verified : bool
    password_hash : str = Field(exclude=True)
    created_at: datetime
    updated_at: datetime
    
class UserProductModel(UserModel):
    products: List[Product]
    reviews: List[ReviewModel]

class UserLoginModel(BaseModel):
    email: str = Field(max_length=40)
    password: str = Field(min_length=6)
    
    
class EmailModel(BaseModel):
    addresses: List[str]
    
    
class PasswordResetRequestModel(BaseModel):
    email: str
    
class PasswordResetConfirmModel(BaseModel):
    new_password: str
    confirm_new_password: str