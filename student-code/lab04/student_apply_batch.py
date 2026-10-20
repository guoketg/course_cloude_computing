"""实验 04 独立编码骨架：在个人副本实现函数，不要修改专项核验器。"""


def apply_student(con, rows, next_offset, fail_before_commit=False):
    """将一批事件与检查点原子提交，返回实际新增条数。

    con: sqlite3.Connection，初始没有正在进行的事务。
    rows: 已校验的 (id, tokens) 元组列表，重复 ID 内容相同。
    next_offset: 本顺序批次处理后的逻辑位置，旧批次重放不得让 offset 倒退。
    fail_before_commit: 真时，在提交前抛 RuntimeError('INJECTED_FAILURE_BEFORE_COMMIT')。

    表结构：events(id TEXT PRIMARY KEY,tokens INTEGER)；
            checkpoint(id INTEGER PRIMARY KEY,offset INTEGER)，已有 id=1 的一行。
    必须显式 BEGIN，事件与 checkpoint 同事务，成功 COMMIT，异常 ROLLBACK 后继续抛出。
    允许使用 SQL 参数化与 INSERT OR IGNORE；不要修改表结构或核验器。
    """
    con.execute("BEGIN")
    try:
        cursor = con.executemany(
            "INSERT OR IGNORE INTO events(id,tokens) VALUES(?,?)", rows
        )
        inserted = cursor.rowcount
        # MAX 保证旧批次重放时 offset 不倒退
        con.execute(
            "UPDATE checkpoint SET offset=MAX(offset,?) WHERE id=1", (next_offset,)
        )
        if fail_before_commit:
            raise RuntimeError("INJECTED_FAILURE_BEFORE_COMMIT")
        con.commit()
        return inserted
    except Exception:
        con.rollback()
        raise
