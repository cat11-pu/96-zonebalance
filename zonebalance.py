"""zonebalance.py：分区迁移（基线：一次全搬）。"""
from __future__ import annotations


class Mover:
    def __init__(self, rate: int = 2):
        self.rate = rate
        self.pending = []
        self.done = []
        self.paused = False
        self.rounds = 0

    def plan(self, partitions) -> dict:
        """基线：把待迁清单记下来，然后一次全搬。"""
        self.pending = list(partitions)
        self.done = list(self.pending)
        self.pending = []
        return {"planned": len(self.done), "remaining": 0}

    def prioritize(self, loads) -> dict:
        raise NotImplementedError("按负载排序还没实现")

    def step(self) -> dict:
        raise NotImplementedError("限速迁移还没实现")

    def pause(self) -> dict:
        raise NotImplementedError("暂停还没实现")

    def resume(self) -> dict:
        raise NotImplementedError("恢复还没实现")

    def stats(self) -> dict:
        return {"rate": self.rate, "pending": len(self.pending), "done": list(self.done),
                "paused": self.paused, "rounds": self.rounds}
