import os
import threading
import time
import unittest

from nexus.consensus.election import DistributedVotingEngine
from nexus.core.clock import LamportClock
from nexus.core.database import DatabaseManager
from nexus.core.identity import IdentityManager
from nexus.core.security import SecurityManager
from nexus.network.node import P2PNode

TEST_USER_A = "test_alice"
TEST_USER_B = "test_bob"
TEST_KEY = "test_network_secret_123"
WRONG_KEY = "wrong_network_secret_999"


class TestP2PModularSystem(unittest.TestCase):

    def setUp(self):
        self._cleanup()

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        for fname in os.listdir("."):
            if fname.startswith("chat_test_") or fname.startswith("identity_test_"):
                try:
                    os.remove(fname)
                except Exception:
                    pass

    # ==========================================
    # 1. SECURITY TESTS
    # ==========================================
    def test_encryption_and_decryption(self):
        sec = SecurityManager(TEST_KEY)
        payload = {"type": "CHAT", "text": "Top Tier Modular P2P 🚀", "msg_id": "123"}
        encrypted = sec.encrypt(payload)
        self.assertIsInstance(encrypted, str)
        self.assertEqual(sec.decrypt(encrypted), payload)

    def test_wrong_key_rejection(self):
        sec1 = SecurityManager(TEST_KEY)
        sec2 = SecurityManager(WRONG_KEY)
        encrypted = sec1.encrypt({"secret": "data"})
        self.assertEqual(sec2.decrypt(encrypted), "WRONG_KEY")

    def test_fingerprint_isolation(self):
        sec1 = SecurityManager(TEST_KEY)
        sec2 = SecurityManager(TEST_KEY)
        sec_diff = SecurityManager(WRONG_KEY)
        self.assertEqual(sec1.get_fingerprint(), sec2.get_fingerprint())
        self.assertNotEqual(sec1.get_fingerprint(), sec_diff.get_fingerprint())

    # ==========================================
    # 2. IDENTITY & RECOVERY TESTS
    # ==========================================
    def test_identity_and_recovery(self):
        ident = IdentityManager(TEST_USER_A)
        recovered = IdentityManager(TEST_USER_A, partial_id=ident.id[:4])
        self.assertEqual(ident.id, recovered.id)

    # ==========================================
    # 3. DATABASE & LAMPORT CAUSALITY
    # ==========================================
    def test_database_and_lamport_ordering(self):
        db = DatabaseManager(TEST_USER_A, "peer_001")
        try:
            # Insert message with clock = 2
            db.save_message("m2", "broadcast", "Bob", "Later message", False, "12:01", lamport_time=2)
            # Insert message with clock = 1
            db.save_message("m1", "broadcast", "Alice", "Earlier message", False, "12:00", lamport_time=1)

            history = db.get_global_history()
            self.assertEqual(len(history), 2)
            # Must be ordered by Lamport logical clock
            self.assertEqual(history[0]["msg_id"], "m1")
            self.assertEqual(history[1]["msg_id"], "m2")
        finally:
            db.close()

    def test_concurrent_database_writes(self):
        db = DatabaseManager(TEST_USER_A, "concurrent_peer")
        errors = []
        try:
            def worker(idx):
                try:
                    for i in range(15):
                        db.save_message(f"m_{idx}_{i}", "broadcast", f"user_{idx}", f"msg {i}", False)
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
            for t in threads: t.start()
            for t in threads: t.join()

            self.assertEqual(len(errors), 0)
        finally:
            db.close()

    # ==========================================
    # 4. CONSENSUS ENGINE TESTS
    # ==========================================
    def test_election_engine(self):
        engine = DistributedVotingEngine("leader_node")
        poll = engine.create_poll("Best Framework?", ["A", "B"], duration_seconds=10)
        self.assertIsNotNone(poll)
        self.assertTrue(engine.is_leader())

        engine.record_vote(poll["id"], 0)
        engine.record_vote(poll["id"], 0)
        engine.record_vote(poll["id"], 1)

        tallies = engine.compute_tallies()
        self.assertEqual(tallies[0], 2)
        self.assertEqual(tallies[1], 1)

    # ==========================================
    # 5. P2P FULL MESH NODE INTEGRATION
    # ==========================================
    def test_p2p_mesh_communication_and_clocks(self):
        events_a = []
        events_b = []

        node_a = P2PNode(TEST_USER_A, TEST_KEY, None, lambda t, d: events_a.append((t, d)), lambda log: None)
        node_b = P2PNode(TEST_USER_B, TEST_KEY, None, lambda t, d: events_b.append((t, d)), lambda log: None)

        try:
            node_b.connect_to_node("127.0.0.1", node_a.port)
            time.sleep(0.5)

            self.assertTrue(node_b.id in node_a.peers or node_a.id in node_b.peers)

            # Node A broadcasts chat
            node_a.broadcast_chat("Distributed S-Tier Hello!")
            time.sleep(0.5)

            chat_events = [d for t, d in events_b if t == "CHAT"]
            self.assertTrue(len(chat_events) >= 1)
            self.assertEqual(chat_events[0]["payload"]["text"], "Distributed S-Tier Hello!")

            # Verify Lamport clock advanced on Node B
            self.assertTrue(node_b.clock.value >= node_a.clock.value)
        finally:
            node_a.stop()
            node_b.stop()


if __name__ == "__main__":
    unittest.main()
