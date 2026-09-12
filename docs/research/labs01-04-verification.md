# 实验 01—04 文档与附件复核记录

复核日期：2026-09-11，Windows PowerShell，课程 `.venv` / Python 3.12。使用已生成的默认 20,000 条合法独特事件，未改写正式原始数据。此文件记录编写者实际运行，不是学生提交模板。

## 1. 文档完整性

| 实验 | 手册行数 | 独立评分文件 | 附件 |
|---|---:|---|---|
| 01 | 245 | 已提供，合计 100 分 | 对象往返个人副本 |
| 02 | 252 | 已提供，合计 100 分 | 个人质量规则、Gold 核验 |
| 03 | 269 | 已提供，合计 100 分 | 慢请求聚合、错误率专项核验 |
| 04 | 273 | 已提供，合计 100 分 | 状态检查、提前提交对照、独立函数骨架、事务专项核验 |

四份手册合计 39 个 PowerShell 代码块通过 PowerShell Parser 语法检查，0 个语法错误。全部附件 Python 文件通过 `compileall`。主线从仓库根目录执行，使用完整 `.venv` 解释器路径；第一段设置 `PYTHONUTF8=1`，首次安装引用 `requirements.lock.txt`。

这项语法检查不等于所有外部环境都已验证。实际运行覆盖下述附件基线、个人修改路径、错误路径和恢复；真实外部云环境不属于本次验证范围。

## 2. 实际运行结果

### 实验 01

- 原始 `student_object_roundtrip.py` 通过真实本地 HTTP 完成 PUT/GET，源与下载摘要均为 `23c0b20c65b4476c7e541044c09c88cd970bb02191681f804daef0b7ba49f0e8`。
- 在隔离副本中把对象键改为 `students/20260001/raw/demo.json` 后，摘要不变，往返相等仍为 true。
- 将 payload 中 tokens 从 120 改成 121 后，摘要变为 `1d0f0d28612d93ec866d670eab8876e9dfb64d1c2b2cb84ee24fa60d0ee63bec`，下载相等仍为 true。
- 主 CLI 使用 `http://127.0.0.1:1` 时实际返回 `EndpointConnectionError` / Windows 10061，退出码 1；恢复默认临时服务后 `hash_matches=true`、`version_ids_differ=true`。

### 实验 02

- 默认附加阈值 2000：raw=20102、valid_unique=20000、duplicates=100；原始非法 Token 1 条、非法时间 1 条；保留 input_tokens 总和 18015640。
- 个人阈值改为 1200：valid_unique=13405、duplicates=67、policy_input_limit=6628，另外保留原始两类拒绝各 1 条；保留 input_tokens 总和 8110488。守恒为 `13405+67+6628+1+1=20102`。
- 坏样本：负数与布尔值返回 `invalid_input_tokens`，无时区时间返回 `non_utc_time`。
- `inspect_gold.py` 核对 Silver 与 Gold 总量均为 `(20000,18015640,6145862)`，依次为请求数、输入 Token、输出 Token。
- 实际 Parquet 为 20000 行、5 个行组；原始/Silver/Gold 三个 manifest 摘要核验通过。

### 实验 03

- 原始个人脚本在两个独立 Worker 进程上运行，`matches_sql=true`。
- 阈值 1000 的慢请求数：assistant=10589、batch=1519、search=3043；阈值 2000 时分别为 7120、1011、2041。请求数与延迟总和保持不变。
- 新增错误率任务的原始附件尚未包含 `errors/error_rate`；专项核验实际拒绝该未完成状态，符合预期。
- 在编写者隔离副本中完成 Dask/SQL 双路错误统计后，专项独立逐行核验输出 `ERROR_EXTENSION_PASS`。错误计数 assistant=543、batch=78、search=179，总计 800。
- `--workers 0 --partitions 8` 实际被教学资源边界拒绝，退出码 1；恢复 2 Worker / 8 分区后，两个 Worker 和 SQL 一致性通过。
- 最后一次恢复运行会更新 `benchmark-w2-p8.json` 与 `benchmark.json`；此轮主计算约 2.04 秒。此前其他运行耗时不同，手册没有承诺固定耗时或必然加速。

### 实验 04

- `inspect_state.py` 只读访问真实 SQLite，检查到 rows=20002、checkpoint=20002、新事件与晚到事件均存在，数据库聚合与 Gold 一致。
- 默认服务请求数为 assistant=14009、batch=2023、search=3970。
- 提前提交示例的错误基线实际得到 rows_after_failure=1、offset_after_failure=0、atomic_contract_passed=false；将开关改为 False 后得到 0/0/true，恢复与再重放后仍为 1/1。
- 独立函数骨架被专项核验以 `NotImplementedError` 拒绝，符合“尚未完成核心编码”的预期。
- 编写者在被忽略的 `outputs/qa-lab04` 中实现契约后，核验输出 `STUDENT_TRANSACTION_PASS`：初次 2/2，旧批次重放 2/2，提交前失败回滚 2/2，磁盘重开恢复与再重放 3/3，总 Token 为 60。
- 专项核验使用 `contextlib.closing` 确保失败时关闭 SQLite 连接，避免 Windows 的临时数据库文件锁掩盖学生代码的原始异常。该错误路径已复测。

## 3. 发布时应保留的教学边界

- 01 为 Moto 云 API HTTP 模拟，不声称真实云耐久性或容灾。
- 02 为 Parquet 加质量/血缘清单，不声称实现湖仓事务表格式。
- 03 为真实本机多进程，不声称跨机容错；计时明确包含哪些阶段。
- 04 为本地单数据库事务微批，不声称 Kafka exactly-once 或 watermark。
- 03 的新增错误率与 04 的独立事务函数为必须本人编码的环节；原始可运行基线和未完成的专项骨架明确区分。
- 供编写者验证的完成版在 `outputs/qa-*`，不属于学生附件。发布课程包时应按项目忽略/打包规则处理运行产物，避免把教师验证副本当成学生默认答案。
