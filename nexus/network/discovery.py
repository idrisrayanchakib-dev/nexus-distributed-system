import socket
import threading
from typing import Callable, Optional

from nexus.core.security import SecurityManager


class UDPDiscovery:
    """
    Manages LAN auto-discovery by broadcasting and receiving UDP presence beacons.
    """

    DEFAULT_PORT = 60001

    def __init__(
        self,
        node_id: str,
        username: str,
        tcp_port: int,
        security: SecurityManager,
        on_peer_discovered: Callable[[str, int, str], None],
        on_log: Optional[Callable[[str], None]] = None,
        discovery_port: int = DEFAULT_PORT,
    ) -> None:
        self.node_id = node_id
        self.username = username
        self.tcp_port = tcp_port
        self.security = security
        self.on_peer_discovered = on_peer_discovered
        self.on_log = on_log or (lambda msg: None)
        self.discovery_port = discovery_port
        self.running = True
        self._listener_thread: Optional[threading.Thread] = None

    def start_listening(self) -> None:
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()

    def _listen_loop(self) -> None:
        try:
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp_sock.bind(("", self.discovery_port))
            while self.running:
                try:
                    data, addr = udp_sock.recvfrom(4096)
                    if not data:
                        continue
                    msg = self.security.decrypt(data.decode("utf-8", errors="ignore"))
                    if isinstance(msg, dict) and msg.get("type") == "DISCOVERY_BEACON":
                        sender_id = msg.get("sender_id")
                        listen_port = msg.get("listen_port")
                        sender_name = msg.get("sender_name", "Peer")
                        sender_ip = addr[0]

                        if sender_id and sender_id != self.node_id and listen_port:
                            self.on_log(f"Auto-discovered '{sender_name}' via UDP Beacon.")
                            self.on_peer_discovered(sender_ip, int(listen_port), sender_id)
                except Exception:
                    continue
        except Exception:
            pass

    def broadcast_beacon(self) -> None:
        try:
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            payload = {
                "type": "DISCOVERY_BEACON",
                "sender_id": self.node_id,
                "sender_name": self.username,
                "listen_port": self.tcp_port,
            }
            encrypted_bytes = self.security.encrypt(payload).encode("utf-8")
            for target in ["<broadcast>", "255.255.255.255", "127.0.0.1"]:
                try:
                    udp_sock.sendto(encrypted_bytes, (target, self.discovery_port))
                except Exception:
                    pass
            udp_sock.close()
        except Exception:
            pass

    def stop(self) -> None:
        self.running = False
