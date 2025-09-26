from celery import Celery
from src.config import Config
from src.admin_dashboard.mail import mail, create_message
from asgiref.sync import async_to_sync

# Explicit Celery config: use Redis for broker + backend
c_app = Celery(
    "taqa_backend",
    broker=Config.REDIS_URL,
    backend=Config.REDIS_URL
)

# Optional: production-safe defaults
c_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

@c_app.task(bind=True)
def send_email(self, recipients: list[str], subject: str, template_name: str, template_body: dict = None):
    if template_body is None:
        template_body = {}

    message = create_message(
        recipients=recipients,
        subject=subject,
        template_name=template_name,
        template_body=template_body,
    )

    async_to_sync(mail.send_message)(message=message, template_name=template_name)
    print(f"Email sent using template: {template_name}")
