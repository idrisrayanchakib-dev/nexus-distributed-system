import base64
import hashlib
import os
import uuid
from typing import Any, Callable, Dict, List, Optional


class FileTransferManager:
    """
    Manages peer-to-peer chunked file transfer with SHA-256 integrity validation.
    """

    CHUNK_SIZE = 32768  # 32 KB binary chunks

    def __init__(self, download_dir: str = "downloads") -> None:
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        # file_id -> { filename, total_size, total_chunks, sha256, received_chunks, sender_name }
        self.incoming_transfers: Dict[str, Dict[str, Any]] = {}

    def prepare_file(self, filepath: str) -> Dict[str, Any]:
        """Prepares a local file for chunked transmission and computes SHA-256."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        filesize = os.path.getsize(filepath)
        filename = os.path.basename(filepath)
        file_id = str(uuid.uuid4())

        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(self.CHUNK_SIZE):
                hasher.update(chunk)

        total_chunks = (filesize + self.CHUNK_SIZE - 1) // self.CHUNK_SIZE if filesize > 0 else 1
        return {
            "file_id": file_id,
            "filename": filename,
            "filesize": filesize,
            "total_chunks": total_chunks,
            "sha256": hasher.hexdigest(),
            "filepath": filepath,
        }

    def read_chunk(self, filepath: str, chunk_index: int) -> str:
        """Reads a specific chunk from a file and returns it as a base64 string."""
        with open(filepath, "rb") as f:
            f.seek(chunk_index * self.CHUNK_SIZE)
            data = f.read(self.CHUNK_SIZE)
            return base64.b64encode(data).decode("utf-8")

    def handle_incoming_start(self, payload: Dict[str, Any], sender_name: str) -> None:
        """Registers a new incoming file transfer."""
        file_id = payload["file_id"]
        self.incoming_transfers[file_id] = {
            "filename": payload["filename"],
            "filesize": payload["filesize"],
            "total_chunks": payload["total_chunks"],
            "sha256": payload["sha256"],
            "received_chunks": {},
            "sender_name": sender_name,
        }

    def handle_incoming_chunk(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Stores an incoming chunk. When all chunks are received, reassembles and verifies
        the file integrity using SHA-256. Returns metadata if complete, otherwise None.
        """
        file_id = payload["file_id"]
        chunk_idx = payload["chunk_index"]
        chunk_data_b64 = payload["chunk_data"]

        if file_id not in self.incoming_transfers:
            return None

        transfer = self.incoming_transfers[file_id]
        transfer["received_chunks"][chunk_idx] = base64.b64decode(chunk_data_b64.encode("utf-8"))

        if len(transfer["received_chunks"]) == transfer["total_chunks"]:
            # Reassemble file
            dest_path = os.path.join(self.download_dir, transfer["filename"])
            # Avoid overwriting existing files
            base_name, ext = os.path.splitext(transfer["filename"])
            counter = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(self.download_dir, f"{base_name}_{counter}{ext}")
                counter += 1

            hasher = hashlib.sha256()
            with open(dest_path, "wb") as out_f:
                for idx in range(transfer["total_chunks"]):
                    chunk_bytes = transfer["received_chunks"][idx]
                    hasher.update(chunk_bytes)
                    out_f.write(chunk_bytes)

            actual_hash = hasher.hexdigest()
            is_valid = actual_hash == transfer["sha256"]

            result = {
                "file_id": file_id,
                "filename": os.path.basename(dest_path),
                "filepath": dest_path,
                "filesize": transfer["filesize"],
                "sha256": actual_hash,
                "is_valid": is_valid,
                "sender_name": transfer["sender_name"],
            }
            del self.incoming_transfers[file_id]
            return result

        return None
