from sqlmodel import func, select, text
from sqlmodel.ext.asyncio.session import AsyncSession
from src.admin_dashboard.statistics.variants_images_breakdown.schemas import BreakdownStats
from src.db.models import Product, ProductImage, VariantGroup

async def get_variants_images_breakdown(db: AsyncSession) -> BreakdownStats:
    # Get total products count
    total_products_result = await db.scalar(
        select(func.count()).select_from(Product)
    )
    total_products = total_products_result or 0
    
    # Get products with more than 1 image using a raw count approach
    # Count distinct products that have more than 1 image
    products_with_multiple_images_query = """
        SELECT COUNT(DISTINCT product_uid) 
        FROM product_images 
        WHERE product_uid IN (
            SELECT product_uid 
            FROM product_images 
            GROUP BY product_uid 
            HAVING COUNT(*) > 1
        )
    """
    products_with_additional_images_result = await db.execute(text(products_with_multiple_images_query))
    products_with_additional_images = products_with_additional_images_result.scalar() or 0
    
    # Get products with at least 1 variant group
    products_with_variants_result = await db.scalar(
        select(func.count(func.distinct(VariantGroup.product_uid)))
    )
    products_with_variants = products_with_variants_result or 0
    
    # Calculate percentages
    with_additional_images_pct = (products_with_additional_images / total_products * 100) if total_products > 0 else 0
    with_variants_pct = (products_with_variants / total_products * 100) if total_products > 0 else 0
    
    return BreakdownStats(
        with_additional_images_pct=round(with_additional_images_pct, 2),
        with_variants_pct=round(with_variants_pct, 2)
    )