# 实验 03 附件

正式入口为根目录 `coursekit/pipeline.py` 的 `lab03()`，通过 `python -m coursekit lab03 --workers 2 --partitions 8` 运行。

`student_latency_aggregate.py` 是必做个人改动：复制到 `submissions/lab03`，先将慢请求阈值从 1000 改成 2000，再本人新增每服务 `errors/error_rate` 的 Dask 与 SQL 实现。保存完整源码 diff、预测与实际输出。它真正启动两个 Worker 进程，在主入口保护内执行，使用独立 SQL 检查结果。

`check_error_extension.py --threshold 2000` 逐行读取 Silver，独立验证学生新增的错误统计。原始附件尚未实现新字段，专项核验会提示缺少字段；学生完成独立编码后应通过。不得修改核验器冒充完成。

输入是正式 Silver Parquet，输出为 `outputs/lab03/student-latency-<阈值>.json`。不改写正式数据。运行须使用课程 `.venv` 解释器，保留文件所在的两层目录关系。

性能判断须分清集群启动、主计算与诊断时间；PID、耗时和任务图大小不能照抄示例。更多 Worker 未必更快，结果正确与证据真实是评分依据。
