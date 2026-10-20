import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from coursekit.intelligence import answer, evaluate
from coursekit.common import OUT
qfile = Path(__file__).resolve().parents[2] / "data" / "raw" / "questions.jsonl"
qs = [json.loads(l) for l in qfile.read_text(encoding="utf-8").splitlines() if l.strip()]
dev = [q for q in qs if q.get("split") == "dev"]
d11 = next(q for q in dev if q["qid"] == "d11")
single = next(q for q in dev if q["qid"] == "d01")
for q in (single, d11):
    r = answer(q["question"], role="public", generator="extractive")
    print(q["qid"], "citations=", [c["chunk_id"] for c in r["citations"]], "expected=", q.get("sources") or q.get("source_ids"))
report = evaluate("dev", "extractive")
print({k: report[k] for k in ["answerable_accept_rate", "unanswerable_refusal_rate", "recall_at_k", "citation_exists_rate"] if k in report})
