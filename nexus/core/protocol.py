from enum import Enum
from typing import Any, Dict, List, Optional
import time
import uuid


class MessageType(str, Enum):
    HANDSHAKE = "HANDSHAKE"
    DISCOVERY_BEACON = "DISCOVERY_BEACON"
    CHAT = "CHAT"
    GROUP_MSG = "GROUP_MSG"
    MSG_EDIT = "MSG_EDIT"
    MSG_DELETE = "MSG_DELETE"
    HISTORY_ITEM = "HISTORY_ITEM"
    POLL_START = "POLL_START"
    VOTE = "VOTE"
    POLL_RESULT = "POLL_RESULT"
    FILE_START = "FILE_START"
    FILE_CHUNK = "FILE_CHUNK"
    FILE_COMPLETE = "FILE_COMPLETE"


class PacketEnvelope:
    """Standard typed envelope structure for all P2P network packets."""

    @staticmethod
    def create(
        msg_type: MessageType,
        sender_id: str,
        sender_name: str,
        payload: Dict[str, Any],
        lamport_time: int = 0,
        msg_id: Optional[str] = None,
        room_id: Optional[str] = None,
        participants: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        packet: Dict[str, Any] = {
            "type": msg_type.value if isinstance(msg_type, MessageType) else str(msg_type),
            "msg_id": msg_id or str(uuid.uuid4()),
            "sender_id": sender_id,
            "sender_name": sender_name,
            "lamport_time": lamport_time,
            "timestamp": time.strftime("%H:%M"),
            "payload": payload,
        }
        if room_id:
            packet["room_id"] = room_id
        if participants:
            packet["participants"] = participants
        return packet
