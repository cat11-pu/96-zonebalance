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
        result = mover.plan(["p1"])
        self.assertEqual(result["remaining"], 1)
        self.assertEqual(mover.stats()["pending"], 1)
        self.assertEqual(mover.stats()["done"], [])

    def test_prioritize_orders_by_load(self):
        mover = Mover()
        mover.plan(["p1", "p2", "p3", "p4"])
        order = mover.prioritize({"p1": 50, "p2": 10, "p3": 90, "p4": 30})
        self.assertEqual(order, ["p3", "p1", "p4", "p2"])

    def test_step_respects_rate(self):
        mover = Mover(rate=2)
        mover.plan(["p1", "p2", "p3", "p4"])
        self.assertEqual(mover.step(), {"migrated": 2, "done": 2})
        self.assertEqual(mover.step(), {"migrated": 2, "done": 4})
        self.assertEqual(mover.step(), {"migrated": 0, "done": 4})

    def test_pause_resume(self):
        mover = Mover()
        mover.plan(["p1", "p2", "p3"])
        mover.pause()
        self.assertEqual(mover.step()["migrated"], 0)
        self.assertEqual(mover.stats()["pending"], 3)
        mover.resume()
        self.assertEqual(mover.step()["migrated"], 2)

    def test_persist_restore(self):
        mover = Mover(rate=3)
        mover.plan(["p1", "p2", "p3", "p4"])
        mover.prioritize({"p1": 50, "p2": 10, "p3": 90, "p4": 30})
        mover.step()
        mover.pause()
        with tempfile.TemporaryDirectory() as tmp:
            blob = mover.persist(os.path.join(tmp, "snapshot.json"))
            with open(os.path.join(tmp, "snapshot.json"), encoding="utf-8") as handle:
                self.assertEqual(json.load(handle), blob)
        restored = Mover()
        restored.restore(json.dumps(blob))
        self.assertEqual(restored.stats(), mover.stats())
        self.assertEqual(restored.step()["migrated"], 0)

    def test_conservation_invariant(self):
        mover = Mover(rate=2)
        planned = mover.plan(["p1", "p2", "p3", "p4", "p5"])["planned"]
        for _ in range(4):
            mover.step()
            stats = mover.stats()
            self.assertEqual(len(stats["done"]) + stats["pending"], planned)
            self.assertEqual(len(set(stats["done"])), len(stats["done"]))

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
