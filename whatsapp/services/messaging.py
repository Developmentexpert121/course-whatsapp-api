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
    async def async_send_list_message(
        phone_number_id: str,
        to: str,
        header: str,
        body: str,
        footer: str,
        button_text: str,
        sections: list[dict],
    ) -> httpx.Response:
        """
        Send a WhatsApp interactive list message asynchronously.

        sections example:
        [
            {
                "title": "Account Services",
                "rows": [
                    {"id": "check_balance", "title": "💰 Check Balance", "description": "View balance"},
                    {"id": "recent_txn", "title": "📜 Recent Transactions", "description": "See last 5"}
                ]
            },
            {
                "title": "Support",
                "rows": [
                    {"id": "contact_agent", "title": "👨‍💻 Talk to Agent", "description": "Human support"}
                ]
            }
        ]
        """
        try:
            access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
            if not access_token:
                raise ValueError("WHATSAPP_ACCESS_TOKEN not configured")

            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "header": {"type": "text", "text": header},
                    "body": {"text": body},
                    "footer": {"text": footer},
                    "action": {"button": button_text, "sections": sections},
                },
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://graph.facebook.com/v22.0/{phone_number_id}/messages",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                return response
        except Exception:
            logger.exception("Error sending WhatsApp list message")
            raise

    @staticmethod
    async def async_send_button_message(
        phone_number_id: str,
        to: str,
        body: str,
        buttons: list[dict],
        header: str = None,
        footer: str = None,
    ) -> httpx.Response:
        """
        Send a WhatsApp interactive button message asynchronously.

        buttons example (max 3):
        [
            {"id": "check_status", "title": "📦 Check Status"},
            {"id": "talk_agent", "title": "💬 Talk to Agent"}
        ]
        """
        try:
            access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
            if not access_token:
                raise ValueError("WHATSAPP_ACCESS_TOKEN not configured")

            # Build button objects
            button_objects = [
                {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                for b in buttons[:3]
            ]

            interactive = {
                "type": "button",
                "body": {"text": body},
                "action": {"buttons": button_objects},
            }

            if header:
                interactive["header"] = {"type": "text", "text": header}
            if footer:
                interactive["footer"] = {"text": footer}

            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": interactive,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://graph.facebook.com/v22.0/{phone_number_id}/messages",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                return response
        except Exception:
            logger.exception("Error sending WhatsApp button message")
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

    @staticmethod
    def send_list_message(
        phone_number_id: str,
        to: str,
        header: str,
        body: str,
        footer: str,
        button_text: str,
        sections: list[dict],
    ) -> httpx.Response:
        """Synchronously send a WhatsApp interactive list message"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                WhatsAppService.async_send_list_message(
                    phone_number_id, to, header, body, footer, button_text, sections
                )
            )
        finally:
            loop.close()

    @staticmethod
    def send_button_message(
        phone_number_id: str,
        to: str,
        body: str,
        buttons: list[dict],
        header: str = None,
        footer: str = None,
    ) -> httpx.Response:
        """Synchronously send a WhatsApp interactive button message"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                WhatsAppService.async_send_button_message(
                    phone_number_id, to, body, buttons, header, footer
                )
            )
        finally:
            loop.close()
