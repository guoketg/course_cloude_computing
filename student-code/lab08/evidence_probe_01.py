import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tempfile import TemporaryDirectory
from coursekit.intelligence import SOURCE, build_index, validate_index, StaleIndexError
with TemporaryDirectory(prefix="bdp08-stale-") as folder:
    source = Path(folder) / "docs.jsonl"
    index = Path(folder) / "index.json"
    source.write_bytes(SOURCE.read_bytes())
    build_index(source, index)
    source.write_bytes(source.read_bytes() + b"\n")
    try:
        validate_index(source, index)
        raise AssertionError("错误：旧索引没有被拒绝")
    except StaleIndexError as error:
        print("EXPECTED_FAILURE:", error)
    build_index(source, index)
    print("RECOVERED:", validate_index(source, index)["index_version"])
