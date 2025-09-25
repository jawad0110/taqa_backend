from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from src.db.main import get_session
from src.auth.dependencies import get_current_user
from src.db.models import User

from .schemas import WishlistModel, WishlistCreateModel, WishlistResponseModel
from .service import WishlistService

user_wishlist_router = APIRouter()


@user_wishlist_router.get("/", response_model=List[WishlistResponseModel])
async def get_wishlist(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get user's wishlist items"""
    service = WishlistService(session)
    wishlist_items = await service.get_wishlist(str(current_user.uid))
    
    # Convert to response model with product details
    response_items = []
    for item in wishlist_items:
        if item.product:
            # Build a lightweight product summary compatible with Pydantic models
            main_image = None
            if getattr(item.product, 'images', None):
                main = next((img for img in item.product.images if getattr(img, 'is_main', False)), None)
                if main:
                    main_image = main.filename

            # Calculate stock status similar to products service
            product_stock = getattr(item.product, 'stock', 0)
            variants = getattr(item.product, 'variant_groups', [])
            
            # Determine stock status
            if variants:
                # Check if any variant is in stock
                any_variant_in_stock = False
                for variant_group in variants:
                    for choice in getattr(variant_group, 'choices', []):
                        variant_stock = getattr(choice, 'stock', None)
                        if variant_stock is not None:
                            if variant_stock > 0:
                                any_variant_in_stock = True
                                break
                stock_status = 'In Stock' if any_variant_in_stock else 'Out of Stock'
            else:
                # For products without variants, use the product stock
                stock_status = 'In Stock' if product_stock and product_stock > 0 else 'Out of Stock'
            
            product_summary = {
                "uid": str(item.product.uid),
                "title": item.product.title,
                "price": float(item.product.price),
                "main_image": main_image,
                "in_stock": stock_status == 'In Stock',
                "stock_status": stock_status,
                "images": [
                    {"uid": img.uid, "filename": img.filename, "is_main": img.is_main}
                    for img in getattr(item.product, 'images', [])
                ]
            }

            response_items.append(WishlistResponseModel(
                uid=str(item.uid),
                product_uid=str(item.product_uid),
                added_at=item.added_at,
                product=product_summary
            ))
    
    return response_items


@user_wishlist_router.post("/", response_model=WishlistModel, status_code=status.HTTP_201_CREATED)
async def add_to_wishlist(
    wishlist_data: WishlistCreateModel,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Add a product to user's wishlist"""
    service = WishlistService(session)
    try:
        wishlist_item = await service.add_to_wishlist(
            str(current_user.uid),
            wishlist_data.product_uid
        )
        return WishlistModel(
            uid=str(wishlist_item.uid),
            user_uid=str(wishlist_item.user_uid),
            product_uid=str(wishlist_item.product_uid),
            added_at=wishlist_item.added_at,
            updated_at=wishlist_item.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@user_wishlist_router.delete("/{product_uid}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_wishlist(
    product_uid: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Remove a product from user's wishlist"""
    service = WishlistService(session)
    removed = await service.remove_from_wishlist(str(current_user.uid), product_uid)
    
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Product not found in wishlist"
        )


@user_wishlist_router.get("/check/{product_uid}")
async def check_wishlist_status(
    product_uid: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Check if a product is in user's wishlist"""
    service = WishlistService(session)
    is_in_wishlist = await service.is_in_wishlist(str(current_user.uid), product_uid)
    
    return {"is_in_wishlist": is_in_wishlist}


@user_wishlist_router.get("/count")
async def get_wishlist_count(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get the count of items in user's wishlist"""
    service = WishlistService(session)
    count = await service.get_wishlist_count(str(current_user.uid))
    
    return {"count": count}


@user_wishlist_router.post("/batch-check")
async def batch_check_wishlist_status(
    product_uids: List[str],
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Check wishlist status for multiple products at once"""
    service = WishlistService(session)
    status_map = await service.batch_check_wishlist_status(str(current_user.uid), product_uids)
    
    return {"status_map": status_map}
