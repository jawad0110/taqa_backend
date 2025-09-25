from fastapi_mail import FastMail, ConnectionConfig, MessageSchema, MessageType # type: ignore
from jinja2 import Environment, FileSystemLoader
from src.config import Config
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent


mail_config = ConnectionConfig(
    MAIL_USERNAME = Config.MAIL_USERNAME,
    MAIL_PASSWORD = Config.MAIL_PASSWORD,
    MAIL_FROM = Config.MAIL_FROM,
    MAIL_PORT = 587,
    MAIL_SERVER = Config.MAIL_SERVER,
    MAIL_FROM_NAME= Config.MAIL_FROM_NAME,
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True,
    TEMPLATE_FOLDER = Path(BASE_DIR, 'templates')
)


mail = FastMail(
    config = mail_config
)

def create_message(recipients: list[str], subject: str, template_name: str, template_body: dict = None):
    if template_body is None:
        template_body = {}
    
    # Set up Jinja2 environment
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    env = Environment(loader=FileSystemLoader(template_dir))
    
    # Load and render the template
    template = env.get_template(template_name)
    html_content = template.render(**template_body)
    
    message = MessageSchema(
        recipients=recipients,
        subject=subject,
        body=html_content,
        subtype=MessageType.html
    )
    
    return message