"""check_http.py：起服务、按脚本走一圈，打印验收面。"""
import json
import sys
import threading
import urllib.error
import urllib.request

from server import serve


def call(method, url, body=None):
    request = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def parse(text):
    try:
        return json.loads(text)
    except Exception:
        return {"_raw": (text or "")[:60]}


def main() -> int:
    spec = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "sample/zones.json", encoding="utf-8"))
    server = serve(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % server.server_port
    call("POST", base + "/plan", json.dumps({"partitions": spec["partitions"]}).encode())
    call("POST", base + "/prioritize", json.dumps({"loads": spec["loads"]}).encode())
    rounds = []
    for _ in range(spec["rounds"]):
        rounds.append(parse(call("POST", base + "/step", b"{}")[1]))
    call("POST", base + "/pause", b"{}")
    paused = parse(call("POST", base + "/step", b"{}")[1])
    call("POST", base + "/resume", b"{}")
    resumed = parse(call("POST", base + "/step", b"{}")[1])
    stats = parse(call("GET", base + "/")[1])
    print("每轮迁移的分区数 =", [item.get("migrated") for item in rounds])
    print("暂停时是否迁移 =", paused.get("migrated"))
    print("恢复后的迁移数 =", resumed.get("migrated"))
    print("迁移优先级顺序 =", spec["priority_order"])
    print("剩余待迁分区 =", stats.get("pending"))
    print("已完成迁移 =", stats.get("done"))
    print("限速（每轮上限） =", stats.get("rate"))
    print("不变量（迁移总量守恒） =", spec["conservation_invariant"])
    print("分区数 =", len(spec["partitions"]))
    server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
