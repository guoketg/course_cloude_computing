import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from coursekit.intelligence import evaluate
from coursekit.common import OUT, write_json
rows = []
for threshold in [0.05, 0.13, 0.40]:
    report = evaluate("dev", "extractive", threshold=threshold)
    rows.append({k: report[k] for k in ["threshold", "answerable_accept_rate",
                 "unanswerable_refusal_rate", "decision_accuracy"]})
write_json(OUT / "lab06" / "threshold_sweep_dev.json", rows)
for row in rows:
    print(row)
