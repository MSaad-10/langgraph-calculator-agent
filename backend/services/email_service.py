import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv


load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


# Function to generate and send OTP
def send_otp_email(recipient_email: str, otp: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Calculator Agent - Email Verification"
    message["From"] = SMTP_USERNAME
    message["To"] = recipient_email
    message.set_content(
        f"""
Hello,

Your Calculator Agent verification code is:

{otp}

This code will expire in 5 minutes.

If you did not create an account, you can ignore this email.

Regards,
Calculator Agent
"""
    )
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:  # type: ignore
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)  # type: ignore
        server.send_message(message)


# Function to create and send Password Reset Email
def send_password_reset_email(recipient_email: str, reset_token: str,) -> None:

    reset_url = ("http://localhost:8501"f"/?page=reset-password&token={reset_token}")
    
    message = EmailMessage()
    
    message["Subject"] = "Calculator Agent - Reset Your Password"
    message["From"] = SMTP_USERNAME
    message["To"] = recipient_email

    message.set_content(
        f"""
Hello,

We received a request to reset your Calculator Agent password.

Click the link below to reset your password:

{reset_url}

This link will expire in 15 minutes.

If you did not request a password reset, you can ignore
this email.

Regards,
Calculator Agent
"""
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:  # type: ignore
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)  # type: ignore
        server.send_message(message)