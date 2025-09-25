from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, desc, and_, or_
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import func, delete
from src.db.models import VariantGroup, VariantChoice
from typing import List, Optional, Tuple, Union
from src.admin_dashboard.products.schemas import (
    ProductCreateModel, ProductUpdateModel,
    PaginatedResponse, Product, ProductAdmin,
)
from src.db.models import Product, VariantGroup, VariantChoice
from src.db.models import Wishlist, Cart
from src.errors import ProductNotFound
from src.errors import (
    MissingMainImageError, InvalidImageTypeError, TooManyAdditionalImagesError, DeletionConstraintError
)
from src.db.models import ProductImage
import os
from fastapi import UploadFile
import imghdr
from src.admin_dashboard.products.schemas import (
    VariantGroupCreate, VariantGroupUpdate, VariantChoiceUpdate,
    VariantGroupRead, VariantChoiceRead
)
from sqlalchemy import func
from typing import List, Optional, Union, Tuple
import uuid
import logging
from enum import Enum

logger = logging.getLogger(__name__)

def get_product_stock_info(product_model):
    """
    Get stock information for a product and its variants.
    
    Args:
        product_model: SQLAlchemy Product model instance
        
    Returns:
        dict: Stock information including product and variants
    """
    try:
        # Initialize total stock
        total_stock = 0
        has_variants = False
        variants = []
        
        # Check if product has variant groups with choices
        if hasattr(product_model, 'variant_groups') and product_model.variant_groups:
            # Calculate total stock from all variant choices
            for group in product_model.variant_groups:
                if hasattr(group, 'choices') and group.choices:
                    has_variants = True
                    for choice in group.choices:
                        choice_stock = getattr(choice, 'stock', 0)
                        total_stock += choice_stock
                        variants.append({
                            'variant': getattr(choice, 'value', None),
                            'stock': choice_stock,
                            'status': 'In Stock' if choice_stock > 0 else 'Out of Stock'
                        })
        
        # If product has variants, use the sum of variant stocks
        if has_variants:
            stock_status = 'In Stock' if total_stock > 0 else 'Out of Stock'
            return {
                'stock': total_stock,
                'stock_status': stock_status,
                'has_variants': True,
                'variants': variants
            }
        # Otherwise, use the product's stock
        else:
            product_stock = getattr(product_model, 'stock', 0)
            return {
                'stock': product_stock,
                'stock_status': 'In Stock' if product_stock > 0 else 'Out of Stock',
                'has_variants': False,
                'variants': variants
            }
            
    except Exception as e:
        logger.error(f"Error in get_product_stock_info: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve stock information")

class SortField(str, Enum):
    PRICE = "price"
    DATE = "date"
    NAME = "name"
    QUANTITY = "quantity"

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(__name__)

    # ------------------- IMAGE MANAGEMENT -------------------
    async def validate_image_file(self, file: UploadFile):
        """
        Validate the uploaded file for allowed image types and extensions.
        Allowed: jpeg, png, webp, jpg
        """
        allowed_types = ["jpeg", "png", "webp", "jpg"]
        ext = os.path.splitext(file.filename)[1].lower().replace('.', '')
        if ext not in allowed_types:
            raise InvalidImageTypeError()
        # Read a small chunk to check content type
        content = await file.read(512)
        file.file.seek(0)
        kind = imghdr.what(None, content)
        if kind not in allowed_types:
            raise InvalidImageTypeError()
        return ext

    async def generate_unique_filename(self, product_title: str, product_uid: str, extension: str) -> str:
        """
        Generate a unique filename for the image based on product title and next index.
        """
        safe_title = product_title.replace(' ', '_').lower()
        base_dir = f"static/images/products/{product_uid}"
        os.makedirs(base_dir, exist_ok=True)
        existing = [f for f in os.listdir(base_dir) if f.startswith(safe_title) and f.endswith(f'.{extension}')]
        indices = [int(f.split('_')[-1].split('.')[0]) for f in existing if f.split('_')[-1].split('.')[0].isdigit()]
        next_index = max(indices, default=0) + 1
        return f"{safe_title}_{next_index}.{extension}"

    async def save_image_to_disk(self, file: UploadFile, product_uid: str, filename: str) -> str:
        """
        Save the image file to static/images/products/{product_uid}/
        """
        try:
            self.logger.info(f"Saving image to disk. Product UID: {product_uid}, Filename: {filename}")
            
            # Ensure the base directory exists
            base_dir = os.path.abspath(f"static/images/products/{product_uid}")
            self.logger.info(f"Base directory: {base_dir}")
            
            # Create directory if it doesn't exist
            os.makedirs(base_dir, exist_ok=True)
            self.logger.info("Directory created or already exists")
            
            # Create full file path
            file_path = os.path.join(base_dir, filename)
            self.logger.info(f"Full file path: {file_path}")
            
            # Ensure the directory is writable
            if not os.access(os.path.dirname(file_path), os.W_OK):
                error_msg = f"Directory is not writable: {os.path.dirname(file_path)}"
                self.logger.error(error_msg)
                raise IOError(error_msg)
            
            # Read file content
            content = await file.read()
            self.logger.info(f"Read {len(content)} bytes from uploaded file")
            
            # Write to disk
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Verify file was written
            if not os.path.exists(file_path):
                error_msg = f"Failed to save file: {file_path}"
                self.logger.error(error_msg)
                raise IOError(error_msg)
                
            file_size = os.path.getsize(file_path)
            self.logger.info(f"Successfully saved {file_size} bytes to {file_path}")
            
            # Reset file pointer
            file.file.seek(0)
            
            return file_path
            
        except Exception as e:
            self.logger.error(f"Error in save_image_to_disk: {str(e)}", exc_info=True)
            raise

    async def delete_image_from_disk(self, product_uid: str, filename: str):
        """
        Delete the image file from static/images/products/{product_uid}/
        """
        file_path = os.path.join(f"static/images/products/{product_uid}", filename)
        if os.path.exists(file_path):
            os.remove(file_path)

    async def create_product_image(self, session: AsyncSession, product_uid: str, file: UploadFile, is_main: bool = False):
        """
        Create a ProductImage for a product, enforcing all constraints.
        """
        # Validate image
        ext = await self.validate_image_file(file)
        # Get product
        product = await session.get(Product, product_uid)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found.")
        # Get all images for product
        result = await session.exec(select(ProductImage).where(ProductImage.product_uid == product_uid))
        images = result.all()
        main_images = [img for img in images if img.is_main]
        additional_images = [img for img in images if not img.is_main]
        if is_main and main_images:
            raise DeletionConstraintError("Product already has a main image. Use swap_main_image or toggle.")
        if not is_main and len(additional_images) >= 4:
            raise TooManyAdditionalImagesError()
        # Generate filename and save
        filename = await self.generate_unique_filename(product.title, product_uid, ext)
        await self.save_image_to_disk(file, product_uid, filename)
        # Create DB record
        img = ProductImage(product_uid=product_uid, filename=filename, is_main=is_main)
        session.add(img)
        await session.commit()
        await session.refresh(img)
        return img

    async def swap_main_image(self, session: AsyncSession, product_uid: str, new_main_image_uid: str):
        """
        Swap the main image for a product, update DB and delete old main image file/record.
        """
        # Get all images for product
        result = await session.exec(select(ProductImage).where(ProductImage.product_uid == product_uid))
        images = result.all()
        if not images:
            raise MissingMainImageError()
        old_main = next((img for img in images if img.is_main), None)
        new_main = next((img for img in images if str(img.uid) == str(new_main_image_uid)), None)
        if not new_main:
            raise HTTPException(status_code=404, detail="New main image not found.")
        if not old_main:
            # No existing main image, just set the new one
            new_main.is_main = True
            session.add(new_main)
            await session.commit()
            return new_main
        # Swap
        old_main.is_main = False
        new_main.is_main = True
        session.add(old_main)
        session.add(new_main)
        await session.commit()
        # Refresh to get updated data
        await session.refresh(new_main)
        if old_main:
            await self.delete_image_from_disk(product_uid, old_main.filename)
            await session.delete(old_main)
            await session.commit()
        return new_main

    async def add_additional_image(self, session: AsyncSession, product_uid: str, file: UploadFile):
        """
        Add an additional image (up to 4). Enforce constraints.
        """
        return await self.create_product_image(session, product_uid, file, is_main=False)

    async def toggle_image_is_main(self, product_uid: str, image_uid: str):
        """
        Toggle the is_main flag for an image. Enforce only one main image per product.
        """
        images = (await self.db.exec(select(ProductImage).where(ProductImage.product_uid == product_uid))).all()
        if not images:
            raise MissingMainImageError()
        img = next((img for img in images if str(img.uid) == str(image_uid)), None)
        if not img:
            raise HTTPException(status_code=404, detail="Image not found.")
        if img.is_main:
            raise DeletionConstraintError("Image is already main.")
        # Unset current main
        for i in images:
            if i.is_main:
                i.is_main = False
        img.is_main = True
        await self.db.commit()
        await self.db.refresh(img)
        return img

    async def delete_product_image(self, product_uid: str, image_uid: str):
        """
        Delete a product image. Enforce constraints.
        """
        images = (await self.db.exec(select(ProductImage).where(ProductImage.product_uid == product_uid))).all()
        if not images:
            raise DeletionConstraintError("No images to delete.")
        img = next((img for img in images if str(img.uid) == str(image_uid)), None)
        if not img:
            raise HTTPException(status_code=404, detail="Image not found.")
        if len(images) == 1:
            raise DeletionConstraintError("Cannot delete the only image for a product.")
        if img.is_main:
            # Check if there is at least one other image to promote
            other = next((i for i in images if not i.is_main), None)
            if not other:
                raise DeletionConstraintError("Cannot delete main image without replacement.")
            other.is_main = True
        await self.delete_image_from_disk(product_uid, img.filename)
        await self.db.delete(img)
        await self.db.commit()
        return {"detail": "Image deleted."}

    # --- VARIANT GROUPS & CHOICES ---
    async def create_variant_group(self, product_uid: uuid.UUID, group_data: VariantGroupCreate):
        # Validate at least one choice
        if not group_data.choices or len(group_data.choices) == 0:
            raise HTTPException(status_code=400, detail="A variant group must have at least one choice.")
        # Validate product exists
        product = await self.db.get(Product, product_uid)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found.")
        group = VariantGroup(product_uid=product_uid, name=group_data.name)
        self.db.add(group)
        await self.db.flush()  # get group.id
        # Add choices
        for choice_data in group_data.choices:
            choice = VariantChoice(
                group_id=group.id,
                value=choice_data.value,
                stock=choice_data.stock,
                extra_price=choice_data.extra_price
            )
            self.db.add(choice)
        await self.db.commit()
        await self.db.refresh(group)
        await self.db.refresh(product)
        # Eager load choices for response
        await self.db.refresh(group)
        return group

    async def update_variant_group(self, product_uid: uuid.UUID, group_id: uuid.UUID, group_data: VariantGroupUpdate):
        try:
            self.logger.info(f"Starting update_variant_group for product_uid={product_uid}, group_id={group_id}")
            
            # Get the variant group with its choices using a proper query
            result = await self.db.execute(
                select(VariantGroup)
                .where(VariantGroup.id == group_id)
                .options(selectinload(VariantGroup.choices))
            )
            group = result.scalar_one_or_none()
            if not group or str(group.product_uid) != str(product_uid):
                self.logger.warning(f"Variant group not found: product_uid={product_uid}, group_id={group_id}")
                raise HTTPException(status_code=404, detail="Variant group not found for this product.")
            
            # Update group name if provided
            if group_data.name is not None:
                self.logger.info(f"Updating group name to: {group_data.name}")
                group.name = group_data.name
            
            # If choices provided, replace all choices
            if group_data.choices is not None:
                self.logger.info(f"Processing {len(group_data.choices)} new choices")
                
                # Delete old choices in a separate transaction
                try:
                    self.logger.info(f"Deleting old choices for group_id={group_id}")
                    await self.db.execute(
                        delete(VariantChoice).where(VariantChoice.group_id == group_id)
                    )
                    await self.db.commit()
                    self.logger.info("Successfully deleted old choices")
                except Exception as e:
                    await self.db.rollback()
                    self.logger.error(f"Error deleting old choices: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to delete existing choices: {str(e)}"
                    )
                
                # Add new choices
                try:
                    new_choices = []
                    for choice_data in group_data.choices:
                        choice = VariantChoice(
                            group_id=group_id,
                            value=choice_data.value,
                            stock=choice_data.stock,
                            extra_price=choice_data.extra_price
                        )
                        self.db.add(choice)
                        new_choices.append({
                            'value': choice_data.value,
                            'stock': choice_data.stock,
                            'extra_price': choice_data.extra_price
                        })
                    
                    await self.db.commit()
                    self.logger.info(f"Successfully added {len(new_choices)} new choices")
                    self.logger.debug(f"New choices: {new_choices}")
                    
                except Exception as e:
                    await self.db.rollback()
                    self.logger.error(f"Error adding new choices: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to add new choices: {str(e)}"
                    )
            
            # Refresh and return the updated group
            try:
                await self.db.refresh(group, ['choices'])
                self.logger.info("Successfully updated variant group")
                return group
            except Exception as e:
                self.logger.error(f"Error refreshing variant group: {str(e)}")
                # Even if refresh fails, we can still return the group
                return group
                
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in update_variant_group: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update variant group: {str(e)}"
            )
    async def delete_variant_group(self, product_uid: uuid.UUID, group_id: uuid.UUID):
        try:
            self.logger.info(f"Starting delete_variant_group for product_uid={product_uid}, group_id={group_id}")
            
            # Get the variant group with its choices using a proper query
            result = await self.db.execute(
                select(VariantGroup)
                .where(VariantGroup.id == group_id)
                .options(selectinload(VariantGroup.choices))
            )
            group = result.scalar_one_or_none()
            
            if not group or str(group.product_uid) != str(product_uid):
                self.logger.warning(f"Variant group not found: product_uid={product_uid}, group_id={group_id}")
                raise HTTPException(status_code=404, detail="Variant group not found for this product.")
            
            # Delete all choices for this group
            if group.choices:
                self.logger.info(f"Deleting {len(group.choices)} variant choices for group {group_id}")
                for choice in group.choices:
                    await self.db.delete(choice)
                await self.db.commit()
            
            # Now delete the group itself
            await self.db.delete(group)
            await self.db.commit()
            
            self.logger.info("Successfully deleted variant group and its choices")
            return {"detail": "Variant group and its choices deleted successfully."}
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error in delete_variant_group: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete variant group: {str(e)}"
            )

    async def update_variant_choice(self, product_uid: uuid.UUID, choice_id: uuid.UUID, choice_data: VariantChoiceUpdate):
        choice = await self.db.get(VariantChoice, choice_id)
        if not choice:
            raise HTTPException(status_code=404, detail="Variant choice not found.")
        group = await self.db.get(VariantGroup, choice.group_id)
        if not group or str(group.product_uid) != str(product_uid):
            raise HTTPException(status_code=404, detail="Variant choice does not belong to this product.")
        if choice_data.value is not None:
            choice.value = choice_data.value
        if choice_data.stock is not None:
            choice.stock = choice_data.stock
        if choice_data.extra_price is not None:
            choice.extra_price = choice_data.extra_price
        await self.db.commit()
        await self.db.refresh(choice)
        return choice

    async def delete_variant_choice(self, product_uid: uuid.UUID, choice_id: uuid.UUID):
        choice = await self.db.get(VariantChoice, choice_id)
        if not choice:
            raise HTTPException(status_code=404, detail="Variant choice not found.")
        group = await self.db.get(VariantGroup, choice.group_id)
        if not group or str(group.product_uid) != str(product_uid):
            raise HTTPException(status_code=404, detail="Variant choice does not belong to this product.")
        await self.db.delete(choice)
        await self.db.commit()
        return {"detail": "Variant choice deleted."}

    async def get_product_with_variants(self, product_uid: str):
        try:
            # Log the query being executed
            logger.info(f"Executing query for product UID: {product_uid}")
            
            statement = select(Product).options(
                joinedload(Product.variant_groups).joinedload(VariantGroup.choices),
                joinedload(Product.reviews)
            ).where(Product.uid == product_uid)
            
            result = await self.db.exec(statement)
            product = result.first()
            
            if not product:
                logger.warning(f"Product not found for UID: {product_uid}")
                raise HTTPException(status_code=404, detail="Product not found.")
            
            logger.info(f"Product found: {product.uid}")
            logger.info(f"Product has {len(product.variant_groups)} variant groups")
            logger.info(f"Product has {len(getattr(product, 'reviews', []))} reviews")
            
            # Convert product to dictionary - handle both model_dump and dict methods
            if hasattr(product, 'model_dump'):
                product_dict = product.model_dump()
            else:
                product_dict = product.dict()
            logger.info(f"Converted product to dict with keys: {list(product_dict.keys())}")
            
            # Get variant groups and choices
            variant_groups = []
            logger.info(f"Processing {len(product.variant_groups)} variant groups")
            
            for group in product.variant_groups:
                logger.info(f"Processing variant group: {group.name}")
                if hasattr(group, 'model_dump'):
                    group_dict = group.model_dump()
                else:
                    group_dict = group.dict()
                
                choices = []
                logger.info(f"Group {group.name} has {len(group.choices)} choices")
                
                for choice in group.choices:
                    logger.info(f"Processing choice: {choice.value}")
                    if hasattr(choice, 'model_dump'):
                        choice_dict = choice.model_dump()
                    else:
                        choice_dict = choice.dict()
                    
                    # Calculate final price by adding extra_price to product's price
                    choice_dict['final_price'] = product.price + (choice.extra_price or 0)
                    
                    # Use the product's available_stock property to determine availability
                    available_stock = getattr(product, 'available_stock', None)
                    logger.info(f"Available stock for product: {available_stock}")
                    logger.info(f"Choice stock: {choice.stock}")
                    
                    choice_dict['is_available'] = bool(available_stock is None or available_stock > 0 and choice.stock > 0)
                    logger.info(f"Choice {choice.value} is available: {choice_dict['is_available']}")
                    choices.append(choice_dict)
                
                group_dict['choices'] = choices
                variant_groups.append(group_dict)
            
            product_dict['variant_groups'] = variant_groups
            logger.info(f"Final product dict: {product_dict}")
            
            # Create a response model with calculated prices
            # First create a dictionary with product_price for each variant choice
            for group in product_dict['variant_groups']:
                for choice in group['choices']:
                    choice['product_price'] = product.price
            
            # Create response model
            try:
                # Try using model_validate if available (newer Pydantic v2)
                if hasattr(Product, 'model_validate'):
                    response = Product.model_validate(product_dict)
                    return response
                # Try using parse_obj if available (older Pydantic v1)
                elif hasattr(Product, 'parse_obj'):
                    response = Product.parse_obj(product_dict)
                    return response
                # If neither is available, try direct instantiation
                else:
                    response = Product(**product_dict)
                    return response
            except Exception as e:
                logger.error(f"Error creating response model: {str(e)}", exc_info=True)
                # Return the dictionary directly if model validation fails
                return product_dict
            
        except Exception as e:
            logger.error(f"Error in get_product_with_variants: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve product details")

    @staticmethod
    async def get_all_products(
        session: AsyncSession, 
        is_active: bool = False,
        page: int = 1,
        limit: int = 20,
        sort_by: Optional[SortField] = None,
        sort_order: SortOrder = SortOrder.DESC
    ) -> Tuple[List[Product], int]:
        """
        Get all products with pagination and optional filtering.
        
        Args:
            session: Database session
            is_active: If True, only return visible products
            page: Page number (1-based)
            limit: Number of items per page
            sort_by: Field to sort by
            sort_order: Sort order (ascending or descending)
            
        Returns:
            Tuple containing list of products and total count
        """
        try:
            logger.info(f"Getting all products with params: is_active={is_active}, page={page}, limit={limit}, sort_by={sort_by}, sort_order={sort_order}")
            
            # Calculate offset for pagination
            offset = (page - 1) * limit
            
            # Base query with eager loading of relationships
            statement = select(Product).options(
                selectinload(Product.user),
                selectinload(Product.images),  # Load images for each product
                selectinload(Product.variant_groups).selectinload(VariantGroup.choices)  # Load variant groups and choices
            )
            
            # Apply visibility filter if needed
            if is_active:
                statement = statement.where(Product.is_active == True)
                
            # Apply sorting
            if sort_by == SortField.PRICE:
                statement = statement.order_by(Product.price.desc() if sort_order == SortOrder.DESC else Product.price.asc())
            elif sort_by == SortField.DATE:
                statement = statement.order_by(Product.created_at.desc() if sort_order == SortOrder.DESC else Product.created_at.asc())
            elif sort_by == SortField.NAME:
                statement = statement.order_by(Product.title.desc() if sort_order == SortOrder.DESC else Product.title.asc())
            elif sort_by == SortField.QUANTITY:
                # Use stock instead of quantity
                statement = statement.order_by(Product.stock.desc() if sort_order == SortOrder.DESC else Product.stock.asc())
            else:
                # Default sorting by creation date (newest first)
                statement = statement.order_by(Product.created_at.desc())
                
            # Get total count for pagination
            count_stmt = select(func.count()).select_from(Product)
            if is_active:
                count_stmt = count_stmt.where(Product.is_active == True)
            result = await session.exec(count_stmt)
            total = result.first() or 0
            
            # Apply pagination
            statement = statement.offset(offset).limit(limit)
            
            # Execute query
            result = await session.exec(statement)
            products = result.all()
            
            logger.info(f"Found {len(products)} products (total: {total})")
            
            # Convert to schema models
            product_schemas = []
            for product in products:
                try:
                    # Start with the base product data
                    # Handle both model_dump and dict methods
                    if hasattr(product, 'model_dump'):
                        product_dict = product.model_dump()
                    else:
                        product_dict = product.dict()
                    
                    # Handle relationships
                    if product.user:
                        if hasattr(product.user, 'model_dump'):
                            product_dict["user"] = product.user.model_dump()
                        else:
                            product_dict["user"] = product.user.dict()
                    else:
                        product_dict["user"] = None
                        
                    
                    # Get stock info
                    stock_info = get_product_stock_info(product)
                    product_dict["stock"] = stock_info.get("stock")
                    product_dict["stock_status"] = stock_info.get("stock_status")
                    product_dict["has_variants"] = stock_info.get("has_variants", False)
                    
                    # Get main image
                    main_image = None
                    if hasattr(product, 'images') and product.images:
                        main_image_obj = next((img for img in product.images if img.is_main), None)
                        if main_image_obj:
                            main_image = main_image_obj.filename
                    product_dict['main_image'] = main_image
                    
                    # Do NOT include 'images' in the list response
                    if 'images' in product_dict:
                        del product_dict['images']
                    
                    # Create ProductAdmin instance with all fields
                    product_schemas.append(ProductAdmin(**product_dict))
                except Exception as e:
                    logger.error(f"Error processing product {getattr(product, 'uid', 'unknown')}: {str(e)}", exc_info=True)
            
            return product_schemas, total
        except Exception as e:
            logger.error(f"Error in get_all_products: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to retrieve products: {str(e)}")
    
    
    
    async def get_user_products(self, user_uid:str, session:AsyncSession):
        statement = select(Product).where(Product.user_uid == user_uid).order_by(desc(Product.created_at))
        
        result = await session.exec(statement)
        
        return result.all()
    
    async def get_product(self, product_uid: str, session:AsyncSession):
        try:
            # Fetch the product with its variants using selectinload
            statement = select(Product).options(
                selectinload(Product.variant_groups).selectinload(VariantGroup.choices),
                selectinload(Product.images)
            ).where(Product.uid == product_uid)
            
            # Log the query for debugging
            self.logger.debug(f"Executing query: {statement}")
            result = await session.exec(statement)
            product = result.first()
            
            if not product:
                return None
            
            # Log product details
            self.logger.debug(f"Product found: {product.title} with UID: {product.uid}")
            self.logger.debug(f"Product variant_groups attribute exists: {hasattr(product, 'variant_groups')}")
            
            # Check variant groups directly
            if hasattr(product, 'variant_groups'):
                self.logger.debug(f"Product has variant_groups: {product.variant_groups}")
                self.logger.debug(f"Product variant_groups type: {type(product.variant_groups)}")
                self.logger.debug(f"Product variant_groups length: {len(product.variant_groups) if isinstance(product.variant_groups, list) else 'Not a list'}")
            else:
                self.logger.debug("Product does not have variant_groups attribute")

            # Create a dictionary from the product model
            product_dict = {
                'uid': str(product.uid),
                'title': product.title,
                'description': product.description,
                'price': product.price,
                'cost_price': product.cost_price, 
                'stock': product.stock,
                'is_active': product.is_active,
                'created_at': product.created_at,
                'updated_at': product.updated_at
            }


            # Add images and set main image
            if hasattr(product, 'images') and product.images:
                # Find main image
                main_image = next((img.filename for img in product.images if img.is_main), None)
                product_dict['main_image'] = main_image
                
                # Get all images
                product_dict['images'] = [img.filename for img in product.images]
            else:
                product_dict['images'] = []
                product_dict['main_image'] = None

            # Add variant groups if they exist
            if hasattr(product, 'variant_groups') and product.variant_groups:
                product_dict['variant_groups'] = [
                    {
                        'id': str(group.id),
                        'name': group.name,
                        'choices': [
                            {
                                'id': str(choice.id),
                                'value': choice.value,
                                'stock': choice.stock,
                                'extra_price': choice.extra_price
                            }
                            for choice in group.choices
                        ]
                    }
                    for group in product.variant_groups
                ]
            else:
                product_dict['variant_groups'] = []
            
            # Add stock information
            stock_info = get_product_stock_info(product)
            product_dict['stock'] = stock_info.get('stock')
            product_dict['stock_status'] = stock_info.get('stock_status')
            
            # Add images and set main image
            if hasattr(product, 'images') and product.images:
                # Find main image
                main_image = next((img.filename for img in product.images if img.is_main), None)
                product_dict['main_image'] = main_image
                
                # Get all images
                product_dict['images'] = [img.filename for img in product.images]
            else:
                product_dict['images'] = []
                product_dict['main_image'] = None
            
            # Add variant groups and choices
            if hasattr(product, 'variant_groups') and product.variant_groups:
                self.logger.debug(f"Found {len(product.variant_groups)} variant groups")
                product_dict['variant_groups'] = []
                for group in product.variant_groups:
                    self.logger.debug(f"Processing variant group: {group.name} with {len(group.choices)} choices")
                    group_dict = {
                        'id': str(group.id),
                        'name': group.name
                    }
                    if hasattr(group, 'choices') and group.choices:
                        group_dict['choices'] = []
                        for choice in group.choices:
                            choice_dict = {
                                'id': str(choice.id),
                                'value': choice.value,
                                'stock': choice.stock,
                                'extra_price': choice.extra_price
                            }
                            group_dict['choices'].append(choice_dict)
                    product_dict['variant_groups'].append(group_dict)
            
            # Add stock information to each variant choice
            if stock_info.get('variants'):
                for group in product_dict.get('variant_groups', []):
                    for choice in group.get('choices', []):
                        for variant in stock_info['variants']:
                            if variant['variant'] == choice['value']:
                                choice['stock'] = variant['stock']
                                choice['stock_status'] = variant['status']
                                break
            
            # Add stock status to product level
            product_dict['stock_status'] = stock_info.get('stock_status')
            
            # Return the dictionary directly
            return product_dict
            
        except Exception as e:
            self.logger.error(f"Error in get_product: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve product details"
            )
    
    
    async def create_product(self, product_data: ProductCreateModel, user_uid:str, session:AsyncSession):
        product_data_dict = product_data.model_dump()
        new_product = Product(**product_data_dict)
        new_product.user_uid = user_uid
        session.add(new_product)
        await session.commit()
        await session.refresh(new_product)
        
        # Add stock status to response
        product_dict = new_product.__dict__.copy()
        stock_info = get_product_stock_info(new_product)
        product_dict['stock'] = stock_info.get('stock')
        product_dict['stock_status'] = stock_info.get('stock_status')
        return Product.model_validate(product_dict)
    
    async def update_product(self, product_uid: str, update_data: ProductUpdateModel, session:AsyncSession):
        try:
            # Fetch the product directly from the database
            statement = select(Product).where(Product.uid == product_uid)
            result = await session.exec(statement)
            product_to_update = result.first()
            
            if not product_to_update:
                self.logger.error(f"Product not found for UID: {product_uid}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with UID {product_uid} not found"
                )

            self.logger.info(f"Updating product {product_uid} with data: {update_data.model_dump()}")
            
            
            update_data_dict = update_data.model_dump()
            
            for k, v in update_data_dict.items():
                setattr(product_to_update, k, v)
                self.logger.debug(f"Set {k} = {v} for product {product_uid}")
            
            await session.commit()
            await session.refresh(product_to_update)
            
            # Ensure stock info is included in the response
            product_dict = product_to_update.__dict__.copy()
            stock_info = get_product_stock_info(product_to_update)
            product_dict['stock'] = stock_info.get('stock')
            product_dict['stock_status'] = stock_info.get('stock_status')

            self.logger.info(f"Successfully updated product {product_uid} with stock: {product_dict['stock']}")
            return Product.model_validate(product_dict)
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error updating product {product_uid}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update product: {str(e)}"
            )
    
    async def delete_product(self, product_uid: str, session:AsyncSession):
        product_to_delete = await self.get_product(product_uid, session)
        
        if product_to_delete is not None:
            await session.delete(product_to_delete)
            
            await session.commit()
            
            return {}
            
        else:
            return None
    
    async def search_products(
        self,
        session: AsyncSession,
        query: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        in_stock: Optional[bool] = None,
        is_active: bool = True
    ):
        conditions = []
        
        if query:
            conditions.append(
                or_(
                    Product.title.ilike(f"%{query}%"),
                    Product.description.ilike(f"%{query}%")
                )
            )
            
            
        if min_price is not None:
            conditions.append(Product.price >= min_price)
            
        if max_price is not None:
            conditions.append(Product.price <= max_price)
            
        if in_stock is not None:
            if in_stock:
                # Products are in stock if they have stock > 0 OR stock is null (unlimited)
                conditions.append(
                    or_(
                        Product.stock > 0,
                        Product.stock == None
                    )
                )
            else:
                # Products are out of stock only if they have stock = 0
                conditions.append(Product.stock == 0)
        
        # Add visibility filter if needed
        if is_active:
            conditions.append(Product.is_active == True)
            
        statement = select(Product)
        
        if conditions:
            statement = statement.where(and_(*conditions))
            
        statement = statement.order_by(desc(Product.created_at))
        
        result = await session.exec(statement)
        products = result.all()
        
        # Convert products to dict and add in_stock status
        product_list = []
        for product in products:
            product_dict = product.__dict__.copy()
            product_dict['in_stock'] = product.in_stock
            product_list.append(product_dict)
            logger.info(f"Filtered Product: {product.title}, Stock Availability: {product.in_stock}, Quantity: {product.stock}")
            
        return product_list

    async def delete_product(self, product_uid: str, session: AsyncSession):
        try:
            # First, check if the product has any associated order items
            from src.db.models import OrderItem, VariantGroup, VariantChoice
            
            self.logger.info(f"Starting delete process for product {product_uid}")
            
            # Get all order items for this product
            try:
                order_items_stmt = select(OrderItem).where(OrderItem.product_uid == product_uid)
                order_items_result = await session.exec(order_items_stmt)
                order_items = order_items_result.all()
                self.logger.info(f"Found {len(order_items)} order items for product {product_uid}")
            except Exception as e:
                self.logger.error(f"Error fetching order items: {str(e)}", exc_info=True)
                order_items = []
            
            # Get the product with its images and variant groups
            try:
                statement = select(Product).options(
                    selectinload(Product.images),
                    selectinload(Product.variant_groups).selectinload(VariantGroup.choices)
                ).where(Product.uid == product_uid)
                
                result = await session.exec(statement)
                product = result.first()
                
                if not product:
                    self.logger.warning(f"Product {product_uid} not found")
                    return None
                    
                self.logger.info(f"Found product {product.title} with {len(getattr(product, 'images', []))} images and {len(getattr(product, 'variant_groups', []))} variant groups")
            except Exception as e:
                self.logger.error(f"Error fetching product details: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Failed to retrieve product details: {str(e)}")
            
            # If product has order items, perform a soft delete instead of hard delete
            if order_items:
                try:
                    order_count = len(order_items)
                    self.logger.info(f"Product {product_uid} has {order_count} order items. Performing soft delete.")
                    
                    # Soft delete: Mark as inactive and update title to indicate it's deleted
                    product.is_active = False
                    product.title = f"[DELETED] {product.title}"
                    product.stock = 0  # Set stock to 0
                    
                    # Also set stock to 0 for all variant choices
                    if hasattr(product, 'variant_groups') and product.variant_groups:
                        for group in product.variant_groups:
                            if hasattr(group, 'choices') and group.choices:
                                for choice in group.choices:
                                    choice.stock = 0
                    
                    await session.commit()
                    self.logger.info(f"Successfully soft-deleted product {product_uid}")
                    
                    return {
                        "soft_deleted": True,
                        "message": f"Product has been archived because it is referenced in {order_count} order{'s' if order_count > 1 else ''}." 
                    }
                except Exception as e:
                    self.logger.error(f"Error during soft delete: {str(e)}", exc_info=True)
                    await session.rollback()
                    raise HTTPException(status_code=500, detail=f"Failed to soft delete product: {str(e)}")
            
            # If no order items, proceed with hard delete
            self.logger.info(f"No order items found for product {product_uid}. Proceeding with hard delete.")
            
            try:
                # Clean up dependent wishlist and cart entries (FK product_uid is NOT NULL)
                try:
                    # Delete wishlist entries referencing this product (ORM-aware to avoid stale updates)
                    wl_stmt = select(Wishlist).where(Wishlist.product_uid == product_uid)
                    wl_result = await session.exec(wl_stmt)
                    wishlists = wl_result.all()
                    for wl in wishlists:
                        await session.delete(wl)

                    # Delete cart entries referencing this product (ORM-aware)
                    cart_stmt = select(Cart).where(Cart.product_uid == product_uid)
                    cart_result = await session.exec(cart_stmt)
                    carts = cart_result.all()
                    for c in carts:
                        await session.delete(c)

                    self.logger.info("Deleted related wishlist and cart entries for the product")
                    # Ensure dependent deletions are flushed before continuing
                    await session.flush()
                except Exception as dep_err:
                    self.logger.warning(f"Failed deleting dependent wishlist/cart rows: {dep_err}")

                # First delete all variant choices and groups
                if hasattr(product, 'variant_groups') and product.variant_groups:
                    self.logger.info(f"Deleting {len(product.variant_groups)} variant groups and their choices")
                    for group in product.variant_groups:
                        if hasattr(group, 'choices') and group.choices:
                            self.logger.info(f"Deleting {len(group.choices)} choices for group {group.name}")
                            for choice in group.choices:
                                await session.delete(choice)
                
                # Then delete all variant groups
                if hasattr(product, 'variant_groups') and product.variant_groups:
                    for group in product.variant_groups:
                        await session.delete(group)
                
                # Delete all related images
                if hasattr(product, 'images') and product.images:
                    self.logger.info(f"Deleting {len(product.images)} product images")
                    for image in product.images:
                        # Delete the image file from disk if it exists
                        try:
                            await self.delete_image_from_disk(str(product.uid), image.filename)
                            self.logger.info(f"Deleted image file: {image.filename}")
                        except Exception as e:
                            self.logger.warning(f"Failed to delete image file {image.filename}: {e}")
                        
                        # Delete the image record
                        await session.delete(image)
                
                # Now delete the product
                self.logger.info(f"Deleting product {product.title} with UID {product.uid}")
                await session.delete(product)
                await session.commit()
                self.logger.info(f"Successfully deleted product {product_uid}")
                return {"deleted": True, "message": "Product successfully deleted"}
                
            except Exception as e:
                self.logger.error(f"Error during hard delete: {str(e)}", exc_info=True)
                await session.rollback()
                raise HTTPException(status_code=500, detail=f"Failed to delete product: {str(e)}")
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error deleting product: {str(e)}", exc_info=True)
            try:
                await session.rollback()
            except Exception as rollback_error:
                self.logger.error(f"Error during rollback: {str(rollback_error)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to delete product: {str(e)}")

# Add paginated response types
PaginatedProductResponse = PaginatedResponse[Union[Product, ProductAdmin]]
