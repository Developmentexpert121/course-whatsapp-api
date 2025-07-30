import asyncio
import logging
import os
import httpx

logger = logging.getLogger(__name__)


class WhatsAppService:
    @staticmethod
    async def async_send_message(
        phone_number_id: str, to: str, message: str
    ) -> httpx.Response:
        """Send a WhatsApp message asynchronously"""
        try:
            access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
            if not access_token:
                raise ValueError("WHATSAPP_ACCESS_TOKEN not configured")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://graph.facebook.com/v18.0/{phone_number_id}/messages",
                    json={
                        "messaging_product": "whatsapp",
                        "recipient_type": "individual",
                        "to": to,
                        "type": "text",
                        "text": {"body": message},
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                return response
        except Exception as e:
            logger.exception("Error sending WhatsApp message")
            raise

    @staticmethod
    def send_message(phone_number_id: str, to: str, message: str) -> httpx.Response:
        """Synchronously send a WhatsApp message"""
        try:
            # Create a new event loop for the synchronous context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                WhatsAppService.async_send_message(phone_number_id, to, message)
            )
        except Exception as e:
            logger.exception("Error in synchronous message sending")
            raise
        finally:
            loop.close()
