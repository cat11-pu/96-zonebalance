"""zonebalance.py：分区迁移（限速、可暂停、可快照恢复）。"""
from __future__ import annotations

import json

SNAPSHOT_PATH = "zonebalance.snapshot.json"


class Mover:
    def __init__(self, rate: int = 2):
        self.rate = rate
        self.pending = []
        self.done = []
        self.paused = False
        self.rounds = 0

    def plan(self, partitions) -> dict:
        """只登记待迁分区，不直接迁移。"""
        self.pending = list(partitions)
        self.done = []
        return {"planned": len(self.pending), "remaining": len(self.pending)}

    def prioritize(self, loads) -> list:
        """按负载降序（同负载按分区名升序）排列待迁分区，返回优先级顺序。"""
        self.pending.sort(key=lambda name: (-loads.get(name, 0), name))
        return list(self.pending)

    def step(self) -> dict:
        """每轮最多迁移 rate 个分区；暂停期间不迁移。"""
        if self.paused:
            return {"migrated": 0, "done": len(self.done)}
        batch = self.pending[: self.rate]
        del self.pending[: self.rate]
        self.done.extend(batch)
        self.rounds += 1
        return {"migrated": len(batch), "done": len(self.done)}

    def pause(self) -> dict:
        self.paused = True
        return {"paused": True}

    def resume(self) -> dict:
        self.paused = False
        return {"paused": False}

    def persist(self, path: str = SNAPSHOT_PATH) -> dict:
        """快照落盘，并返回快照内容。"""
        blob = {
            "rate": self.rate,
            "pending": list(self.pending),
            "done": list(self.done),
            "paused": self.paused,
            "rounds": self.rounds,
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(blob, handle)
        return blob

    def restore(self, blob) -> dict:
        """从快照（dict 或 JSON 字符串）恢复待迁清单、已迁集合与暂停状态。"""
        if isinstance(blob, (str, bytes)):
            blob = json.loads(blob)
        self.rate = blob.get("rate", self.rate)
        self.pending = list(blob.get("pending", []))
        self.done = list(blob.get("done", []))
        self.paused = bool(blob.get("paused", False))
        self.rounds = blob.get("rounds", 0)
        return self.stats()

    def stats(self) -> dict:
        return {"rate": self.rate, "pending": len(self.pending), "done": list(self.done),
                "paused": self.paused, "rounds": self.rounds}
