from celery import Celery
from src.admin_dashboard.mail import mail, create_message
from asgiref.sync import async_to_sync

c_app = Celery()

c_app.config_from_object('src.config')


@c_app.task(bind=True)
def send_email(self, recipients: list[str], subject: str, template_name: str, template_body: dict = None):
    if template_body is None:
        template_body = {}
        
    message = create_message(
        recipients=recipients,
        subject=subject,
        template_name=template_name,
        template_body=template_body
    )
    
    async_to_sync(mail.send_message)(message=message, template_name=template_name)
    print(f"Email sent using template: {template_name}")
