import logging
from fastapi import APIRouter, Depends, Query, HTTPException, status
from .schemas import (
    Product,
    ProductDetail,
    PaginatedProductResponse
)
from sqlmodel.ext.asyncio.session import AsyncSession
from src.admin_dashboard.products.service import SortField, SortOrder
from .service import ProductService
from src.db.main import get_session
from typing import List, Optional, Union
from src.auth.dependencies import AccessTokenBearer, RoleChecker, get_optional_current_user
from src.errors import ProductNotFound
import math

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

user_product_router = APIRouter()
access_token_bearer = AccessTokenBearer()

# Different role checkers for different operations
user_role_checker = Depends(RoleChecker(['admin', 'user']))

@user_product_router.get(
    "/",
    response_model=PaginatedProductResponse,
    summary="List products for users (with images)",
    responses={
        200: {"description": "Paginated list of products returned."},
        500: {"description": "Internal server error."}
    }
)
async def get_all_products(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for product name or description"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    in_stock: Optional[bool] = Query(None, description="Filter by stock availability"),
    sort_by: Optional[SortField] = Query(None, description="Field to sort by"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order"),
    session: AsyncSession = Depends(get_session),
    token_details: Optional[dict] = Depends(get_optional_current_user)
):
    """
    List all products available to users, with pagination, filtering, and sorting.
    Each product includes its images (main and additional).
    Returns 500 for unexpected errors.
    """
    try:
        # Check if user is admin (if logged in)
        is_admin = token_details and 'admin' in token_details.get('user', {}).get('roles', [])
        service = ProductService(session)
        # If any search parameters are provided, use search_products
        if search or category or min_price or max_price or in_stock:
            products = await service.search_products(
                query=search,
                category=category,
                min_price=min_price,
                max_price=max_price,
                stock=in_stock,
                visible_only=not is_admin
            )
            total = len(products)
            # Apply pagination manually
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_products = products[start_idx:end_idx]
            product_list = [Product.model_validate(product.model_dump()) for product in paginated_products]
            return {
                "items": product_list,
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": math.ceil(total / limit)
            }
        else:
            # Otherwise use get_all_products with sorting
            products, total_count = await service.get_all_products(
                visible_only=not is_admin,
                page=page,
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order
            )
            product_list = [Product.model_validate(product.model_dump()) for product in products]
            return {
                "items": product_list,
                "total": total_count,
                "page": page,
                "limit": limit,
                "total_pages": math.ceil(total_count / limit)
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve products")


@user_product_router.get(
    "/{product_uid}",
    response_model=Union[ProductDetail],
    summary="Get product details (with images)",
    responses={
        200: {"description": "Product details returned."},
        404: {"description": "Product not found."},
        500: {"description": "Internal server error."}
    }
)
async def get_product(
    product_uid: str,
    variant_id: Optional[str] = Query(None, description="ID of the selected variant"),
    session: AsyncSession = Depends(get_session),
    token_details: Optional[dict] = Depends(get_optional_current_user)
):
    """
    Retrieve full details for a product, including all associated images.
    Shows which image is the main image.
    
    If a variant_id is provided, the stock status will reflect the selected variant.
    Otherwise, the stock status will show as in stock if any variant is in stock.
    
    Returns 404 if the product does not exist.
    Returns 500 for unexpected errors.
    """
    try:
        product_service = ProductService(session)
        product = await product_service.get_product(product_uid, session, variant_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # The product is already a ProductDetail model with stock info
        # No need to modify it further
        return product
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve product details")