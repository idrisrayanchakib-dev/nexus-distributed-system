import json
import socket
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from nexus.consensus.election import DistributedVotingEngine
from nexus.core.clock import LamportClock
from nexus.core.database import DatabaseManager
from nexus.core.identity import IdentityManager
from nexus.core.protocol import MessageType, PacketEnvelope
from nexus.core.security import SecurityManager
from nexus.network.discovery import UDPDiscovery
from nexus.network.file_transfer import FileTransferManager


class P2PNode:
    """
    Decentralized P2P Mesh Node.
    Coordinates socket connections, Lamport clock ordering, dynamic discovery,
    history synchronization, distributed elections, and encrypted file transfer.
    """

    PORT_RANGE = range(6000, 6030)
    BUFFER_SIZE = 65536

    def __init__(
        self,
        username: str,
        secret_key: str,
        specific_id: Optional[str] = None,
        on_event: Optional[Callable[[str, Any], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.username = username
        self.on_event = on_event or (lambda event_type, data: None)
        self.on_log = on_log or (lambda msg: None)

        self.security = SecurityManager(secret_key)
        self.identity = IdentityManager(username, specific_id)
        self.id = self.identity.id
        self.clock = LamportClock()
        self.db = DatabaseManager(username, self.id)
        self.election = DistributedVotingEngine(self.id)
        self.file_manager = FileTransferManager()

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.port = self._bind_to_free_port()
        self.peers: Dict[str, Dict[str, Any]] = {}
        self.running = True

        # Start TCP Listener
        threading.Thread(target=self._listen_for_incoming, daemon=True).start()

        # Start UDP Discovery
        self.discovery = UDPDiscovery(
            node_id=self.id,
            username=self.username,
            tcp_port=self.port,
            security=self.security,
            on_peer_discovered=self._handle_discovered_peer,
            on_log=self.on_log,
        )
        self.discovery.start_listening()

    def _bind_to_free_port(self) -> int:
        for p in self.PORT_RANGE:
            try:
                self.server_socket.bind(("0.0.0.0", p))
                self.server_socket.listen(10)
                return p
            except OSError:
                continue
        raise RuntimeError("No available TCP port in configured range (6000-6030).")

    def _handle_discovered_peer(self, ip: str, port: int, peer_id: str) -> None:
        if peer_id != self.id and not self.is_connected_to_port(port):
            threading.Thread(target=self.connect_to_node, args=(ip, port), daemon=True).start()

    def scan_network(self) -> None:
        self.on_log(f"Broadcasting discovery beacon (UDP {self.discovery.discovery_port} & Ports {min(self.PORT_RANGE)}-{max(self.PORT_RANGE)})...")
        threading.Thread(target=self.discovery.broadcast_beacon, daemon=True).start()

        # Localhost fallback scan for same-machine instances
        target_ip = "127.0.0.1"
        for p in self.PORT_RANGE:
            if p == self.port:
                continue
            if not self.is_connected_to_port(p):
                threading.Thread(target=self.connect_to_node, args=(target_ip, p), daemon=True).start()

    def is_connected_to_port(self, port: int) -> bool:
        for p in list(self.peers.values()):
            if str(p.get("port")) == str(port):
                return True
        return False

    def _listen_for_incoming(self) -> None:
        while self.running:
            try:
                client_sock, _ = self.server_socket.accept()
                time.sleep(0.05)
                self.send_handshake(client_sock)
                threading.Thread(target=self._handle_client_stream, args=(client_sock,), daemon=True).start()
            except Exception:
                break

    def connect_to_node(self, ip: str, port: int) -> None:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.6)
            s.connect((ip, int(port)))
            s.settimeout(None)
            time.sleep(0.05)
            self.send_handshake(s)
            threading.Thread(target=self._handle_client_stream, args=(s,), daemon=True).start()
        except Exception:
            pass

    def send_packet(self, sock: socket.socket, data: Dict[str, Any]) -> None:
        try:
            encrypted_str = self.security.encrypt(data) + "\n"
            sock.sendall(encrypted_str.encode("utf-8"))
        except Exception:
            pass

    def send_handshake(self, sock: socket.socket) -> None:
        packet = PacketEnvelope.create(
            msg_type=MessageType.HANDSHAKE,
            sender_id=self.id,
            sender_name=self.username,
            payload={"listen_port": self.port},
            lamport_time=self.clock.value,
        )
        self.send_packet(sock, packet)

    def _handle_client_stream(self, conn: socket.socket) -> None:
        buffer = ""
        peer_id = None
        while self.running:
            try:
                data = conn.recv(self.BUFFER_SIZE)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="ignore")

                while "\n" in buffer:
                    packet_str, buffer = buffer.split("\n", 1)
                    if not packet_str.strip():
                        continue

                    msg = self.security.decrypt(packet_str)
                    if msg == "WRONG_KEY":
                        conn.close()
                        return
                    if msg == "CORRUPTED" or not isinstance(msg, dict):
                        continue

                    msg_type = msg.get("type")
                    sender = msg.get("sender_id")
                    remote_clock = msg.get("lamport_time", 0)

                    # Update local Lamport Clock
                    current_clock = self.clock.update(remote_clock)

                    if msg_type == MessageType.HANDSHAKE.value:
                        peer_id = sender
                        if peer_id in self.peers and self.peers[peer_id].get("socket") != conn:
                            try:
                                self.peers[peer_id]["socket"].close()
                            except Exception:
                                pass
                        self.peers[peer_id] = {
                            "socket": conn,
                            "name": msg["sender_name"],
                            "port": msg["payload"]["listen_port"],
                        }
                        self.on_event("PEER_JOIN", dict(self.peers))
                        self.on_log(f"Connected to '{msg['sender_name']}' (Clock: {current_clock})")
                        threading.Thread(target=self._stream_history_to_peer, args=(conn,), daemon=True).start()

                    elif msg_type == MessageType.CHAT.value:
                        self.db.save_message(
                            msg["msg_id"],
                            "broadcast",
                            msg["sender_name"],
                            msg["payload"]["text"],
                            False,
                            msg.get("timestamp"),
                            remote_clock,
                        )
                        self.on_event("CHAT", msg)

                    elif msg_type == MessageType.HISTORY_ITEM.value:
                        item = msg["payload"]
                        saved = self.db.save_message(
                            item["msg_id"],
                            "broadcast",
                            item["sender_name"],
                            item["content"],
                            False,
                            item["timestamp"],
                            item.get("lamport_time", 0),
                        )
                        if saved:
                            self.on_event("REFRESH_CHAT", None)

                    elif msg_type == MessageType.GROUP_MSG.value:
                        self.db.save_message(
                            msg["msg_id"],
                            msg["room_id"],
                            msg["sender_name"],
                            msg["payload"]["text"],
                            True,
                            msg.get("timestamp"),
                            remote_clock,
                        )
                        self.on_event("GROUP_MSG", msg)

                    elif msg_type == MessageType.MSG_EDIT.value:
                        self.db.update_message(msg["payload"]["target_id"], msg["payload"]["new_text"])
                        self.on_event("REFRESH_CHAT", None)

                    elif msg_type == MessageType.MSG_DELETE.value:
                        self.db.delete_message(msg["payload"]["target_id"])
                        self.on_event("REFRESH_CHAT", None)

                    elif msg_type == MessageType.POLL_START.value:
                        self.election.register_remote_poll(msg["payload"])
                        self.db.save_poll(msg["payload"])
                        self.on_event("POLL_START", msg["payload"])

                    elif msg_type == MessageType.VOTE.value:
                        self.election.record_vote(msg["payload"]["poll_id"], msg["payload"]["choice"])
                        self.db.save_vote(msg["payload"]["poll_id"], msg["payload"]["choice"])
                        self.on_event("VOTE", msg["payload"])

                    elif msg_type == MessageType.POLL_RESULT.value:
                        self.on_event("POLL_RESULT", msg["payload"])

                    elif msg_type == MessageType.FILE_START.value:
                        self.file_manager.handle_incoming_start(msg["payload"], msg["sender_name"])
                        self.on_log(f"Receiving file '{msg['payload']['filename']}' from {msg['sender_name']}...")
                        self.on_event("FILE_START", msg["payload"])

                    elif msg_type == MessageType.FILE_CHUNK.value:
                        completed_file = self.file_manager.handle_incoming_chunk(msg["payload"])
                        if completed_file:
                            self.db.save_shared_file(
                                completed_file["file_id"],
                                completed_file["filename"],
                                completed_file["filesize"],
                                completed_file["sha256"],
                                completed_file["sender_name"],
                                completed_file["filepath"],
                            )
                            self.on_log(f"File '{completed_file['filename']}' downloaded and verified (SHA-256 OK)!")
                            self.on_event("FILE_COMPLETE", completed_file)
            except Exception:
                break

        if peer_id and peer_id in self.peers:
            del self.peers[peer_id]
            self.on_event("PEER_LEAVE", dict(self.peers))
        try:
            conn.close()
        except Exception:
            pass

    def _stream_history_to_peer(self, conn_socket: socket.socket) -> None:
        history = self.db.get_global_history()
        for item in history:
            packet = PacketEnvelope.create(
                msg_type=MessageType.HISTORY_ITEM,
                sender_id=self.id,
                sender_name=self.username,
                payload=item,
                lamport_time=item.get("lamport_time", 0),
            )
            self.send_packet(conn_socket, packet)
            time.sleep(0.02)

    # --- ACTION METHODS ---
    def broadcast_chat(self, text: str) -> None:
        l_time = self.clock.tick()
        msg_id = str(uuid.uuid4())
        packet = PacketEnvelope.create(
            msg_type=MessageType.CHAT,
            sender_id=self.id,
            sender_name=self.username,
            payload={"text": text},
            lamport_time=l_time,
            msg_id=msg_id,
        )
        for p in list(self.peers.values()):
            self.send_packet(p["socket"], packet)
        self.db.save_message(msg_id, "broadcast", self.username, text, False, lamport_time=l_time)

    def send_group_message(self, room_id: str, participants: List[str], text: str) -> None:
        l_time = self.clock.tick()
        msg_id = str(uuid.uuid4())
        packet = PacketEnvelope.create(
            msg_type=MessageType.GROUP_MSG,
            sender_id=self.id,
            sender_name=self.username,
            payload={"text": text},
            lamport_time=l_time,
            msg_id=msg_id,
            room_id=room_id,
            participants=participants,
        )
        for pid in participants:
            if pid == self.id:
                continue
            if pid in self.peers:
                self.send_packet(self.peers[pid]["socket"], packet)
        self.db.save_message(msg_id, room_id, self.username, text, True, lamport_time=l_time)

    def edit_message_net(self, msg_id: str, new_text: str) -> None:
        l_time = self.clock.tick()
        packet = PacketEnvelope.create(
            msg_type=MessageType.MSG_EDIT,
            sender_id=self.id,
            sender_name=self.username,
            payload={"target_id": msg_id, "new_text": new_text},
            lamport_time=l_time,
        )
        self.db.update_message(msg_id, new_text)
        for p in list(self.peers.values()):
            self.send_packet(p["socket"], packet)

    def delete_message_net(self, msg_id: str) -> None:
        l_time = self.clock.tick()
        packet = PacketEnvelope.create(
            msg_type=MessageType.MSG_DELETE,
            sender_id=self.id,
            sender_name=self.username,
            payload={"target_id": msg_id},
            lamport_time=l_time,
        )
        self.db.delete_message(msg_id)
        for p in list(self.peers.values()):
            self.send_packet(p["socket"], packet)

    def start_poll(self, question: str, options: List[str], duration: int = 30) -> Optional[Dict[str, Any]]:
        poll_data = self.election.create_poll(question, options, duration)
        if not poll_data:
            return None
        l_time = self.clock.tick()
        packet = PacketEnvelope.create(
            msg_type=MessageType.POLL_START,
            sender_id=self.id,
            sender_name=self.username,
            payload=poll_data,
            lamport_time=l_time,
        )
        for p in list(self.peers.values()):
            self.send_packet(p["socket"], packet)
        self.db.save_poll(poll_data)
        self.on_event("POLL_START", poll_data)
        return poll_data

    def cast_vote(self, poll_id: str, choice_idx: int) -> bool:
        if not self.election.record_vote(poll_id, choice_idx):
            return False
        l_time = self.clock.tick()
        packet = PacketEnvelope.create(
            msg_type=MessageType.VOTE,
            sender_id=self.id,
            sender_name=self.username,
            payload={"poll_id": poll_id, "choice": choice_idx},
            lamport_time=l_time,
        )
        for p in list(self.peers.values()):
            self.send_packet(p["socket"], packet)
        return True

    def broadcast_result(self, poll_id: str, counts_dict: Dict[int, int]) -> Dict[str, Any]:
        l_time = self.clock.tick()
        packet = PacketEnvelope.create(
            msg_type=MessageType.POLL_RESULT,
            sender_id=self.id,
            sender_name=self.username,
            payload={"poll_id": poll_id, "counts": counts_dict},
            lamport_time=l_time,
        )
        for p in list(self.peers.values()):
            self.send_packet(p["socket"], packet)
        return packet

    def send_file(self, filepath: str) -> None:
        """Transfers a local file to all connected peers in chunked packets."""
        file_meta = self.file_manager.prepare_file(filepath)
        l_time = self.clock.tick()

        # Send FILE_START packet
        start_packet = PacketEnvelope.create(
            msg_type=MessageType.FILE_START,
            sender_id=self.id,
            sender_name=self.username,
            payload=file_meta,
            lamport_time=l_time,
        )
        for p in list(self.peers.values()):
            self.send_packet(p["socket"], start_packet)

        # Stream chunks in background thread to avoid blocking UI
        def _stream_chunks() -> None:
            for idx in range(file_meta["total_chunks"]):
                chunk_b64 = self.file_manager.read_chunk(filepath, idx)
                chunk_packet = PacketEnvelope.create(
                    msg_type=MessageType.FILE_CHUNK,
                    sender_id=self.id,
                    sender_name=self.username,
                    payload={
                        "file_id": file_meta["file_id"],
                        "chunk_index": idx,
                        "chunk_data": chunk_b64,
                    },
                    lamport_time=self.clock.tick(),
                )
                for p in list(self.peers.values()):
                    self.send_packet(p["socket"], chunk_packet)
                time.sleep(0.01)
            self.on_log(f"Finished sending '{file_meta['filename']}' ({file_meta['filesize']} bytes).")

        threading.Thread(target=_stream_chunks, daemon=True).start()

    def stop(self) -> None:
        self.running = False
        self.discovery.stop()
        try:
            self.server_socket.close()
        except Exception:
            pass
        for p in list(self.peers.values()):
            try:
                p["socket"].close()
            except Exception:
                pass
        self.peers.clear()
        self.db.close()
