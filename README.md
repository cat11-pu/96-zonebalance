# zonebalance

纯 Python 标准库的本机服务。

## 起服务

    python3 server.py 8000

浏览器打开 http://127.0.0.1:8000/ 看结果。

接口：`POST /plan` 登记待迁分区，`POST /prioritize` 按负载定优先级，
`POST /step` 限速迁移（每轮最多 rate 个），`POST /pause` / `POST /resume`
控制开关，`POST /persist` / `POST /restore` 做快照与恢复。

## 测试

    python3 -m unittest discover -s tests -v

## 验收自检

    python3 check_http.py
