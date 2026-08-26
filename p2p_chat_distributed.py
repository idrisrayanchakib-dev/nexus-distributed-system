"""
Backwards-compatible launcher and module facade for NEXUS P2P.
Delegates to the modular 'nexus' package architecture.
"""

from nexus.core.security import SecurityManager
from nexus.core.identity import IdentityManager
from nexus.core.clock import LamportClock
from nexus.core.database import DatabaseManager
from nexus.consensus.election import DistributedVotingEngine
from nexus.network.discovery import UDPDiscovery
from nexus.network.file_transfer import FileTransferManager
from nexus.network.node import P2PNode
from nexus.ui.app import MainApp

__all__ = [
    "SecurityManager",
    "IdentityManager",
    "LamportClock",
    "DatabaseManager",
    "DistributedVotingEngine",
    "UDPDiscovery",
    "FileTransferManager",
    "P2PNode",
    "MainApp",
]

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()