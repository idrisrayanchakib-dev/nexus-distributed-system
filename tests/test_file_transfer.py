import os
import tempfile
import unittest

from nexus.network.file_transfer import FileTransferManager


class TestFileTransfer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.manager = FileTransferManager(download_dir=self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_file_preparation_and_chunking(self):
        # Create a sample binary file of 70 KB (> 2 chunks of 32KB)
        sample_path = os.path.join(self.temp_dir.name, "sample.bin")
        data = os.urandom(70000)
        with open(sample_path, "wb") as f:
            f.write(data)

        meta = self.manager.prepare_file(sample_path)
        self.assertEqual(meta["filename"], "sample.bin")
        self.assertEqual(meta["filesize"], 70000)
        self.assertEqual(meta["total_chunks"], 3)
        self.assertTrue(len(meta["sha256"]) == 64)

        # Simulate receiver receiving chunks
        self.manager.handle_incoming_start(meta, sender_name="Alice")

        # Send chunks 0, 1, 2
        chunk0 = self.manager.read_chunk(sample_path, 0)
        res0 = self.manager.handle_incoming_chunk(
            {"file_id": meta["file_id"], "chunk_index": 0, "chunk_data": chunk0}
        )
        self.assertIsNone(res0)

        chunk1 = self.manager.read_chunk(sample_path, 1)
        res1 = self.manager.handle_incoming_chunk(
            {"file_id": meta["file_id"], "chunk_index": 1, "chunk_data": chunk1}
        )
        self.assertIsNone(res1)

        chunk2 = self.manager.read_chunk(sample_path, 2)
        res2 = self.manager.handle_incoming_chunk(
            {"file_id": meta["file_id"], "chunk_index": 2, "chunk_data": chunk2}
        )
        self.assertIsNotNone(res2)
        self.assertTrue(res2["is_valid"])
        self.assertEqual(res2["sha256"], meta["sha256"])
        self.assertTrue(os.path.exists(res2["filepath"]))


if __name__ == "__main__":
    unittest.main()
