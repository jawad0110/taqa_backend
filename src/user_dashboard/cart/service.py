from sqlmodel import select, delete
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi.exceptions import HTTPException
from fastapi import status
from typing import Optional, List
from datetime import datetime
from src.config import Settings
from src.user_dashboard.cart.schemas import CartModel
from src.db.models import Cart, Product, Discount, ProductImage
import uuid
from decimal import Decimal, ROUND_HALF_UP


class CartService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_item(self, user_uid: str, product_uid: str, quantity: int = 1, variant_choice_id: Optional[str] = None):
        """
        Add a product (and variant if applicable) to the user's cart or update the quantity if it already exists.
        """
        # only select products that exist and are visible
        statement = select(Product).where(Product.uid == product_uid, Product.is_active == True)
        result = await self.session.exec(statement)
        product = result.first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
        
        # Check if product has variants
        has_variants = bool(getattr(product, 'variant_groups', None)) and any(getattr(product, 'variant_groups', []))
        if has_variants:
            # Check if all variants are out of stock
            from src.db.models import VariantChoice, VariantGroup
            all_variants_stmt = select(VariantChoice).join(VariantGroup, VariantChoice.group_id == VariantGroup.id).where(VariantGroup.product_uid == product_uid)
            all_variants_result = await self.session.exec(all_variants_stmt)
            all_variants = all_variants_result.all()
            
            # Check if all variants have stock <= 0
            all_out_of_stock = all(variant.stock is not None and variant.stock <= 0 for variant in all_variants)
            if all_out_of_stock:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="نفذت الكمية لهذا المنتج")
            
            if not variant_choice_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="يرجى اختيار خيار لهذا المنتج")
            # Validate variant choice exists and belongs to this product
            variant_stmt = select(VariantChoice, VariantGroup).join(VariantGroup, VariantChoice.group_id == VariantGroup.id).where(VariantChoice.id == variant_choice_id, VariantGroup.product_uid == product_uid)
            variant_result = await self.session.exec(variant_stmt)
            variant_row = variant_result.first()
            if not variant_row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الخيار المحدد غير موجود لهذا المنتج")
            variant_choice = variant_row[0]
            # Check stock for variant
            if variant_choice.stock is not None:
                if variant_choice.stock <= 0:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="نفذت الكمية لهذا الخيار")
                # Get current cart quantity for this variant
                current_cart_stmt = select(Cart).where(Cart.user_uid == user_uid, Cart.product_uid == product_uid, Cart.variant_choice_id == variant_choice_id)
                current_cart_result = await self.session.exec(current_cart_stmt)
                current_cart_item = current_cart_result.first()
                current_quantity = current_cart_item.quantity if current_cart_item else 0
                # Check if new total quantity would exceed stock
                if current_quantity + quantity > variant_choice.stock:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="عذراً، الكمية المطلوبة غير متوفرة")
        else:
            if variant_choice_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="هذا المنتج لا يحتوي على خيارات")
            # Check product stock
            if product.stock <= 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="نفذت الكمية لهذا المنتج")
            # Get current cart quantity for this product
            current_cart_stmt = select(Cart).where(Cart.user_uid == user_uid, Cart.product_uid == product_uid, Cart.variant_choice_id == None)
            current_cart_result = await self.session.exec(current_cart_stmt)
            current_cart_item = current_cart_result.first()
            current_quantity = current_cart_item.quantity if current_cart_item else 0
            # Check if new total quantity would exceed stock
            if current_quantity + quantity > product.stock:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="عذراً، الكمية المطلوبة غير متوفرة")

        # Multi-variant support: unique by (user, product, variant_choice_id)
        stmt = select(Cart).where(Cart.user_uid == user_uid, Cart.product_uid == product_uid, Cart.variant_choice_id == variant_choice_id)
        result = await self.session.exec(stmt)
        cart_item = result.first()
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = Cart(user_uid=user_uid, product_uid=product_uid, variant_choice_id=variant_choice_id, quantity=quantity)
            self.session.add(cart_item)
        await self.session.commit()
        await self.session.refresh(cart_item)
        
        # Calculate price based on product and variant using Decimal
        decimal_price = Decimal(str(product.price))
        if has_variants:
            decimal_price += Decimal(str(variant_choice.extra_price))
        price = float(decimal_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

        # Get the main image URL
        main_image = next((img for img in product.images if img.is_main), None)
        main_image_url = main_image.filename if main_image else None

        # In the add_item method, around line 95-105
        # Calculate stock based on product or variant
        if has_variants and variant_choice:
            stock = variant_choice.stock if variant_choice.stock is not None else 0
        else:
            stock = product.stock
        
        # Return CartModel with calculated price
        return CartModel(
            uid=cart_item.uid,
            user_uid=cart_item.user_uid,
            product_uid=cart_item.product_uid,
            variant_choice_id=cart_item.variant_choice_id,
            quantity=cart_item.quantity,
            price=round(price, 2),
            total_price=round((Decimal(str(price)) * Decimal(str(quantity))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP), 2),
            product_title=product.title,
            main_image_url=main_image_url,
            added_at=cart_item.added_at,
            updated_at=cart_item.updated_at,
            stock=stock  # Add the missing stock field
            # Remove total_price as it's not in the schema
        )

    async def remove_item(self, user_uid: str, product_uid: str):
        """
        Remove a specific product from the user's cart.
        """
        stmt = select(Cart).where(Cart.user_uid == user_uid, Cart.product_uid == product_uid)
        result = await self.session.exec(stmt)
        cart_item = result.first()
        if not cart_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found.")
        await self.session.delete(cart_item)
        await self.session.commit()
        return {}

    async def update_item_quantity(self, user_uid: str, product_uid: str, quantity: int, variant_choice_id: Optional[str] = None):
        """
        Update the quantity of a specific product (and variant if applicable) in the user's cart.
        """
        stmt = select(Cart).where(Cart.user_uid == user_uid, Cart.product_uid == product_uid, Cart.variant_choice_id == variant_choice_id)
        result = await self.session.exec(stmt)
        cart_item = result.first()
        if not cart_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found.")
        # Check product and variant stock status
        from src.db.models import Product, VariantChoice, VariantGroup
        statement = select(Product).where(Product.uid == product_uid)
        result = await self.session.exec(statement)
        product = result.first()
        has_variants = bool(getattr(product, 'variant_groups', None)) and any(getattr(product, 'variant_groups', []))
        if has_variants:
            if not variant_choice_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You must select a variant for this product.")
            variant_stmt = select(VariantChoice, VariantGroup).join(VariantGroup, VariantChoice.group_id == VariantGroup.id).where(VariantChoice.id == variant_choice_id, VariantGroup.product_uid == product_uid)
            variant_result = await self.session.exec(variant_stmt)
            variant_row = variant_result.first()
            if not variant_row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected variant does not exist for this product.")
            variant_choice = variant_row[0]
            if variant_choice.stock is not None and variant_choice.stock <= 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected variant is out of stock.")
        else:
            if variant_choice_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This product does not have variants.")
            if hasattr(product, 'in_stock') and not product.in_stock:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product is out of stock.")
        if quantity <= 0:
            await self.session.delete(cart_item)
            await self.session.commit()
            return None
        cart_item.quantity = quantity
        await self.session.commit()
        await self.session.refresh(cart_item)
        return cart_item

    async def get_cart(self, user_uid: str) -> List[CartModel]:
        """
        Return CartModel list with product details and main image URL.
        """
        # 1) Fetch raw Cart items with product relationship
        stmt = select(Cart).where(Cart.user_uid == user_uid)
        result = await self.session.exec(stmt)
        cart_items = result.all()

        # 2) Ensure product and variant relationships are loaded
        for item in cart_items:
            await self.session.refresh(item, attribute_names=["product", "variant_choice"])

        # 3) Batch-fetch main-image filenames
        product_uids = [item.product_uid for item in cart_items]
        main_image_map = {}
        if product_uids:
            img_stmt = (
                select(ProductImage.product_uid, ProductImage.filename)
                .where(
                    ProductImage.product_uid.in_(product_uids),
                    ProductImage.is_main == True
                )
            )
            img_rows = await self.session.exec(img_stmt)
            main_image_map = {
                pu: f"{Settings().DOMAIN}{Settings().STATIC_URL}/images/products/{pu}/{filename}"
                for pu, filename in img_rows.all()
            }

        # 4) Build and return CartModel instances with calculated price and stock
        return [
            CartModel(
                uid=item.uid,
                product_uid=item.product_uid,
                variant_choice_id=item.variant_choice_id,
                product_title=item.product.title,
                main_image_url=main_image_map.get(item.product_uid),
                quantity=item.quantity,
                # Calculate price using Decimal for precise calculations
                price=float(Decimal(str(item.product.price)) + (Decimal(str(item.variant_choice.extra_price)) if item.variant_choice and item.variant_choice.extra_price else Decimal('0'))),
                total_price=float((Decimal(str(item.product.price)) + (Decimal(str(item.variant_choice.extra_price)) if item.variant_choice and item.variant_choice.extra_price else Decimal('0'))) * Decimal(str(item.quantity))),
                user_uid=item.user_uid,
                added_at=item.added_at,
                updated_at=item.updated_at,
                # Add stock information
                stock=item.variant_choice.stock if item.variant_choice else item.product.stock
            )
            for item in cart_items
        ]


    async def clear_cart(self, user_uid: str):
        """
        Remove all items from the user's cart.
        """
        del_stmt = delete(Cart).where(Cart.user_uid == user_uid)
        await self.session.exec(del_stmt)
        await self.session.commit()
        return {}

    async def calculate_totals(self, user_uid: str, discount_code: Optional[str] = None):
        """
        Calculate the subtotal, discounts, and total for the user's cart.
        """
        stmt = select(Cart).where(Cart.user_uid == user_uid)
        result = await self.session.exec(stmt)
        items = result.all()
        subtotal = 0.0
        discount = 0.0
        # Initialize Decimal variables for precise calculations
        decimal_subtotal = Decimal('0')
        decimal_discount = Decimal('0')  # Initialize here for scope
        
        for item in items:
            await self.session.refresh(item, attribute_names=["product", "variant_choice"])
            # Calculate item price using Decimal
            decimal_price = Decimal(str(item.product.price))
            if item.variant_choice and item.variant_choice.extra_price:
                decimal_price += Decimal(str(item.variant_choice.extra_price))
            # Add to subtotal using Decimal
            decimal_subtotal += decimal_price * Decimal(str(item.quantity))
            
        # Convert subtotal to float for the response
        subtotal = float(decimal_subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        # Apply discount code if provided and not empty
        if discount_code:
            # Find discount by code
            stmt = select(Discount).where(Discount.code == discount_code)
            result = await self.session.exec(stmt)
            discount_obj = result.first()
            if not discount_obj:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon does not exist.")
            if not discount_obj.is_active:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon is not valid anymore.")
            if discount_obj.expires_at and discount_obj.expires_at < datetime.now(discount_obj.expires_at.tzinfo):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discount code expired.")
            if discount_obj.minimum_order_amount and subtotal < discount_obj.minimum_order_amount:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Minimum order amount for discount is {discount_obj.minimum_order_amount}")
            if discount_obj.usage_limit and discount_obj.used_count >= discount_obj.usage_limit:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discount code usage limit reached")
            # Calculate discount using Decimal
            if discount_obj.discount_type == "percent":
                decimal_discount = decimal_subtotal * (Decimal(str(discount_obj.value)) / Decimal('100'))
            else:
                decimal_discount = Decimal(str(discount_obj.value))
            
            # Ensure discount doesn't exceed subtotal
            decimal_discount = min(decimal_discount, decimal_subtotal)
            
            # Convert discount to float for the response
            discount = float(decimal_discount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        # Calculate total using Decimal
        decimal_total = decimal_subtotal - decimal_discount
        total = float(decimal_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        return {"subtotal": subtotal, "discount": f"-{discount}", "total": total}