import json
import os
import tempfile
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

    def test_plan_registers_pending(self):
        mover = Mover()
        self.assertEqual(mover.plan(["p1"]), {"planned": 1, "remaining": 1})
        self.assertEqual(mover.stats()["pending"], 1)

    def test_rate_default(self):
        self.assertEqual(Mover().stats()["rate"], 2)

    def test_stats_shape(self):
        self.assertIn("paused", Mover().stats())

    def test_prioritize_orders_by_load(self):
        mover = Mover()
        mover.plan(["p1", "p2", "p3", "p4"])
        order = mover.prioritize({"p1": 50, "p2": 10, "p3": 90, "p4": 30})
        self.assertEqual(order, ["p3", "p1", "p4", "p2"])

    def test_prioritize_tie_breaks_by_name(self):
        mover = Mover()
        mover.plan(["pb", "pa"])
        self.assertEqual(mover.prioritize({"pa": 5, "pb": 5}), ["pa", "pb"])

    def test_step_respects_rate(self):
        mover = Mover(rate=2)
        mover.plan(["p1", "p2", "p3", "p4", "p5"])
        self.assertEqual(mover.step(), {"migrated": 2, "done": 2})
        self.assertEqual(mover.step(), {"migrated": 2, "done": 4})
        self.assertEqual(mover.step(), {"migrated": 1, "done": 5})
        self.assertEqual(mover.step()["migrated"], 0)

    def test_pause_and_resume(self):
        mover = Mover()
        mover.plan(["p1", "p2", "p3"])
        mover.pause()
        self.assertEqual(mover.step()["migrated"], 0)
        self.assertEqual(mover.stats()["pending"], 3)
        mover.resume()
        self.assertEqual(mover.step()["migrated"], 2)

    def test_conservation_invariant(self):
        mover = Mover(rate=2)
        planned = mover.plan(["p1", "p2", "p3", "p4"])["planned"]
        for _ in range(4):
            mover.step()
            stats = mover.stats()
            self.assertEqual(stats["pending"] + len(stats["done"]), planned)
            self.assertEqual(len(stats["done"]), len(set(stats["done"])))

    def test_persist_and_restore(self):
        mover = Mover()
        mover.plan(["p1", "p2", "p3"])
        mover.step()
        mover.pause()
        with tempfile.TemporaryDirectory() as tmp:
            blob = mover.persist(os.path.join(tmp, "state.json"))
            self.assertTrue(os.path.exists(os.path.join(tmp, "state.json")))
        restored = Mover()
        restored.restore(blob)
        self.assertEqual(restored.pending, ["p3"])
        self.assertEqual(restored.done, ["p1", "p2"])
        self.assertTrue(restored.paused)

    def test_http_plan(self):
        server = serve(0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:%d" % server.server_port
        with urllib.request.urlopen(base + "/plan", data=b'{"partitions": ["p1", "p2"]}',
                                    timeout=5) as response:
            self.assertEqual(json.loads(response.read())["planned"], 2)
        server.shutdown()
