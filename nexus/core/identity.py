import json
import os
import uuid
from typing import Optional


class IdentityManager:
    """
    Manages persistent peer cryptographic identities (UUIDs) and short-hash
    account recovery mechanisms.
    """

    def __init__(self, username: str, partial_id: Optional[str] = None) -> None:
        self.username = username
        self.filename = ""
        self.id = ""

        if partial_id and partial_id.strip():
            short_id = partial_id.strip()
            found_full_id = self.find_file_by_partial_id(short_id)
            if found_full_id:
                self.id = found_full_id
            else:
                self.id = short_id
            self.filename = f"identity_{username}_{self.id}.json"
            self.save_identity()
        else:
            self.id = str(uuid.uuid4())
            self.filename = f"identity_{username}_{self.id}.json"
            self.save_identity()

    def find_file_by_partial_id(self, short_id: str) -> Optional[str]:
        prefix = f"identity_{self.username}_"
        try:
            for fname in os.listdir("."):
                if fname.startswith(prefix) and fname.endswith(".json"):
                    full_id = fname[len(prefix) : -5]
                    if full_id.startswith(short_id):
                        return full_id
        except Exception:
            pass
        return None

    def save_identity(self) -> None:
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump({"username": self.username, "id": self.id}, f, indent=2)
        except Exception:
            pass
