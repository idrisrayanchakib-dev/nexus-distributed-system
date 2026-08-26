import unittest
from nexus.core.clock import LamportClock


class TestLamportClock(unittest.TestCase):

    def test_local_tick_increments(self):
        clock = LamportClock()
        self.assertEqual(clock.value, 0)
        self.assertEqual(clock.tick(), 1)
        self.assertEqual(clock.tick(), 2)
        self.assertEqual(clock.value, 2)

    def test_remote_update_advances_clock(self):
        clock = LamportClock(initial_value=5)
        # Receive a message from a node with Lamport clock = 10
        updated = clock.update(10)
        self.assertEqual(updated, 11)
        self.assertEqual(clock.value, 11)

    def test_remote_update_with_older_clock(self):
        clock = LamportClock(initial_value=15)
        # Receive a message with an older Lamport clock = 8
        updated = clock.update(8)
        self.assertEqual(updated, 16)
        self.assertEqual(clock.value, 16)


if __name__ == "__main__":
    unittest.main()
