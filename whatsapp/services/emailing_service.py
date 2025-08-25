import os
import smtplib
import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import List, Optional

logger = logging.getLogger(__name__)


class EmailService:
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER")  # Your email
    SMTP_PASS = os.getenv("SMTP_PASS")  # App password or SMTP password

    @staticmethod
    async def async_send_email(
        subject: str,
        body: str,
        to: List[str],
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        html: bool = False,
    ):
        """Send an email asynchronously"""
        try:
            msg = MIMEMultipart()
            msg["From"] = EmailService.SMTP_USER
            msg["To"] = ", ".join(to)
            if cc:
                msg["Cc"] = ", ".join(cc)
            msg["Subject"] = subject

            # Body (plain text or HTML)
            if html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))

            # Attach files
            if attachments:
                for file_path in attachments:
                    with open(file_path, "rb") as f:
                        part = MIMEApplication(
                            f.read(), Name=os.path.basename(file_path)
                        )
                        part["Content-Disposition"] = (
                            f'attachment; filename="{os.path.basename(file_path)}"'
                        )
                        msg.attach(part)

            recipients = to + (cc or []) + (bcc or [])

            # Send
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, EmailService._send_smtp, msg, recipients)

            return {"status": "success", "to": recipients}

        except Exception as e:
            logger.exception("Error sending email")
            raise

    @staticmethod
    def _send_smtp(msg, recipients):
        """Handles raw SMTP sending"""
        with smtplib.SMTP(EmailService.SMTP_HOST, EmailService.SMTP_PORT) as server:
            server.starttls()
            server.login(EmailService.SMTP_USER, EmailService.SMTP_PASS)
            server.sendmail(msg["From"], recipients, msg.as_string())

    # --------- SYNC WRAPPERS ---------
    @staticmethod
    def send_simple_email(subject: str, body: str, to: List[str]):
        """Send simple plain text email"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                EmailService.async_send_email(subject, body, to)
            )
        finally:
            loop.close()

    @staticmethod
    def send_email_with_file(
        subject: str, body: str, to: List[str], attachments: List[str]
    ):
        """Send email with attachments"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                EmailService.async_send_email(
                    subject, body, to, attachments=attachments
                )
            )
        finally:
            loop.close()

    @staticmethod
    def send_email_with_template(
        subject: str,
        html_body: str,
        to: List[str],
        attachments: Optional[List[str]] = None,
    ):
        """Send email with HTML template"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                EmailService.async_send_email(
                    subject, html_body, to, attachments=attachments, html=True
                )
            )
        finally:
            loop.close()
