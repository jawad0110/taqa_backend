from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, desc, and_, or_
from src.db.models import Product
from typing import Optional, Tuple, List
import logging
from fastapi import HTTPException, status
from src.user_dashboard.products.schemas import ProductImageRead, ProductRead
from sqlalchemy.orm import selectinload, joinedload
from enum import Enum
from src.db.models import ProductImage
from src.db.redis import get_cache, set_cache, delete_cache_pattern


logger = logging.getLogger(__name__)

def get_product_stock_info(product, selected_variant_id: str = None):
    """
    Get stock information for a product and its variants.
    
    Args:
        product: SQLAlchemy Product model instance
        selected_variant_id: ID of the currently selected variant (optional)
        
    Returns:
        dict: Stock information including product and variants
    """
    try:
        # Get product stock
        product_stock = getattr(product, 'available_stock', None)
        
        # Get variant stock information
        variants = []
        any_variant_in_stock = False
        selected_variant_stock = None
        
        if hasattr(product, 'variant_groups'):
            variant_groups = getattr(product, 'variant_groups', [])
            for group in variant_groups:
                if hasattr(group, 'choices'):
                    choices = getattr(group, 'choices', [])
                    for choice in choices:
                        variant_stock = getattr(choice, 'stock', 0)
                        is_in_stock = variant_stock > 0
                        
                        # Track if any variant is in stock
                        if is_in_stock:
                            any_variant_in_stock = True
                            
                        # Track selected variant stock
                        if selected_variant_id and str(choice.id) == str(selected_variant_id):
                            selected_variant_stock = variant_stock
                        
                        variants.append({
                            'id': str(getattr(choice, 'id', '')),
                            'variant': getattr(choice, 'value', None),
                            'stock': variant_stock,
                            'status': 'In Stock' if is_in_stock else 'Out of Stock',
                            'is_available': is_in_stock
                        })
        
        # Determine overall stock status
        if selected_variant_id and selected_variant_stock is not None:
            # If a variant is selected, use its stock status
            stock_status = 'In Stock' if selected_variant_stock > 0 else 'Out of Stock'
            stock = selected_variant_stock
        elif variants:
            # If no variant selected but product has variants, check if any variant is in stock
            stock_status = 'In Stock' if any_variant_in_stock else 'Out of Stock'
            stock = sum(v.get('stock', 0) for v in variants) if variants else 0
        else:
            # For products without variants, use the product stock
            stock_status = 'In Stock' if product_stock and product_stock > 0 else 'Out of Stock'
            stock = product_stock or 0
        
        return {
            'stock': stock,
            'stock_status': stock_status,
            'variants': variants,
            'in_stock': stock_status == 'In Stock'
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
    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = logging.getLogger(__name__)

    async def get_all_products(
        self,
        visible_only: bool = False,
        page: int = 1,
        limit: int = 20,  # Increased from 10 to 20
        sort_by: Optional[SortField] = None,
        sort_order: SortOrder = SortOrder.DESC
    ) -> Tuple[List[ProductRead], int]:
        try:
            # Check cache first
            cache_key = f"products:{visible_only}:{page}:{limit}:{sort_by}:{sort_order}"
            cached_result = await get_cache(cache_key)
            if cached_result:
                try:
                    items = [ProductRead.model_validate(item) for item in cached_result.get("items", [])]
                    total_cached = int(cached_result.get("total", 0))
                    return items, total_cached
                except Exception:
                    # Ignore cache if shape mismatched
                    pass
            # Base query with images - optimized with joinedload for better performance
            stmt = select(Product).options(
                joinedload(Product.images)
            )
            
            if visible_only:
                stmt = stmt.where(Product.is_active == True)
            
            # Apply sorting
            if sort_by:
                if sort_by == SortField.PRICE:
                    stmt = stmt.order_by(desc(Product.price) if sort_order == SortOrder.DESC else Product.price)
                elif sort_by == SortField.DATE:
                    stmt = stmt.order_by(desc(Product.created_at) if sort_order == SortOrder.DESC else Product.created_at)
                elif sort_by == SortField.NAME:
                    stmt = stmt.order_by(desc(Product.title) if sort_order == SortOrder.DESC else Product.title)
            
            # Apply pagination
            offset = (page - 1) * limit
            stmt = stmt.offset(offset).limit(limit)
            
            # Execute query
            result = await self.session.execute(stmt)
            # With joinedload on collection relationships, ensure unique rows
            products = result.unique().scalars().all()
            
            # Convert to ProductRead models
            product_reads = []
            for product in products:
                # Get main image
                main_image = None
                if product.images:
                    main_image_obj = next((img for img in product.images if img.is_main), None)
                    if main_image_obj:
                        main_image = main_image_obj.filename
                
                # Get stock info
                stock_info = get_product_stock_info(product)
                
                # Create ProductRead instance
                product_read = ProductRead(
                    uid=product.uid,
                    title=product.title,
                    description=product.description,
                    price=product.price,
                    main_image=main_image,
                    created_at=product.created_at,
                    updated_at=product.updated_at,
                    is_active=product.is_active,
                    stock=stock_info['stock'],
                    stock_status=stock_info['stock_status'],
                    in_stock=stock_info['stock_status'] != 'Out of Stock'
                )
                product_reads.append(product_read)
            
            # Get total count for pagination
            count_stmt = select(Product)
            if visible_only:
                count_stmt = count_stmt.where(Product.is_active == True)
            count_result = await self.session.execute(count_stmt)
            total = len(count_result.scalars().all())
            
            # Cache JSON-serializable payload
            await set_cache(cache_key, {"items": [p.model_dump() for p in product_reads], "total": total})
            
            return product_reads, total
            
        except Exception as e:
            self.logger.error(f"Error getting products: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving products"
            )
    
    
    
    async def get_product(self, product_uid: str, session: AsyncSession, selected_variant_id: str = None):
        from src.db.models import VariantGroup, VariantChoice
        from sqlalchemy.orm import selectinload
        from .schemas import ProductDetail, VariantGroupModel, VariantChoiceModel
        
        # First, get the product with its relationships
        statement = select(Product).options(
            selectinload(Product.variant_groups).selectinload(VariantGroup.choices),
            selectinload(Product.reviews),
            selectinload(Product.images)
        ).where(Product.uid == product_uid, Product.is_active == True)
        
        result = await session.exec(statement)
        product = result.first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Get stock information with selected variant
        stock_info = get_product_stock_info(product, selected_variant_id)
        
        # Get main image
        main_image = None
        if product.images:
            main_image_obj = next((img for img in product.images if img.is_main), None)
            if main_image_obj:
                main_image = main_image_obj.filename
        
        # Prepare variant groups with stock information
        variant_groups = []
        if hasattr(product, 'variant_groups'):
            for group in product.variant_groups:
                choices = []
                if hasattr(group, 'choices'):
                    for choice in group.choices:
                        is_available = choice.stock > 0
                        choices.append(VariantChoiceModel(
                            id=choice.id,
                            value=choice.value,
                            stock=choice.stock,
                            is_available=is_available,
                            extra_price=choice.extra_price,
                            status='In Stock' if is_available else 'Out of Stock'
                        ))
                
                variant_groups.append(VariantGroupModel(
                    id=group.id,
                    name=group.name,
                    choices=choices
                ))
        
        # Get all images for the product
        images = []
        if hasattr(product, 'images') and product.images:
            for img in product.images:
                images.append(ProductImageRead.model_validate({
                    "uid": img.uid,
                    "filename": img.filename,
                    "is_main": img.is_main
                }))
        
        product_detail = ProductDetail(
            uid=product.uid,
            title=product.title,
            description=product.description,
            price=product.price,
            main_image=main_image,
            stock=stock_info['stock'],
            stock_status=stock_info['stock_status'],
            created_at=product.created_at,
            updated_at=product.updated_at,
            reviews=[r.model_dump() for r in getattr(product, 'reviews', [])],
            variant_groups=variant_groups,
            images=images
        )
        return product_detail
    
    
    
    async def search_products(
        self,
        query: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        stock: Optional[bool] = None,
        visible_only: bool = True
    ) -> List[ProductRead]:
        try:
            # Verify session is active first
            if not self.session.is_active:
                logger.error("Database session is not active")
                raise HTTPException(
                    status_code=500,
                    detail="Database connection error"
                )

            logger.info(f"Search products called with params: query={query}, min_price={min_price}, max_price={max_price}, stock={stock}, visible_only={visible_only}")
            
            # Start with base query
            query_builder = select(Product).options(
                selectinload(Product.images)
            )
            
            # Handle search query
            if query:
                try:
                    query = query.strip()
                    if not query:
                        logger.info("Empty search query provided")
                        return []
                    
                    logger.info(f"Searching for query: {query}")
                    query_builder = query_builder.where(
                        or_(
                            Product.title.ilike(f"%{query}%"),
                            Product.description.ilike(f"%{query}%")
                        )
                    )
                except Exception as e:
                    logger.error(f"Error processing search query '{query}': {e}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid search query: {str(e)}"
                    )
            
            
            # Add price filters
            if min_price is not None:
                logger.info(f"Adding min price filter: {min_price}")
                query_builder = query_builder.where(Product.price >= min_price)
            
            if max_price is not None:
                logger.info(f"Adding max price filter: {max_price}")
                query_builder = query_builder.where(Product.price <= max_price)
            
            # Add stock filter
            if stock is not None:
                logger.info(f"Adding stock filter: {stock}")
                if stock:
                    query_builder = query_builder.where(
                        or_(
                            Product.stock > 0,
                            Product.stock == None
                        )
                    )
                else:
                    query_builder = query_builder.where(Product.stock == 0)
            
            # Add visibility filter
            if visible_only:
                logger.info("Adding visibility filter")
                query_builder = query_builder.where(Product.is_active == True)
            
            # Order by creation date
            query_builder = query_builder.order_by(desc(Product.created_at))
            
            # Execute query
            logger.info("Executing search query")
            results = await self.session.exec(query_builder)
            products = results.unique().all()
            
            logger.info(f"Found {len(products)} products matching the search criteria")
            
            # Convert to ProductRead models
            product_list = []
            for product in products:
                try:
                    main_image = None
                    if product.images:
                        main_image_obj = next((img for img in product.images if img.is_main), None)
                        if main_image_obj:
                            main_image = main_image_obj.filename
                    
                    stock_info = get_product_stock_info(product)
                    
                    product_read = ProductRead(
                        uid=product.uid,
                        title=product.title,
                        description=product.description,
                        price=product.price,
                        main_image=main_image,
                        created_at=product.created_at,
                        updated_at=product.updated_at,
                        is_active=product.is_active,
                        stock=stock_info['stock'],
                        stock_status=stock_info['stock_status'],
                        in_stock=stock_info['stock_status'] != 'Out of Stock'
                    )
                    product_list.append(product_read)
                except Exception as e:
                    logger.error(f"Error converting product {getattr(product, 'uid', 'N/A')}: {e}")
            
            return product_list
            
        except Exception as e:
            logger.error(f"Error in search_products: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Failed to search products. Please try again later."
            )
                
            
            if min_price is not None:
                logger.debug(f"Adding min_price condition: {min_price}")
                conditions.append(Product.price >= min_price)
                
            if max_price is not None:
                logger.debug(f"Adding max_price condition: {max_price}")
                conditions.append(Product.price <= max_price)
                
            if stock is not None:
                logger.debug(f"Adding stock condition: {stock}")
                if stock:
                    # Products are in stock if they have available_stock > 0 OR available_stock is null (always in stock)
                    conditions.append(
                        or_(
                            Product.available_stock > 0,
                            Product.available_stock == None
                        )
                    )
                else:
                    # Products are out of stock only if they have available_stock = 0
                    conditions.append(Product.available_stock == 0)
            
            # Add visibility filter if needed
            if visible_only:
                logger.debug("Adding visibility filter")
                conditions.append(Product.is_active == True)
                
            # Base query - Load images - optimized with joinedload
            statement = select(Product).options(
                joinedload(Product.images)
            )
            
            if conditions:
                logger.debug(f"Adding conditions to query: {conditions}")
                statement = statement.where(and_(*conditions))
                
            logger.debug(f"Final SQL query: {str(statement)}")
            statement = statement.order_by(desc(Product.created_at))
            
            try:
                result = await self.session.exec(statement)
                products = result.all()
                logger.debug(f"Found {len(products)} products")
                
                # Convert products to ProductRead models
                product_list = []
                for product in products:
                    try:
                        # Get main image (logic copied from get_all_products)
                        main_image_filename = None
                        if product.images:
                            main_image_obj = next((img for img in product.images if img.is_main), None)
                            if main_image_obj:
                                main_image_filename = main_image_obj.filename
                        
                        # Get stock info
                        stock_info = get_product_stock_info(product)
                        
                        # Create ProductRead instance
                        product_read = ProductRead(
                            uid=product.uid,
                            title=product.title,
                            description=product.description,
                            price=product.price,
                            main_image=main_image_filename,
                            created_at=product.created_at,
                            updated_at=product.updated_at,
                            is_active=product.is_active,
                            stock=stock_info['stock'],
                            stock_status=stock_info['stock_status'],
                            in_stock=stock_info['stock_status'] != 'Out of Stock'
                        )
                        product_list.append(product_read)
                    except Exception as e:
                        logger.error(f"Error processing product {product.uid}: {e}")
                        continue
            except Exception as e:
                logger.error(f"Error executing search query: {e}")
                raise HTTPException(status_code=500, detail="Failed to retrieve products")
            
            return product_list
            
        except Exception as e:
            logger.error(f"Error in search_products: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve products")
