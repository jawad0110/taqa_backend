from sqlmodel import select, or_, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Tuple
from datetime import datetime
from src.db.models import Product, ProductImage, VariantGroup, VariantChoice
from .schemas import RecentProduct, AlertItem, Alerts, OutOfStockProduct

async def get_recent_products(db: AsyncSession) -> List[RecentProduct]:
    statement = (
        select(Product)
        .order_by(desc(Product.created_at))
        .limit(5)
    )
    result = await db.execute(statement)
    products = result.scalars().all()
    
    return [
        RecentProduct(
            id=product.uid,
            title=product.title,
            created_at=product.created_at
        ) for product in products
    ]

async def get_alerts(db: AsyncSession) -> Alerts:
    # Get all products - relationships are already configured for selectin loading
    all_products_stmt = select(Product)
    result = await db.execute(all_products_stmt)
    all_products = result.scalars().all()
    
    missing_main_image = []
    out_of_stock_products = []
    
    for product in all_products:
        # Check for missing main image
        has_main_image = any(img.is_main for img in product.images)
        if not has_main_image:
            missing_main_image.append(product)
        
        # Check for out of stock
        is_out_of_stock = False
        
        if not product.variant_groups:
            # Product without variants
            if product.stock <= 0:
                is_out_of_stock = True
        else:
            # Product with variants - check if all variants are out of stock
            all_variants_out_of_stock = True
            for variant_group in product.variant_groups:
                for choice in variant_group.choices:
                    if choice.stock is not None and choice.stock > 0:
                        all_variants_out_of_stock = False
                        break
                if not all_variants_out_of_stock:
                    break
            is_out_of_stock = all_variants_out_of_stock
        
        if is_out_of_stock:
            out_of_stock_products.append(product)
    
    return Alerts(
        missing_main_image=[
            AlertItem(id=product.uid, title=product.title)
            for product in missing_main_image
        ],
        out_of_stock=[
            OutOfStockProduct(
                id=str(product.uid),
                title=product.title,
                stock=0,
                has_variants=bool(product.variant_groups)
            )
            for product in out_of_stock_products
        ]
    )