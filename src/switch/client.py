"""Client interface for Switch communication and Telegram group mirroring."""

import logging
import uuid
import httpx
from typing import Optional, List, Dict, Any, Callable
from src.config import SWITCH_SERVER_URL, SWITCH_ROOM_ID, TELEGRAM_CHAT_ID
from src.switch.protocol import SwitchProtocol
from src.switch.auth import generate_switch_auth_token

logger = logging.getLogger("switch.client")


class SwitchClient:
    def __init__(
        self,
        server_url: str = SWITCH_SERVER_URL,
        room_id: str = SWITCH_ROOM_ID,
        telegram_chat_id: str = TELEGRAM_CHAT_ID,
        on_message_callback: Optional[Callable[[str, str, str], None]] = None,
        deliver_live: bool = True,
    ):
        self.server_url = server_url.rstrip("/")
        self.room_id = room_id
        self.telegram_chat_id = telegram_chat_id
        self.on_message_callback = on_message_callback
        self.deliver_live = deliver_live
        self.message_history: List[Dict[str, Any]] = []
        self._auth_token = generate_switch_auth_token() if deliver_live else None

    def _get_cookies(self) -> Dict[str, str]:
        return {"switch_auth": self._auth_token or ""}

    def post_to_room(self, sender: str, text: str, target: Optional[str] = None) -> Dict[str, Any]:
        """Post a message to the Switch room, automatically mirrored to Telegram."""
        if target:
            formatted_text = SwitchProtocol.format_targeted_message(target, text)
        else:
            formatted_text = text

        record = {
            "sender": sender,
            "target": target,
            "body": formatted_text,
            "room_id": self.room_id,
            "telegram_chat_id": self.telegram_chat_id,
        }
        self.message_history.append(record)

        # Notify callback if registered
        if self.on_message_callback:
            try:
                self.on_message_callback(sender, target or "everyone", formatted_text)
            except Exception as e:
                logger.warning(f"Error in message callback: {e}")

        delivered = False
        if self.deliver_live:
            try:
                url = f"{self.server_url}/gateway/chats/{self.room_id}/messages"
                payload = {
                    "requestId": str(uuid.uuid4()),
                    "body": f"[{sender}] {formatted_text}"
                }
                with httpx.Client(timeout=4.0) as client:
                    res = client.post(url, json=payload, cookies=self._get_cookies())
                    if res.status_code in (200, 201, 202):
                        delivered = True
                    else:
                        logger.warning(f"Switch returned status {res.status_code}: {res.text}")
            except Exception as e:
                logger.warning(f"Switch delivery failed: {e}")
                delivered = False

        record["delivered_to_live_switch"] = delivered
        return record

    def get_room_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch the latest messages from the Switch room."""
        if not self.deliver_live:
            return []
        try:
            url = f"{self.server_url}/gateway/chats/{self.room_id}/messages"
            params = {"limit": limit}
            with httpx.Client(timeout=5.0) as client:
                res = client.get(url, params=params, cookies=self._get_cookies())
                if res.status_code == 200:
                    return res.json().get("messages", [])
                else:
                    logger.warning(f"Failed to fetch messages: {res.status_code}")
                    return []
        except Exception as e:
            logger.warning(f"Error fetching room messages: {e}")
            return []
