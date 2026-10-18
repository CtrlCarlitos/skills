"""Regression tests for patch 0001 (Windows pipe reader).

select.select() only accepts sockets on Windows, so run_single_query's
non-Windows read loop (select + os.read on the pipe fd) can't be used there.
On win32 a background thread pumps process.stdout into a queue instead,
which the main loop polls with a timeout the same way select's timeout
worked. This tests that pump directly, independent of sys.platform and
without spawning a real `claude` subprocess.

Run from skills/skill-creator/: python3 -m unittest discover -s tests
"""
import queue
import unittest

from scripts.run_eval import pump_stdout_to_queue


class _FakeStdoutWithRead1:
    """Mimics a buffered pipe object exposing read1(), like subprocess.PIPE."""

    def __init__(self, chunks: list[bytes]):
        self._chunks = list(chunks)

    def read1(self, _size: int) -> bytes:
        return self._chunks.pop(0) if self._chunks else b""


class _FakeStdoutWithOnlyRead:
    """Mimics a stream exposing only read(), to exercise the fallback branch."""

    def __init__(self, chunks: list[bytes]):
        self._chunks = list(chunks)

    def read(self, _size: int) -> bytes:
        return self._chunks.pop(0) if self._chunks else b""


class PumpStdoutToQueueTests(unittest.TestCase):
    def test_pumps_chunks_in_order_then_signals_eof_with_none(self):
        q: queue.Queue = queue.Queue()
        out = _FakeStdoutWithRead1([b"hello ", b"world"])

        pump_stdout_to_queue(out, q)

        self.assertEqual(q.get_nowait(), b"hello ")
        self.assertEqual(q.get_nowait(), b"world")
        self.assertIsNone(q.get_nowait())
        self.assertTrue(q.empty())

    def test_falls_back_to_plain_read_when_read1_is_unavailable(self):
        q: queue.Queue = queue.Queue()
        out = _FakeStdoutWithOnlyRead([b"chunk"])

        pump_stdout_to_queue(out, q)

        self.assertEqual(q.get_nowait(), b"chunk")
        self.assertIsNone(q.get_nowait())

    def test_immediate_eof_still_signals_none(self):
        q: queue.Queue = queue.Queue()
        out = _FakeStdoutWithRead1([])

        pump_stdout_to_queue(out, q)

        self.assertIsNone(q.get_nowait())
        self.assertTrue(q.empty())


if __name__ == "__main__":
    unittest.main()
