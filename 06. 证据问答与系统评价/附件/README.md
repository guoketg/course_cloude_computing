# 实验06附件导航

继续使用同一个BDP工作区和实验05索引，不另建知识库。

- [共享源码](../../coursekit/intelligence.py)：answer、evaluate与真实Ollama调用。
- [完整手册](../实验手册.md)：四类问题、指标、阈值、模型对照和冻结测试。
- [报告要求](../实验报告提交及评分标准.md)：逐题证据、独立改动与人工评审。
- [安装入口](../../README.md)：课前模型依赖与缓存。

标准命令为 `.\.venv\Scripts\python.exe -m coursekit lab06 --split dev --generator extractive`；模型路径把最后一个参数改为 `--generator ollama`，测试阶段把 `--split dev` 改为 `--split test`。

独立作业位于 `answer()` 的证据选择逻辑。测试标签保持冻结，评价结果由实际逐题输出计算。默认摘录路径不调用 LLM；选择模型路径时保留实际调用或失败证据，并记录 model_id 与 digest。
