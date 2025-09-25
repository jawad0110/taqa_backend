from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Dict, Optional

from src.db.main import get_session
from src.auth.dependencies import get_current_user
from src.db.models import User

from .schemas import CartModel, CartCreateModel, CartUpdateModel
from .service import CartService

user_cart_router = APIRouter()

@user_cart_router.get("/", response_model=List[CartModel])
async def get_cart(
    session: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user),
):
    service = CartService(session)
    return await service.get_cart(str(current_user.uid))

@user_cart_router.post("/", response_model=CartModel, status_code=status.HTTP_201_CREATED)
async def add_item(
    cart_data: CartCreateModel,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    service = CartService(session)
    item = await service.add_item(
        str(current_user.uid),
        str(cart_data.product_uid),
        cart_data.quantity,
        str(cart_data.variant_choice_id) if cart_data.variant_choice_id else None
    )
    return item

@user_cart_router.patch("/{product_uid}", response_model=CartModel)
async def update_item(
    product_uid: str,
    cart_data: CartUpdateModel,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    service = CartService(session)
    raw_item = await service.update_item_quantity(
        str(current_user.uid),
        product_uid,
        cart_data.quantity,
        str(cart_data.variant_choice_id) if cart_data.variant_choice_id else None
    )
    # Convert raw Cart object to CartModel
    if raw_item is None:
        # Item was deleted (quantity was 0)
        return {"message": "Item removed from cart"}
    
    # Refresh relationships
    await session.refresh(raw_item, attribute_names=["product", "variant_choice"])
    
    # Create CartModel with proper price calculation
    price = raw_item.product.price
    if raw_item.variant_choice and raw_item.variant_choice.extra_price:
        price += raw_item.variant_choice.extra_price
    
    # Calculate total price
    total_price = price * raw_item.quantity
    
    # Get stock information
    stock = raw_item.product.stock
    if raw_item.variant_choice and raw_item.variant_choice.stock is not None:
        stock = raw_item.variant_choice.stock
    
    return CartModel(
        uid=raw_item.uid,
        product_uid=raw_item.product_uid,
        variant_choice_id=raw_item.variant_choice_id,
        product_title=raw_item.product.title,
        main_image_url=None,  # This would typically be fetched from product images
        quantity=raw_item.quantity,
        price=price,
        total_price=total_price,
        user_uid=raw_item.user_uid,
        added_at=raw_item.added_at,
        updated_at=raw_item.updated_at,
        stock=stock,
    )

@user_cart_router.delete("/{product_uid}", response_model=Dict[str, str])
async def remove_item(
    product_uid: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    service = CartService(session)
    await service.remove_item(str(current_user.uid), product_uid)
    return {"message": "item removed"}



@user_cart_router.get("/totals", response_model=Dict[str, float])
async def get_totals(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    discount_code: Optional[str] = Query(None)
):
    service = CartService(session)
    totals = await service.calculate_totals(str(current_user.uid), discount_code)
    return totals


@user_cart_router.delete("/", response_model=Dict[str, str])
async def clear_cart(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    service = CartService(session)
    await service.clear_cart(str(current_user.uid))
    return {"message": "cart cleared"}