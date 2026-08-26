import json
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Tuple


class DatabaseManager:
    """
    Thread-safe SQLite database manager for local peer storage.
    Orders messages causally using Lamport logical timestamps.
    """

    def __init__(self, username: str, peer_id: str) -> None:
        self.db_name = f"chat_{username}_{peer_id}.db"
        self.lock = threading.Lock()
        with self.lock:
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self._create_tables()

    def _create_tables(self) -> None:
        c = self.conn.cursor()
        # Messages table with Lamport timestamp support
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                msg_id TEXT PRIMARY KEY,
                contact_id TEXT,
                sender_name TEXT,
                content TEXT,
                timestamp TEXT,
                is_private INTEGER,
                lamport_time INTEGER DEFAULT 0
            )
            """
        )
        # Polls table
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS polls (
                poll_id TEXT PRIMARY KEY,
                question TEXT,
                options TEXT,
                end_time REAL,
                sender_id TEXT
            )
            """
        )
        # Votes table
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS votes (
                poll_id TEXT,
                choice INTEGER
            )
            """
        )
        # Files metadata table
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS shared_files (
                file_id TEXT PRIMARY KEY,
                filename TEXT,
                filesize INTEGER,
                sha256 TEXT,
                sender_name TEXT,
                local_path TEXT,
                timestamp TEXT
            )
            """
        )
        self.conn.commit()

    def save_message(
        self,
        msg_id: str,
        room_id: str,
        sender: str,
        content: str,
        is_private: bool,
        timestamp: Optional[str] = None,
        lamport_time: int = 0,
    ) -> bool:
        ts = timestamp if timestamp else time.strftime("%H:%M")
        with self.lock:
            try:
                self.conn.execute(
                    "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (msg_id, room_id, sender, content, ts, 1 if is_private else 0, lamport_time),
                )
                self.conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def update_message(self, msg_id: str, new_content: str) -> None:
        with self.lock:
            self.conn.execute(
                "UPDATE messages SET content=? WHERE msg_id=?",
                (new_content, msg_id),
            )
            self.conn.commit()

    def delete_message(self, msg_id: str) -> None:
        with self.lock:
            self.conn.execute("DELETE FROM messages WHERE msg_id=?", (msg_id,))
            self.conn.commit()

    def load_chat(self, room_id: str) -> List[Tuple[Any, ...]]:
        with self.lock:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT * FROM messages WHERE contact_id=? ORDER BY lamport_time ASC, timestamp ASC",
                (room_id,),
            )
            return cur.fetchall()

    def get_my_messages(self, my_name: str) -> List[Tuple[Any, ...]]:
        with self.lock:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT * FROM messages WHERE sender_name=? ORDER BY lamport_time DESC, timestamp DESC LIMIT 50",
                (my_name,),
            )
            return cur.fetchall()

    def get_global_history(self) -> List[Dict[str, Any]]:
        with self.lock:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT msg_id, contact_id, sender_name, content, timestamp, is_private, lamport_time "
                "FROM messages WHERE contact_id='broadcast' ORDER BY lamport_time ASC, timestamp ASC LIMIT 50"
            )
            rows = cur.fetchall()
            return [
                {
                    "msg_id": r[0],
                    "sender_name": r[2],
                    "content": r[3],
                    "timestamp": r[4],
                    "lamport_time": r[6],
                }
                for r in rows
            ]

    def save_poll(self, poll_data: Dict[str, Any]) -> None:
        opts_str = json.dumps(poll_data["options"])
        with self.lock:
            try:
                self.conn.execute(
                    "INSERT INTO polls VALUES (?, ?, ?, ?, ?)",
                    (
                        poll_data["id"],
                        poll_data["question"],
                        opts_str,
                        poll_data["end_time"],
                        poll_data["sender_id"],
                    ),
                )
                self.conn.commit()
            except sqlite3.IntegrityError:
                pass

    def save_vote(self, poll_id: str, choice: int) -> None:
        with self.lock:
            self.conn.execute("INSERT INTO votes VALUES (?, ?)", (poll_id, choice))
            self.conn.commit()

    def get_latest_poll(self) -> Optional[Dict[str, Any]]:
        with self.lock:
            cur = self.conn.cursor()
            cur.execute("SELECT * FROM polls ORDER BY end_time DESC LIMIT 1")
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "question": row[1],
                    "options": json.loads(row[2]),
                    "end_time": row[3],
                    "sender_id": row[4],
                }
            return None

    def get_poll_counts(self, poll_id: str) -> Dict[int, int]:
        with self.lock:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT choice, COUNT(*) FROM votes WHERE poll_id=? GROUP BY choice",
                (poll_id,),
            )
            return {r[0]: r[1] for r in cur.fetchall()}

    def save_shared_file(
        self,
        file_id: str,
        filename: str,
        filesize: int,
        sha256_hash: str,
        sender_name: str,
        local_path: str,
    ) -> None:
        ts = time.strftime("%H:%M")
        with self.lock:
            try:
                self.conn.execute(
                    "INSERT INTO shared_files VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (file_id, filename, filesize, sha256_hash, sender_name, local_path, ts),
                )
                self.conn.commit()
            except sqlite3.IntegrityError:
                pass

    def close(self) -> None:
        with self.lock:
            try:
                self.conn.close()
            except Exception:
                pass
