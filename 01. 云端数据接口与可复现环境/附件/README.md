# 实验 01 附件与个人修改

主运行入口位于 `coursekit/pipeline.py`。从课程根目录运行 `.\.venv\Scripts\python.exe -m coursekit lab01`。

本目录的 `student_object_roundtrip.py` 是个人修改练习。先复制到 `submissions/lab01`，再修改 `STUDENT_ID` 和 `make_key()`。随后改变一个 payload 数值并比较哈希，提交源码、与原附件的 diff、真实运行结果。

此脚本使用临时 Moto HTTP 模拟器，退出即停止服务；它不是持久云存储。脚本只处理内置的小型 JSON，个人练习不要改写 `data/raw` 中供后续实验使用的原始数据。

输入：脚本内的小型 JSON。输出：终端中的对象键、原始与下载 SHA-256、相等判定。测试凭据 `testing` 只用于本机模拟，不含真实账号权限。

不提交 `.venv`、缓存或测试服务临时数据。报告结构以同级上层的 `实验报告提交及评分标准.md` 为准。
