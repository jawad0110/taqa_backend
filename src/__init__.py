from fastapi import FastAPI, Depends

from src.auth.routes import auth_router
from src.auth.dependencies import admin_role_checker
from src.admin_dashboard.celery_tasks import send_email
from src.admin_dashboard.mail import mail, create_message

from src.admin_dashboard.products.routes import product_router
from src.admin_dashboard.reviews.routes import review_router
from src.admin_dashboard.discounts.routes import discount_router
from src.admin_dashboard.orders.routes import order_router
from src.admin_dashboard.shipping_rates.routes import shipping_rate_router
from src.admin_dashboard.users.routes import user_router

from src.admin_dashboard.overview.routes import overview_router
from src.admin_dashboard.statistics.sales_analytics.routes import sales_analytics_router
from src.admin_dashboard.statistics.earnings_analytics.routes import earnings_router
from src.admin_dashboard.statistics.recent_products_alerts.routes import recent_products_alerts_router
from src.admin_dashboard.statistics.storage_usage.routes import storage_usage_router
from src.admin_dashboard.statistics.variants_images_breakdown.routes import variants_images_breakdown_router

from src.user_dashboard.profile.routes import profile_router
from src.user_dashboard.products.routes import user_product_router
from src.user_dashboard.reviews.routes import user_review_router
from src.user_dashboard.cart.routes import user_cart_router
from src.user_dashboard.wishlist.routes import user_wishlist_router
from src.user_dashboard.checkouts.routes import user_checkout_router
from src.user_dashboard.shipping.routes import user_shipping_router

from .errors import register_all_errors
from .admin_dashboard.middleware import register_middleware

from fastapi.staticfiles import StaticFiles
import os

version = "v1"

app = FastAPI(
    title = "Taqa Store",
    description = " A REST API for a book review web service",
    version = version,
)

# Mount static file serving for product images
static_images_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "images", "products")
app.mount("/static/images/products", StaticFiles(directory=static_images_path), name="product_images")


register_all_errors(app)
register_middleware(app)


app.include_router(auth_router, prefix=f"/auth", tags = ['auth'])

app.include_router(product_router, prefix=f"/admin/products", tags=['admin products'], dependencies=[Depends(admin_role_checker)])
app.include_router(review_router, prefix=f"/admin/reviews", tags=['admin reviews'], dependencies=[Depends(admin_role_checker)])
app.include_router(discount_router, prefix=f"/admin/discounts", tags=["admin discounts"], dependencies=[Depends(admin_role_checker)])
app.include_router(order_router, prefix=f"/admin/orders", tags=["admin orders"], dependencies=[Depends(admin_role_checker)])
app.include_router(shipping_rate_router, prefix=f"/admin/shipping-rates", tags=["admin shipping"], dependencies=[Depends(admin_role_checker)])
app.include_router(user_router, prefix=f"/admin/users", tags=["admin users"], dependencies=[Depends(admin_role_checker)])

app.include_router(overview_router, prefix=f"/admin/overview", tags=["admin overview"], dependencies=[Depends(admin_role_checker)])
app.include_router(sales_analytics_router, prefix=f"/admin/sales-analytics", tags=["admin sales analytics"], dependencies=[Depends(admin_role_checker)])
app.include_router(earnings_router, prefix=f"/admin/earnings-analytics", tags=["admin earnings analytics"], dependencies=[Depends(admin_role_checker)])
app.include_router(recent_products_alerts_router, prefix=f"/admin/recent-products-alerts", tags=["admin recent products alerts"], dependencies=[Depends(admin_role_checker)])
app.include_router(storage_usage_router, prefix=f"/admin/storage-usage", tags=["admin storage usage"], dependencies=[Depends(admin_role_checker)])
app.include_router(variants_images_breakdown_router, prefix=f"/admin/variants-images-breakdown", tags=["admin variants images breakdown"], dependencies=[Depends(admin_role_checker)])

app.include_router(profile_router, prefix=f"/profile", tags = ['user profile'])
app.include_router(user_product_router, prefix=f"/products", tags = ['user products'])
app.include_router(user_review_router, prefix=f"/reviews", tags = ['user reviews'])
app.include_router(user_cart_router, prefix=f"/cart", tags = ['user cart'])
app.include_router(user_wishlist_router, prefix=f"/wishlist", tags = ['user wishlist'])
app.include_router(user_checkout_router, prefix=f"/checkouts", tags = ['user checkouts'])
app.include_router(user_shipping_router, prefix=f"/shipping", tags = ['user shipping'])
