# 实验07附件导航

- [服务源码](../../coursekit/service.py)：真实HTTP、固定统计工具、权限/版本缓存与计量。
- [Dockerfile](../../Dockerfile) 与 [Compose](../../compose.yaml)：同一服务的容器部署描述。
- [完整手册](../实验手册.md)：两个终端、UTF-8请求、指标、故障与容器说明。
- [评分标准](../实验报告提交及评分标准.md)：独立改动、证据和报告结构。

在项目根目录的终端 A 运行 `.\.venv\Scripts\python.exe -m uvicorn coursekit.service:app --host 127.0.0.1 --port 8000`，终端 B 运行 `.\.venv\Scripts\python.exe -m coursekit lab07 --requests 20`。

请独立增加一条固定统计短语并提交正负例；缓存容量是观察项。此服务的 role 由请求模拟，只在本机实验；当前 HTTP 默认使用摘录生成器，模型计量来自本人实验 06 的 Ollama 结果，两类时间应分列记录。
