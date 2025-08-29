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

            # print(
            #     "Whatsapp message payload: ",
            #     {
            #         "messaging_product": "whatsapp",
            #         "recipient_type": "individual",
            #         "to": to,
            #         "type": "text",
            #         "text": {"body": message},
            #     },
            # )
            print("[Sending to WhatsApp]:", message)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://graph.facebook.com/v22.0/{phone_number_id}/messages",
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
            print("Error sending WhatsApp message:", e)
            logger.exception("Error sending WhatsApp message")
            raise

    @staticmethod
    async def async_send_file(
        phone_number_id: str, to: str, file_url: str, filename: str
    ) -> httpx.Response:
        """Send a file to WhatsApp asynchronously"""
        try:
            access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
            if not access_token:
                raise ValueError("WHATSAPP_ACCESS_TOKEN not configured")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://graph.facebook.com/v22.0/{phone_number_id}/messages",
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "document",
                        "document": {"link": file_url, "filename": filename},
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                return response
        except Exception as e:
            logger.exception("Error sending WhatsApp file")
            raise

    @staticmethod
    async def async_send_file_with_message(
        phone_number_id: str, to: str, file_url: str, filename: str, message: str
    ) -> httpx.Response:
        """Send a file with a caption/message to WhatsApp asynchronously"""
        try:
            access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
            if not access_token:
                raise ValueError("WHATSAPP_ACCESS_TOKEN not configured")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://graph.facebook.com/v22.0/{phone_number_id}/messages",
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "document",
                        "document": {
                            "link": file_url,
                            "filename": filename,
                            "caption": message,
                        },
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                return response
        except Exception as e:
            logger.exception("Error sending WhatsApp file with message")
            raise

    @staticmethod
    async def async_send_images_with_message(
        phone_number_id: str, to: str, images: list[dict], message: str = ""
    ) -> None:
        """
        Send multiple images to WhatsApp asynchronously.
        - First image will carry the message as its caption
        - Remaining images will be sent without captions
        `images` should be a list of dicts like: [{"url": "...", "caption": "..."}, ...]
        """
        try:
            access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
            if not access_token:
                raise ValueError("WHATSAPP_ACCESS_TOKEN not configured")

            async with httpx.AsyncClient(timeout=30.0) as client:
                for idx, img in enumerate(images):
                    img_url = img.get("url")
                    if not img_url:
                        continue

                    # First image: attach main message (ignore image.caption)
                    # Other images: send without caption
                    caption = message if idx == 0 else img.get("caption", "")

                    response = await client.post(
                        f"https://graph.facebook.com/v22.0/{phone_number_id}/messages",
                        json={
                            "messaging_product": "whatsapp",
                            "to": to,
                            "type": "image",
                            "image": {"link": img_url, "caption": caption},
                        },
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json",
                        },
                    )
                    response.raise_for_status()

        except Exception:
            logger.exception("Error sending multiple images with captioned first image")
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

    @staticmethod
    def send_file(
        phone_number_id: str, to: str, file_url: str, filename: str
    ) -> httpx.Response:
        """Synchronously send a WhatsApp file"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                WhatsAppService.async_send_file(phone_number_id, to, file_url, filename)
            )
        finally:
            loop.close()

    @staticmethod
    def send_file_with_message(
        phone_number_id: str, to: str, file_url: str, filename: str, message: str
    ) -> httpx.Response:
        """Synchronously send a WhatsApp file with message"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                WhatsAppService.async_send_file_with_message(
                    phone_number_id, to, file_url, filename, message
                )
            )
        finally:
            loop.close()

    @staticmethod
    def send_images_with_message(
        phone_number_id: str, to: str, images: list[dict], message: str
    ) -> None:
        """Synchronously send multiple WhatsApp images followed by a message"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                WhatsAppService.async_send_images_with_message(
                    phone_number_id=phone_number_id,
                    to=to,
                    images=images,
                    message=message,
                )
            )
        finally:
            loop.close()
