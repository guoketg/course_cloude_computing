# 实验05附件导航

本课程使用一个共享运行包，避免每次复制后丢失数据血缘。请返回项目根目录使用 `coursekit/intelligence.py`；不要在本附件目录新建第二份data。

- [运行源码](../../coursekit/intelligence.py)：seed_corpus、latest_documents、chunk_documents、build_index、search。
- [课程安装与入口](../../README.md)：Windows环境、基础与模型依赖。
- [完整实验手册](../实验手册.md)：逐阶段操作及预期结果。
- [报告与评分](../实验报告提交及评分标准.md)：必交证据和评分分母。

标准入口：`python -m coursekit lab05 --mode lexical`，真实语义对照为 `--mode semantic`；实际执行请使用项目 `.venv\Scripts\python.exe`。

附件不再提供一份脱离前四次实验的数据副本。源码已可运行；基础路径学生在 `coursekit/intelligence.py` 的 `search()` 候选过滤处完成未知可见性 fail-closed 改动，并用正常 public/internal 正例和未知标签负例验证。第二种关键词方法、RRF 和切分参数变式为进阶；“只运行现成脚本”不能取得独立操作分。
