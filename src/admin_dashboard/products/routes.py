from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional, Dict, Any
from src.db.models import ProductImage, Product
from src.admin_dashboard.products.service import ProductService, SortField, SortOrder, get_product_stock_info
from src.admin_dashboard.products.schemas import (
    ProductCreateModel, ProductUpdateModel,
    PaginatedProductResponse, ProductDetailModel, ProductImageRead,
    VariantGroupCreate, VariantGroupUpdate, VariantGroupRead,
    VariantChoiceUpdate, VariantChoiceRead
)
from src.auth.dependencies import admin_role_checker, get_current_user, AccessTokenBearer
from src.db.main import get_session
from sqlmodel import select, SQLModel
import math
import os
import shutil
import uuid
from fastapi.responses import JSONResponse
import logging

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

product_router = APIRouter()
access_token_bearer = AccessTokenBearer()

# --- Product Image Management Endpoints ---
from src.admin_dashboard.products.schemas import ProductImageRead

@product_router.post(
    "/{product_uid}/main_image",
    response_model=ProductImageRead,
    summary="Add or replace the main image for a product",
    responses={
        200: {"description": "Main image added or replaced successfully."},
        400: {"description": "Validation error or business constraint violation."},
        404: {"description": "Product not found."},
        413: {"description": "File too large."},
        415: {"description": "Unsupported media type."},
        500: {"description": "Internal server error."}
    }
)
async def add_or_replace_main_image(
    product_uid: str,
    file: UploadFile = File(..., media_type='image/*', alias='file'),
    _: bool = Depends(admin_role_checker)
):
    """
    Add or replace the main image for a product.
    If a main image exists, it will be deleted and replaced with the new one.
    Business rules enforced: only one main image per product.
    
    Args:
        product_uid: The UID of the product
        file: The image file to upload (JPEG, PNG, or WebP, max 10MB)
        
    Returns:
        The created ProductImage object
        
    Raises:
        HTTPException: If there's an error processing the request
    """
    logger.info(f"Starting main image upload for product {product_uid}")
    
    # Validate file is provided
    if not file:
        logger.error("No file provided in the request")
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Log file metadata
    logger.info(f"File metadata - filename: {file.filename}, content_type: {file.content_type}, size: {getattr(file, 'size', 'unknown')}")
    
    # Get a new session using the async generator pattern
    session_gen = get_session()
    session = await session_gen.__anext__()
    try:
        async with session.begin():
            service = ProductService(session)
            
            # Check if product exists
            logger.info(f"Checking if product {product_uid} exists")
            try:
                # First check if product_uid is a valid UUID
                from uuid import UUID
                UUID(product_uid)
                
                # Fetch the product using direct SQLAlchemy query
                from sqlalchemy import select
                stmt = select(Product).where(Product.uid == product_uid)
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()
                
                if not product:
                    logger.error(f"Product {product_uid} not found in database")
                    raise HTTPException(status_code=404, detail=f"Product with ID {product_uid} not found")
                
                # Ensure we have a fresh instance
                await session.refresh(product)
                logger.info(f"Product found - ID: {product.uid}, Title: {getattr(product, 'title', 'N/A')}")
                
            except ValueError as ve:
                logger.error(f"Invalid product UID format: {product_uid}")
                raise HTTPException(status_code=400, detail=f"Invalid product UID format: {product_uid}")
            except HTTPException as he:
                # Re-raise HTTP exceptions as they are
                logger.error(f"HTTP Exception while fetching product: {he.detail}")
                raise
            except Exception as e:
                # Log the full exception details for debugging
                logger.error(f"Unexpected error fetching product {product_uid}: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=500, 
                    detail=f"Error fetching product information: {str(e)}"
                )
            
            # Get all images for the product
            logger.info("Fetching existing images for product")
            images = (await session.execute(select(ProductImage).where(ProductImage.product_uid == product_uid))).scalars().all()
            logger.info(f"Found {len(images)} existing images")
        
            # Delete existing main image if it exists
            main_img = next((img for img in images if img.is_main), None)
            if main_img:
                try:
                    logger.info(f"Found existing main image {main_img.filename}, deleting it")
                    # Delete the file from disk
                    await service.delete_image_from_disk(product_uid, main_img.filename)
                    # Delete the database record
                    await session.delete(main_img)
                    await session.flush()
                    logger.info("Successfully deleted old main image")
                except Exception as e:
                    logger.error(f"Error deleting old main image: {str(e)}", exc_info=True)
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to remove existing main image: {str(e)}"
                    )
            
            # Create new main image
            try:
                logger.info("Validating image file")
                # Validate file type
                ext = await service.validate_image_file(file)
                logger.info(f"File validation passed, extension: {ext}")
                
                # Generate unique filename
                filename = await service.generate_unique_filename(product.title, product_uid, ext)
                logger.info(f"Generated filename: {filename}")
                
                # Save file to disk
                logger.info("Saving file to disk")
                await service.save_image_to_disk(file, product_uid, filename)
                logger.info("File saved to disk successfully")
                
                # Create database record
                logger.info("Creating database record")
                img = ProductImage(
                    product_uid=product_uid,
                    filename=filename,
                    is_main=True
                )
                session.add(img)
                await session.flush()
                await session.refresh(img)
                logger.info(f"Database record created with ID: {img.uid}")
                
                # Convert SQLAlchemy model to Pydantic model
                img_dict = img.__dict__.copy()
                # Remove SQLAlchemy internal attributes
                img_dict.pop('_sa_instance_state', None)
                
                logger.info("Returning success response")
                return ProductImageRead(**img_dict)
                
            except HTTPException as he:
                logger.error(f"HTTPException in image processing: {str(he.detail)}")
                raise
            except Exception as e:
                logger.error(f"Error creating new main image: {str(e)}", exc_info=True)
                # Clean up if file was created but DB operation failed
                try:
                    if 'filename' in locals():
                        logger.info(f"Cleaning up file: {filename}")
                        await service.delete_image_from_disk(product_uid, filename)
                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup: {str(cleanup_error)}")
                
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create new main image: {str(e)}"
                )
                
    except HTTPException as he:
        logger.error(f"HTTPException in add_or_replace_main_image: {str(he.detail)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in add_or_replace_main_image: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )
    finally:
        # Ensure the session is properly closed
        try:
            await session.close()
        except Exception as e:
            logger.error(f"Error closing session: {str(e)}")

@product_router.post(
    "/{product_uid}/additional_images",
    response_model=ProductImageRead,
    summary="Add an additional image to a product (max 4)",
    responses={
        200: {"description": "Additional image added successfully."},
        400: {"description": "Too many additional images or invalid image."},
        404: {"description": "Product not found."},
        500: {"description": "Internal server error."}
    }
)
async def add_additional_image(
    product_uid: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    Add an additional image to a product. Maximum of 4 additional images allowed.
    Business rules enforced: up to 4 additional images per product.
    Returns 500 for unexpected errors.
    """
    try:
        # Don't use a transaction context manager here
        service = ProductService(session)
        img = await service.add_additional_image(session, product_uid, file)
        
        # Convert SQLAlchemy model to Pydantic model
        img_dict = img.__dict__.copy()
        # Remove SQLAlchemy internal attributes
        img_dict.pop('_sa_instance_state', None)
        return ProductImageRead(**img_dict)
    except HTTPException as he:
        await session.rollback()
        raise
    except Exception as e:
        logger.error(f"Error in add_additional_image: {str(e)}", exc_info=True)
        await session.rollback()
        raise HTTPException(status_code=500, detail="Failed to add additional image")

@product_router.patch(
    "/{product_uid}/images/{image_uid}",
    response_model=ProductImageRead,
    summary="Toggle the is_main flag for a product image",
    responses={
        200: {"description": "Main image toggled successfully."},
        400: {"description": "Business rule violation (e.g., no main image left)."},
        404: {"description": "Product or image not found."},
        500: {"description": "Internal server error."}
    }
)
async def toggle_image_is_main(
    product_uid: str,
    image_uid: str,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    Toggle the is_main flag for a product image.
    Ensures only one main image exists for the product at any time.
    Returns 500 for unexpected errors.
    """
    try:
        # Create a new service instance with the session
        service = ProductService(session)
        
        # Get the image to be toggled
        img = await service.toggle_image_is_main(product_uid, image_uid)
        
        # Commit the transaction
        await session.commit()
        
        # Convert SQLAlchemy model to Pydantic model
        img_dict = img.__dict__.copy()
        # Remove SQLAlchemy internal attributes
        img_dict.pop('_sa_instance_state', None)
        return ProductImageRead(**img_dict)
        
    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error in toggle_image_is_main: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to toggle main image")
    finally:
        await session.close()

@product_router.delete(
    "/{product_uid}/images/{image_uid}",
    status_code=204,
    summary="Delete a product image",
    responses={
        204: {"description": "Image deleted successfully."},
        400: {"description": "Cannot delete last/main image without replacement."},
        404: {"description": "Product or image not found."},
        500: {"description": "Internal server error."}
    }
)
async def delete_product_image(
    product_uid: str,
    image_uid: str,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    Delete a product image.
    Enforces constraints: cannot delete the only image or main image without replacement.
    Returns 500 for unexpected errors.
    """
    try:
        service = ProductService(session)
        await service.delete_product_image(product_uid, image_uid)
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete product image")

@product_router.get(
    "/{product_uid}/images",
    response_model=List[ProductImageRead],
    summary="List all images for a product",
    responses={
        200: {"description": "List of images returned."},
        404: {"description": "Product not found."}
    }
)
async def list_product_images(
    product_uid: str,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    List all images for a product (admin view).
    """
    images = (await session.exec(select(ProductImage).where(ProductImage.product_uid == product_uid))).all()
    return images


@product_router.post(
    "/",
    response_model=Product,
    summary="Create a new product",
    responses={
        200: {"description": "Product created successfully."},
        400: {"description": "Validation error or business constraint violation."},
        500: {"description": "Internal server error."}
    }
)
async def create_product(
    product_data: ProductCreateModel,
    session: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user),
    _: bool = Depends(admin_role_checker)
):
    """
    Create a new product. Returns 500 for unexpected errors.
    """
    try:
        product_service = ProductService(session)
        product = await product_service.create_product(product_data, current_user.uid, session)
        
        # Convert product to dict and ensure UUIDs and datetimes are strings
        product_dict = product.model_dump()
        
        # Convert UUIDs to strings
        product_dict['uid'] = str(product_dict['uid'])
        if 'user_uid' in product_dict:
            product_dict['user_uid'] = str(product_dict['user_uid'])
            
        # Convert datetimes to ISO format strings
        if 'created_at' in product_dict:
            product_dict['created_at'] = product_dict['created_at'].isoformat()
        if 'updated_at' in product_dict and product_dict['updated_at']:
            product_dict['updated_at'] = product_dict['updated_at'].isoformat()
            
        return JSONResponse(
            content={
                "message": "Product created successfully",
                "product": product_dict
            },
            status_code=status.HTTP_201_CREATED
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create product: {str(e)}"
        )

@product_router.get(
    "/{product_uid}",
    response_model=ProductDetailModel,
    summary="Get product details (admin)",
    responses={
        200: {"description": "Product details returned."},
        404: {"description": "Product not found."},
        500: {"description": "Internal server error."}
    }
)
async def get_product(
    product_uid: str,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(access_token_bearer),
    _: bool = Depends(admin_role_checker)
):
    """
    Retrieve product details for admin, with all variants. Returns 404 if not found, 500 for unexpected errors.
    """
    try:
        # Initialize ProductService
        product_service = ProductService(session)
        
        # Get product from database
        product = await product_service.get_product(product_uid, session)
        if not product:
            return JSONResponse(
                status_code=404,
                content={"message": "Product doesn't exist"}
            )
        
        # The product is already a dictionary from the service
        product_dict = product
        
        logger.info(f"Final product dict: {product_dict}")
        return product_dict
    except Exception as e:
        logger.error(f"Error in get_product: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to retrieve product details"}
        )


@product_router.post(
    "/{product_uid}/variant_groups",
    response_model=VariantGroupRead,
    summary="Create a variant group for a product",
    responses={
        200: {"description": "Variant group created successfully."},
        400: {"description": "Validation error or business constraint violation."},
        404: {"description": "Product not found."},
        500: {"description": "Internal server error."}
    }
)
async def create_variant_group(
    product_uid: uuid.UUID,
    group_data: VariantGroupCreate,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    Create a variant group for a product. Returns 500 for unexpected errors.
    """
    try:
        service = ProductService(session)
        group = await service.create_variant_group(product_uid, group_data)
        return group
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create variant group")

@product_router.put(
    "/{product_uid}/variant_groups/{group_id}",
    response_model=VariantGroupRead,
    summary="Update a variant group for a product",
    responses={
        200: {"description": "Variant group updated successfully."},
        400: {"description": "Validation error or business constraint violation."},
        404: {"description": "Product or group not found."},
        500: {"description": "Internal server error."}
    }
)
async def update_variant_group(
    product_uid: uuid.UUID,
    group_id: uuid.UUID,
    group_data: VariantGroupUpdate,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    Update a variant group for a product. Returns 500 for unexpected errors.
    """
    try:
        service = ProductService(session)
        group = await service.update_variant_group(product_uid, group_id, group_data)
        return group
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update variant group")

@product_router.delete(
    "/{product_uid}/variant_groups/{group_id}",
    status_code=204,
    summary="Delete a variant group from a product",
    responses={
        204: {"description": "Variant group deleted successfully."},
        404: {"description": "Product or group not found."},
        500: {"description": "Internal server error."}
    }
)
async def delete_variant_group(
    product_uid: uuid.UUID,
    group_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    Delete a variant group from a product. Returns 500 for unexpected errors.
    """
    try:
        service = ProductService(session)
        await service.delete_variant_group(product_uid, group_id)
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete variant group")

@product_router.patch(
    "/{product_uid}/variant_choices/{choice_id}",
    response_model=VariantChoiceRead,
    summary="Update a variant choice for a product",
    responses={
        200: {"description": "Variant choice updated successfully."},
        400: {"description": "Validation error or business constraint violation."},
        404: {"description": "Product or choice not found."},
        500: {"description": "Internal server error."}
    }
)
async def update_variant_choice(
    product_uid: uuid.UUID,
    choice_id: uuid.UUID,
    choice_data: VariantChoiceUpdate,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    Update a variant choice for a product. Returns 500 for unexpected errors.
    """
    try:
        service = ProductService(session)
        choice = await service.update_variant_choice(product_uid, choice_id, choice_data)
        return choice
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update variant choice")

@product_router.delete(
    "/{product_uid}/variant_choices/{choice_id}",
    status_code=204,
    summary="Delete a variant choice from a product",
    responses={
        204: {"description": "Variant choice deleted successfully."},
        404: {"description": "Product or choice not found."},
        500: {"description": "Internal server error."}
    }
)
async def delete_variant_choice(
    product_uid: uuid.UUID,
    choice_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    Delete a variant choice from a product. Returns 500 for unexpected errors.
    """
    try:
        service = ProductService(session)
        await service.delete_variant_choice(product_uid, choice_id)
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete variant choice")

@product_router.get("/", response_model=PaginatedProductResponse, dependencies=[Depends(admin_role_checker)])
async def get_products(
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(access_token_bearer),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),  # Increased from 10 to 20
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None
):
    product_service = ProductService(session)
    
    # If any search parameters are provided, use search_products
    if search or min_price or max_price or in_stock:
        products = await product_service.search_products(
            session=session,
            query=search,
            min_price=min_price,
            max_price=max_price,
            in_stock=in_stock
        )
        total = len(products)
        
        # Apply pagination manually
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_products = products[start_idx:end_idx]
        
        return PaginatedProductResponse(
            items=paginated_products,
            total=total,
            page=page,
            limit=limit,
            total_pages=math.ceil(total / limit)
        )
    else:
        # Otherwise use get_all_products with sorting
        sort_field = None
        if sort_by:
            try:
                sort_field = SortField(sort_by)
            except ValueError:
                pass
                
        sort_order_enum = SortOrder.DESC
        if sort_order and sort_order.lower() == "asc":
            sort_order_enum = SortOrder.ASC
            
        products, total = await product_service.get_all_products(
            session=session,
            page=page,
            limit=limit,
            sort_by=sort_field,
            sort_order=sort_order_enum
        )
        
        return PaginatedProductResponse(
            items=products,
            total=total,
            page=page,
            limit=limit,
            total_pages=math.ceil(total / limit)
        )

@product_router.patch(
    "/{product_uid}",
    response_model=Product,
    summary="Update a product",
    responses={
        200: {"description": "Product updated successfully."},
        400: {"description": "Validation error or business constraint violation."},
        404: {"description": "Product not found."},
        500: {"description": "Internal server error."}
    }
)
async def update_product(
    product_uid: str,
    update_data: ProductUpdateModel,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(access_token_bearer),
    _: bool = Depends(admin_role_checker)
):
    """
    Update a product. Returns 404 if not found, 500 for unexpected errors.
    """
    try:
        product_service = ProductService(session)
        product = await product_service.update_product(product_uid, update_data, session)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update product")

@product_router.delete(
    "/{product_uid}",
    status_code=status.HTTP_200_OK,
    summary="Delete a product",
    responses={
        200: {"description": "Product deleted successfully."},
        404: {"description": "Product not found."},
        500: {"description": "Internal server error."}
    }
)
async def delete_product(
    product_uid: str,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(admin_role_checker)
):
    """
    Delete a product. Returns 404 if not found, 500 for unexpected errors.
    """
    try:
        product_service = ProductService(session)
        result = await product_service.delete_product(product_uid, session)
        
        if result is None:
            return JSONResponse(
                status_code=404,
                content={"message": "Product doesn't exist"}
            )
        
        # Check if result is a dictionary with special handling
        if isinstance(result, dict):
            # Handle error case
            if "error" in result:
                if result["error"] == "cannot_delete_ordered_product":
                    return JSONResponse(
                        status_code=400,
                        content={"message": result["message"]}
                    )
            # Handle soft delete case
            elif "soft_deleted" in result and result["soft_deleted"]:
                return JSONResponse(
                    status_code=200,
                    content={"message": result["message"], "soft_deleted": True}
                )
        
        return {"message": "Product deleted successfully"}
    except Exception as e:
        logger.error(f"Error in delete_product: {str(e)}", exc_info=True)
        # Check for specific constraint violation errors
        error_message = str(e)
        if "violates foreign key constraint" in error_message:
            return JSONResponse(
                status_code=400,
                content={"message": "Cannot delete product because it is referenced by other items"}
            )
        elif "violates not-null constraint" in error_message:
            return JSONResponse(
                status_code=400,
                content={"message": "Cannot delete product because it has related items"}
            )
        else:
            return JSONResponse(
                status_code=500,
                content={"message": "Failed to delete product. Please try again later."}
            )