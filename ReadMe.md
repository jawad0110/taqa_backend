taqa_website/
├── backend/
│   ├── .env
│   ├── .gitignore
│   ├── ReadMe.md
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── migrations/
│   ├── taqa_env/
│   └── src/
│       ├── __init__.py
│       ├── config.py
│       ├── errors.py
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── dependencies.py
│       │   ├── routes.py
│       │   ├── schemas.py
│       │   ├── service.py
│       │   └── utils.py
│       ├── db/
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── models.py
│       │   ├── redis.py
│       │   └── static/
│       │       └── images/
│       ├── admin_dashboard/
│       │   ├── celery_tasks.py
│       │   ├── mail.py
│       │   ├── middleware.py
│       │   ├── overview/                # Dashboard Overview page
│       │   │   ├── __init__.py
│       │   │   ├── routes.py
│       │   │   ├── schemas.py
│       │   │   └── service.py
│       │   ├── statistics/
│       │   │   ├── sales_analytics/         # Sales Analytics page
│       │   │   │   ├── __init__.py
│       │   │   │   ├── routes.py
│       │   │   │   ├── schemas.py
│       │   │   │   └── service.py
│       │   │   ├── recent_products_alerts/  # Recent Products & Alerts
│       │   │   │   ├── __init__.py
│       │   │   │   ├── routes.py
│       │   │   │   ├── schemas.py
│       │   │   │   └── service.py
│       │   │   ├── storage_usage/           # Storage Usage page
│       │   │   │   ├── __init__.py
│       │   │   │   ├── routes.py
│       │   │   │   ├── schemas.py
│       │   │   │   └── service.py
│       │   │   └── variants_images_breakdown/  # Variants & Images Breakdown
│       │   │       ├── __init__.py
│       │   │       ├── routes.py
│       │   │       ├── schemas.py
│       │   │       └── service.py
│       │   ├── categories/
│       │   │   ├── __init__.py
│       │   │   ├── routes.py
│       │   │   ├── schemas.py
│       │   │   └── service.py
│       │   ├── discounts/
│       │   │   ├── __init__.py
│       │   │   ├── routes.py
│       │   │   ├── schemas.py
│       │   │   └── service.py
│       │   ├── orders/
│       │   │   ├── __init__.py
│       │   │   ├── routes.py
│       │   │   ├── schemas.py
│       │   │   └── service.py
│       │   ├── products/
│       │   │   ├── __init__.py
│       │   │   ├── routes.py
│       │   │   ├── schemas.py
│       │   │   └── service.py
│       │   ├── reviews/
│       │   │   ├── __init__.py
│       │   │   ├── routes.py
│       │   │   ├── schemas.py
│       │   │   └── service.py
│       │   ├── shipping_rates/
│       │   │   ├── routes.py
│       │   │   ├── schemas.py
│       │   │   └── service.py
│       │   └── templates/
│       │       ├── email_verification.html
│       │       ├── notification.html
│       │       ├── password_reset.html
│       │       ├── welcome.html
│       │       └── static/
│       └── user_side/
│           ├── cart/
│           │   ├── __init__.py
│           │   ├── routes.py
│           │   ├── schemas.py
│           │   └── service.py
│           ├── categories/
│           │   ├── __init__.py
│           │   ├── routes.py
│           │   ├── schemas.py
│           │   └── service.py
│           ├── checkouts/
│           │   ├── __init__.py
│           │   ├── routes.py
│           │   ├── schemas.py
│           │   └── service.py
│           ├── home/
│           │   ├── __init__.py
│           │   ├── routes.py
│           │   ├── schemas.py
│           │   └── service.py
│           ├── products/
│           │   ├── __init__.py
│           │   ├── routes.py
│           │   ├── schemas.py
│           │   └── service.py
│           ├── reviews/
│           │   ├── __init__.py
│           │   ├── routes.py
│           │   ├── schemas.py
│           │   └── service.py
│           └── profile/
└── frontend/