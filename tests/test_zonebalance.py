import json
import threading
import unittest
import urllib.error
import urllib.request

from zonebalance import Mover
from server import serve

class TestMover(unittest.TestCase):
    def test_plan_moves_all(self):
        mover = Mover()
        self.assertEqual(mover.plan(["p1", "p2"])["planned"], 2)

    def test_plan_clears_pending(self):
        mover = Mover()
        mover.plan(["p1"])
        self.assertEqual(mover.stats()["pending"], 0)

    def test_rate_default(self):
        self.assertEqual(Mover().stats()["rate"], 2)

    def test_stats_shape(self):
        self.assertIn("paused", Mover().stats())

    def test_http_plan(self):
        server = serve(0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:%d" % server.server_port
        with urllib.request.urlopen(base + "/plan", data=b'{"partitions": ["p1", "p2"]}',
                                    timeout=5) as response:
            self.assertEqual(json.loads(response.read())["planned"], 2)
        server.shutdown()
