# 实验08附件导航

- [治理源码](../../coursekit/governance.py)：七项真实发布检查。
- [检索与版本源码](../../coursekit/intelligence.py)：manifest校验、权限过滤和实际索引。
- [服务源码](../../coursekit/service.py)：缓存身份与HTTP证据。
- [完整手册](../实验手册.md) 与 [评分标准](../实验报告提交及评分标准.md)。

在项目根目录执行 `python -m coursekit lab08`，解释器应为项目 `.venv\Scripts\python.exe`。必须先拥有实验01—07产物；不能只复制一份通过报告代替运行。

个人核心改动为加入 silver_lineage 第八项检查；审核状态对照为观察项。当前发布门禁验证课程本机 extractive 服务；只有选择模型路径者才另外披露本人模型结果和失败。
