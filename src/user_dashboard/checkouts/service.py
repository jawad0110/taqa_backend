from decimal import Decimal
from typing import List
import uuid
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from datetime import datetime, timedelta, timezone

from src.db.models import Order, OrderItem, ShippingAddress, Product, OrderStatus, Cart, Discount, ShippingRate, User, VariantGroup
from sqlalchemy import delete
from .schemas import CheckoutCreate, CheckoutResponse, OrderItemResponse, ShippingAddressModel
from src.admin_dashboard.mail import mail, create_message

class CheckoutService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _validate_user(self, user_uid: str) -> uuid.UUID:
        # validate user UID
        try:
            return uuid.UUID(user_uid)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user UID")

    def _build_response(self, order: Order) -> CheckoutResponse:
        shipping_data = order.shipping_address.model_dump()
        items = []
        for item in order.items:
            item_data = item.model_dump()
            # Create ProductDetail from the product relationship
            product = item.product
            # Find main image URL if available
            main_image = next((img for img in product.images if img.is_main), None)
            main_image_url = main_image.filename if main_image else None
            
            product_detail = {
                'uid': product.uid,
                'title': product.title,
                'main_image_url': main_image_url,
                'variant_groups': []  # Add variant groups if needed
            }
            # Update item data with the properly structured product
            item_data['product'] = product_detail
            items.append(OrderItemResponse(**item_data))
            
        return CheckoutResponse(
            uid=order.uid,
            status=order.status,
            total_price=order.total_price,
            discount=order.discount,
            shipping_price=order.shipping_price,
            final_price=order.final_price,
            coupon_code=order.coupon_code,
            created_at=order.created_at,
            shipping_address=ShippingAddressModel(**shipping_data),
            items=items
        )

    async def create_order(self, user_uid: str, cmd: CheckoutCreate, background_tasks=None) -> CheckoutResponse:
        try:
            user_uuid = self._validate_user(user_uid)
            print(f"Creating order for user: {user_uid}")

            # create shipping address
            try:
                print("Creating shipping address...")
                shipping = ShippingAddress(user_uid=user_uuid, **cmd.shipping_address.dict())
                self.session.add(shipping)
                await self.session.commit()
                await self.session.refresh(shipping)
                print(f"Created shipping address: {shipping.uid}")
            except Exception as e:
                print(f"Error creating shipping address: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid shipping address: {str(e)}"
                )

            # lookup shipping rate
            try:
                print(f"Looking up shipping rate for {cmd.shipping_address.country}, {cmd.shipping_address.city}")
                result_rate = await self.session.exec(
                    select(ShippingRate).where(
                        ShippingRate.country == cmd.shipping_address.country,
                        ShippingRate.city == cmd.shipping_address.city
                    )
                )
                shipping_rate = result_rate.one_or_none()
                if not shipping_rate:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, 
                        detail="Sorry, we don't ship to that address"
                    )
                shipping_price = shipping_rate.price
                print(f"Found shipping rate: {shipping_price}")
            except HTTPException:
                raise
            except Exception as e:
                print(f"Error looking up shipping rate: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Error processing shipping information"
                )

            # fetch cart items with product and variant relationships
            stmt_cart = (
                select(Cart)
                .options(
                    selectinload(Cart.product).selectinload(Product.images),
                    selectinload(Cart.variant_choice),
                )
                .where(Cart.user_uid == user_uuid)
            )
            result_cart = await self.session.exec(stmt_cart)
            cart_items = result_cart.all()
            if not cart_items:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

            # compute totals from cart
            total_price = Decimal('0.0')
            items_data = []
            seen_products = set()
            
            for cart_item in cart_items:
                product = cart_item.product
                quantity = cart_item.quantity
                variant_choice = cart_item.variant_choice
                
                # Track product/variant combination to prevent duplicates
                item_key = f"{product.uid}-{variant_choice.id if variant_choice else 'no-variant'}"
                if item_key in seen_products:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Duplicate product/variant combination found in cart: {product.title}"
                    )
                seen_products.add(item_key)
                
                # Calculate item price based on variant or base price
                if variant_choice:
                    if variant_choice.stock < quantity:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Not enough stock for variant: {product.title} - {variant_choice.value}"
                        )
                    item_price = Decimal(str(product.price)) + Decimal(str(variant_choice.extra_price or 0))
                else:
                    if product.stock < quantity:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Not enough stock for product: {product.title}"
                        )
                    item_price = Decimal(str(product.price))
                
                item_total = item_price * Decimal(str(quantity))
                total_price += item_total
                
                items_data.append({
                    "product": product,
                    "variant_choice": variant_choice,
                    "quantity": quantity,
                    "price": float(item_price),
                    "total": float(item_total)
                })

            # apply coupon
            discount = Decimal('0.0')
            if cmd.coupon_code:
                res_disc = await self.session.exec(select(Discount).where(Discount.code == cmd.coupon_code))
                disc = res_disc.one_or_none()
                if not disc:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discount code does not exist")
                if not disc.is_active:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discount code is not valid anymore")
                now = datetime.now(timezone.utc)
                if disc.expires_at and disc.expires_at < now:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discount code has expired")
                if disc.minimum_order_amount and total_price < disc.minimum_order_amount:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order does not meet minimum amount for discount")
                if disc.discount_type == "percent":
                    discount = total_price * (disc.value / 100.0)
                else:
                    discount = disc.value
                discount = min(discount, total_price)

            final_price = total_price - discount + shipping_price

            # create order
            try:
                print("Creating order...")
                order = Order(
                    user_uid=user_uuid,
                    total_price=round(total_price, 2),
                    discount=round(discount, 2),
                    shipping_price=round(shipping_price, 2),
                    shipping_rate_uid=shipping_rate.uid,
                    final_price=round(final_price, 2),
                    shipping_address_uid=shipping.uid,
                    coupon_code=cmd.coupon_code
                )
                self.session.add(order)
                await self.session.commit()
                await self.session.refresh(order)
                print(f"Created order: {order.uid}")
            except Exception as e:
                print(f"Error creating order: {str(e)}")
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error creating order: {str(e)}"
                )

            # create order items
            for data in items_data:
                order_item = OrderItem(
                    order_uid=order.uid,
                    product_uid=data["product"].uid,
                    variant_choice_id=data["variant_choice"].id if data["variant_choice"] else None,
                    quantity=data["quantity"],
                    price_at_purchase=round(Decimal(str(data["price"])), 2),
                    total_price=round(Decimal(str(data["total"])), 2)
                )
                self.session.add(order_item)
            await self.session.commit()

            # DECREMENT STOCK for each product/variant if not unlimited
            for cart_item in cart_items:
                product = cart_item.product
                variant_choice = cart_item.variant_choice
                quantity = cart_item.quantity
                
                if variant_choice and variant_choice.stock is not None:
                    # Decrement variant stock
                    variant_choice.stock = max(0, variant_choice.stock - quantity)
                    self.session.add(variant_choice)
                elif hasattr(product, 'stock') and product.stock is not None:
                    # Decrement product stock (for non-variant products)
                    product.stock = max(0, product.stock - quantity)
                    self.session.add(product)
            await self.session.commit()

            # clear cart
            await self.session.exec(delete(Cart).where(Cart.user_uid == user_uuid))
            await self.session.commit()

            # reload order with relationships
            stmt = select(Order).options(
                selectinload(Order.items).selectinload(OrderItem.product).selectinload(Product.images),
                selectinload(Order.items).selectinload(OrderItem.product).selectinload(Product.variant_groups).selectinload(VariantGroup.choices),
                selectinload(Order.shipping_address)
            ).where(Order.uid == order.uid)
            res = await self.session.exec(stmt)
            order = res.one()

            await self.session.refresh(order, attribute_names=["items","shipping_address"])

            # Fetch user info for email
            user_result = await self.session.exec(select(User).where(User.uid == user_uuid))
            user = user_result.first()
            if user:
                # Prepare email context
                shipping_addr = order.shipping_address
                items = []
                for item in order.items:
                    product = getattr(item, 'product', None)
                    items.append({
                        'product_title': product.title if product else '',
                        'variant': getattr(item, 'variant', None),
                        'unit_price': round(item.price_at_purchase, 2),
                        'discount': '-',
                        'quantity': item.quantity,
                        'subtotal': item.total_price,
                    })
                email_context = {
                    'user_name': user.first_name or user.username,
                    'shipping_address': f"{shipping_addr.full_name}, {shipping_addr.street}, {shipping_addr.area}, {shipping_addr.city}, {shipping_addr.country}",
                    'items': items,
                    'subtotal': order.total_price,
                    'shipping_fee': order.shipping_price,
                    'total': order.final_price,
                    'currency': 'JOD',
                }
                
                message = create_message(
                    recipients=[user.email],
                    subject="Order Details - Taqa",
                    template_name="order_details.html",
                    template_body=email_context
                )
                await mail.send_message(message)
                if background_tasks:
                    background_tasks.add_task(mail.send_message, message)
                else:
                    await mail.send_message(message)
            return self._build_response(order)
        except HTTPException:
            await self.session.rollback()
            raise
        except Exception as e:
            await self.session.rollback()
            print(f"Unexpected error in create_order: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            print("Traceback:", traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred: {str(e)}"
            )
    
    
    

    async def list_orders_for_user(self, user_uid: str) -> List[CheckoutResponse]:
        user_uuid = self._validate_user(user_uid)
        result = await self.session.exec(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.shipping_address))
            .where(
                Order.user_uid == user_uuid,
                Order.status != OrderStatus.canceled
            )
        )
        return [self._build_response(o) for o in result.all()]

    async def get_order_for_user(self, user_uid: str, order_uid: str) -> CheckoutResponse:
        user_uuid = self._validate_user(user_uid)
        result = await self.session.exec(
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product).selectinload(Product.images),
                selectinload(Order.items).selectinload(OrderItem.product).selectinload(Product.variant_groups).selectinload(VariantGroup.choices),
                selectinload(Order.shipping_address)
            )
            .where(Order.uid == order_uid, Order.user_uid == user_uuid)
        )
        order = result.one_or_none()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return self._build_response(order)
    
    async def cancel_order(self, user_uid: str, order_uid: str) -> CheckoutResponse:
        user_uuid = self._validate_user(user_uid)
        result = await self.session.exec(
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product).selectinload(Product.images),
                selectinload(Order.items).selectinload(OrderItem.product).selectinload(Product.variant_groups).selectinload(VariantGroup.choices),
                selectinload(Order.shipping_address)
            )
            .where(Order.uid == order_uid, Order.user_uid == user_uuid)
        )
        order = result.one_or_none() or HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        
        # Check if order is already canceled
        if order.status == OrderStatus.canceled:
            return self._build_response(order)
            
        # Ensure both datetimes are timezone-aware for comparison
        created_at = order.created_at.replace(tzinfo=timezone.utc) if order.created_at.tzinfo is None else order.created_at
        if datetime.now(timezone.utc) - created_at > timedelta(hours=24):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancellation window has expired")
        
        # Restore product stock
        for item in order.items:
            product = item.product
            # If product has variants, find and update the variant's stock
            if hasattr(item, 'variant_choice_id') and item.variant_choice_id:
                # Find the variant choice in the product's variant groups
                for group in product.variant_groups:
                    for choice in group.choices:
                        if str(choice.id) == str(item.variant_choice_id):
                            choice.stock += item.quantity
                            break
            else:
                # Update product stock directly if no variants
                product.stock += item.quantity
            
            self.session.add(product)
        
        # Update order status
        order.status = OrderStatus.canceled
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order, attribute_names=["items", "shipping_address"])
        return self._build_response(order)