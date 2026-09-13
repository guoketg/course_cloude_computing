# 实验06附件导航

继续使用同一个BDP工作区和实验05索引，不另建知识库。

- [共享源码](../../coursekit/intelligence.py)：answer、evaluate与真实Ollama调用。
- [完整手册](../实验手册.md)：四类问题、指标、阈值、模型对照和冻结测试。
- [报告要求](../实验报告提交及评分标准.md)：逐题证据、独立改动与人工评审。
- [安装入口](../../README.md)：课前模型依赖与缓存。

标准命令为 `python -m coursekit lab06 --split dev --generator extractive` 和 `--generator ollama`。测试阶段使用 `--split test`。请始终用项目 `.venv\Scripts\python.exe`。

独立作业位于 `answer()` 的证据选择逻辑；不要修改测试标签或把评价结果固定写成 1.0。默认摘录路径不是 LLM；未选择模型路径无需模型状态记录，选择者必须保留真实调用或失败证据。
