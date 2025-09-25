import logging
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from sqlalchemy import update
from typing import List, Tuple

from src.db.models import Order, OrderStatus, Product, VariantChoice, OrderItem, VariantGroup
from src.user_dashboard.checkouts.schemas import ShippingAddressModel, OrderItemResponse
from .schemas import OrderResponse, UpdateOrderStatus, PaginatedOrderResponse

class OrderService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    async def list_orders(self, session: AsyncSession, page: int = 1, per_page: int = 10) -> PaginatedOrderResponse:
        # Get total count
        count_stmt = select(func.count(Order.uid))
        count_result = await session.exec(count_stmt)
        total = count_result.first()
        
        # Calculate pagination
        offset = (page - 1) * per_page
        total_pages = (total + per_page - 1) // per_page
        
        # Get paginated orders
        stmt = (
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.shipping_address), selectinload(Order.user))
            .offset(offset)
            .limit(per_page)
            .order_by(Order.created_at.desc())
        )
        result = await session.exec(stmt)
        orders = result.all()
        
        return PaginatedOrderResponse(
            orders=[self._build_order_response(o) for o in orders],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    async def get_order(self, session: AsyncSession, order_uid: str) -> OrderResponse:
        stmt = select(Order).options(selectinload(Order.items), selectinload(Order.shipping_address)).where(Order.uid == order_uid)
        result = await session.exec(stmt)
        order = result.one_or_none()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return self._build_order_response(order)

    async def update_order_status(self, session: AsyncSession, order_uid: str, data: UpdateOrderStatus) -> OrderResponse:
        # Get the order with items and their products/variants
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items)
                .selectinload(OrderItem.product)
                .selectinload(Product.variant_groups)
                .selectinload(VariantGroup.choices),
                selectinload(Order.items).selectinload(OrderItem.variant_choice),
                selectinload(Order.shipping_address)
            )
            .where(Order.uid == order_uid)
        )
        result = await session.exec(stmt)
        order = result.one_or_none()
        
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        
        # Store previous status to check if we need to restore stock
        previous_status = order.status
        
        # Update the order status
        order.status = data.status
        session.add(order)
        
        try:
            # If order is being canceled, restore stock
            if data.status == OrderStatus.canceled and previous_status != OrderStatus.canceled:
                await self._restore_order_stock(session, order)
            
            # If order was canceled and is now being uncanceled, reduce stock again
            elif previous_status == OrderStatus.canceled and data.status != OrderStatus.canceled:
                await self._reduce_order_stock(session, order)
            
            await session.commit()
            
            # Refresh the order to get the latest state
            await session.refresh(order, attribute_names=["items", "shipping_address"])
            
            return self._build_order_response(order)
            
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update order status: {str(e)}"
            )
    
    async def _restore_order_stock(self, session: AsyncSession, order: Order) -> None:
        """Restore product stock when an order is canceled"""
        for item in order.items:
            if not item.product:
                continue
                
            product = item.product
            
            # If this is a variant product and has a variant choice
            if item.variant_choice:
                # Update variant stock directly using the loaded relationship
                item.variant_choice.stock += item.quantity
                session.add(item.variant_choice)
                self.logger.info(f"Restored {item.quantity} items to variant {item.variant_choice_id}, new stock: {item.variant_choice.stock}")
            elif hasattr(product, 'variant_groups') and product.variant_groups:
                # This is a variant product but no variant_choice is set - log a warning
                self.logger.warning(f"Order item {item.uid} appears to be a variant product but has no variant_choice set")
            else:
                # Update product stock for non-variant products
                stmt = (
                    update(Product)
                    .where(Product.uid == product.uid)
                    .values(stock=Product.stock + item.quantity)
                )
                await session.execute(stmt)
                self.logger.info(f"Restored {item.quantity} items to product {product.uid}")
            
            # Commit after each item to ensure changes are saved
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Failed to restore stock for order item {item.uid}: {str(e)}")
                raise
    
    async def _reduce_order_stock(self, session: AsyncSession, order: Order) -> None:
        """Reduce product stock when an order is uncanceled"""
        for item in order.items:
            if not item.product:
                continue
                
            product = item.product
            
            # If this is a variant product and has a variant choice
            if item.variant_choice:
                # Check if we have enough stock
                if item.variant_choice.stock < item.quantity:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Not enough stock for variant {item.variant_choice_id}"
                    )
                # Update variant stock directly using the loaded relationship
                item.variant_choice.stock -= item.quantity
                session.add(item.variant_choice)
                self.logger.info(f"Reduced {item.quantity} items from variant {item.variant_choice_id}, new stock: {item.variant_choice.stock}")
            elif hasattr(product, 'variant_groups') and product.variant_groups:
                # This is a variant product but no variant_choice is set - log a warning
                self.logger.warning(f"Order item {item.uid} appears to be a variant product but has no variant_choice set")
            else:
                # Check if we have enough stock for non-variant products
                if product.stock < item.quantity:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Not enough stock for product {product.uid}"
                    )
                # Update product stock for non-variant products
                stmt = (
                    update(Product)
                    .where(Product.uid == product.uid)
                    .values(stock=Product.stock - item.quantity)
                )
                await session.execute(stmt)
                self.logger.info(f"Reduced {item.quantity} items from product {product.uid}")
            
            # Commit after each item to ensure changes are saved
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Failed to reduce stock for order item {item.uid}: {str(e)}")
                raise

    @staticmethod
    def _build_order_response(order: Order) -> OrderResponse:
        shipping_data = order.shipping_address.model_dump() if order.shipping_address else {}
        items_data = []
        for item in order.items:
            if not item.product:
                continue
                
            product = item.product
            main_image = None
            if hasattr(product, 'images') and product.images:
                main_image = next((img for img in product.images if hasattr(img, 'is_main') and img.is_main), None)
                
            product_detail = {
                "uid": product.uid,
                "title": product.title,
                "main_image_url": main_image.filename if main_image and hasattr(main_image, 'filename') else None,
                "variant_groups": [vg.model_dump() for vg in getattr(product, 'variant_groups', [])]
            }
            item_data = item.model_dump()
            item_data["product"] = product_detail
            items_data.append(item_data)
        
        return OrderResponse(
            uid=order.uid,
            user_uid=order.user_uid,
            first_name=order.user.first_name,
            last_name=order.user.last_name,
            status=order.status,
            total_price=round(order.total_price, 2),
            shipping_price=round(order.shipping_price, 2),
            discount=round(order.discount, 2),
            final_price=round(order.final_price, 2),
            coupon_code=order.coupon_code,
            created_at=order.created_at,
            shipping_address=ShippingAddressModel(**shipping_data),
            items=[
                OrderItemResponse(
                    uid=data['uid'],
                    product_uid=data['product_uid'],
                    variant_choice_id=data.get('variant_choice_id'),  # Use get() to handle None
                    quantity=data['quantity'],
                    price_at_purchase=round(data['price_at_purchase'], 2),
                    total_price=round(data['total_price'], 2),
                    product=data['product']
                )
                for data in items_data
            ]
        )