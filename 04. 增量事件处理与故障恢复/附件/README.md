# 实验 04 附件

共享运行入口是根目录 `coursekit/pipeline.py` 中的 `apply_batch()` 与 `lab04()`。它把事件和检查点放在一个事务中，并在同一次运行中完成重放、失败回滚、重连恢复和晚到处理。

- `inspect_state.py`：从 `data/state/latest.json` 找到真实数据库，以只读连接核对状态与 Gold 汇总。
- `student_atomicity.py`：故意包含提前提交错误的个人练习。复制到 `submissions/lab04`，先运行收集 `atomic_contract_passed=false`，再将 `COMMIT_EARLY` 改为 `False` 并验证修复。临时数据库不会覆盖主实验状态。
- `student_apply_batch.py`：事务练习 B 的函数骨架，需要你写出事务、批量写入、检查点、提交和异常回滚；未实现时抛出占位异常。
- `check_student_transaction.py`：验证练习 B，覆盖正常写入、旧批次重放不倒退、失败回滚、磁盘重开和恢复。按手册的 `--module` 参数指定个人副本。

按手册从练习 A（修复提前提交）和练习 B（补全事务骨架）中任选一个。提交你的预测、所选源码 diff、失败/恢复结果与事务时间线；选择练习 B 时再提交 `STUDENT_TRANSACTION_PASS`。选择练习 A 时，除修改开关外，还要提交修改前的失败结果和修改后的恢复结果。练习中的预设错误不属于主实验的正常行为，报告中要明确区分。

每次主实验的新数据库位于 `data/state/runs/<run_id>/events.sqlite`；不要把旧版本路径写死到个人脚本，更不要删除整个状态目录。本课程没有实现 Kafka、全局 exactly-once 或 watermark。
