# 实验07附件导航

- [服务源码](../../coursekit/service.py)：真实HTTP、固定统计工具、权限/版本缓存与计量。
- [Dockerfile](../../Dockerfile) 与 [Compose](../../compose.yaml)：同一服务的容器部署描述。
- [完整手册](../实验手册.md)：两个终端、UTF-8请求、指标、故障与容器说明。
- [评分标准](../实验报告提交及评分标准.md)：独立改动、证据和报告结构。

在项目根目录终端A运行 `python -m uvicorn coursekit.service:app --host 127.0.0.1 --port 8000`，终端B运行 `python -m coursekit lab07 --requests 20`；请把python替换为项目 `.venv\Scripts\python.exe`。

学生独立修改缓存容量和固定统计短语。此服务的role由请求模拟，只能本机教学；当前HTTP默认摘录，真实LLM计量沿用实验06，不得混称。
