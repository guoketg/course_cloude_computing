from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from coursekit.intelligence import SOURCE, build_index, validate_index, StaleIndexError
with TemporaryDirectory(prefix="bdp05-") as folder:
    source = Path(folder) / "documents.jsonl"
    target = Path(folder) / "index.json"
    source.write_bytes(SOURCE.read_bytes())
    old = build_index(source, target)
    source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    try:
        validate_index(source, target)
    except StaleIndexError as error:
        print("EXPECTED_FAILURE", error)
    new = build_index(source, target)
    print("version_changed=", old["index_version"] != new["index_version"])
