import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from copy import deepcopy
from coursekit.intelligence import load_index, search
i = load_index()
print("positive_public=", [h["doc_id"] for h in search("缓存键", role="public", k=5, method="tfidf", index=i)])
print("positive_internal=", [h["doc_id"] for h in search("内部维护窗口", role="internal", k=20, method="tfidf", index=i)])
bad = deepcopy(i)
for chunk in bad["chunks"]:
    if chunk["doc_id"] == "maintenance":
        chunk["visibility"] = "partner"
print("unknown_visibility=", [h["doc_id"] for h in search("内部维护窗口", role="internal", k=20, method="tfidf", index=bad)])
