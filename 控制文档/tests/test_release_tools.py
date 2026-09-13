import hashlib
import json
from pathlib import Path

import pytest

from scripts import capture_validation, package_course


def test_base_capture_succeeds_without_model_artifacts(tmp_path):
    for relative in capture_validation.BASE_PATHS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"path": relative}), encoding="utf-8")
    target = tmp_path / "captured"
    result = capture_validation.capture("base", tmp_path, target, capture_validation.ROOT)
    report = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    assert report["profile"] == "base"
    assert not any(name in report["packages"] for name in capture_validation.MODEL_PACKAGES)
    assert not (target / "default-model").exists()


def test_base_capture_defaults_to_control_evidence_directory(tmp_path):
    for relative in capture_validation.BASE_PATHS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"path": relative}), encoding="utf-8")
    result = capture_validation.capture("base", tmp_path, model_root=capture_validation.ROOT)
    expected = tmp_path / "控制文档/验证证据/base/manifest.json"
    assert Path(result["manifest"]) == expected
    assert expected.is_file()


def test_student_release_allow_list_excludes_control_and_maintenance_tools():
    relative = [path.relative_to(package_course.ROOT) for path in package_course.course_files()]
    assert not any("控制文档" in path.parts for path in relative)
    docs = {path.as_posix() for path in relative if path.parts[0] == "docs"}
    assert docs == {"docs/Windows环境准备.md", "docs/运行包接口说明.md"}
    scripts = {path.as_posix() for path in relative if path.parts[0] == "scripts"}
    assert scripts == set(package_course.STUDENT_TOOLS)


def test_default_capture_rejects_wrong_imported_digest(monkeypatch, tmp_path):
    gguf_content = b"test-gguf"
    gguf_name = "test.gguf"
    gguf_sha = hashlib.sha256(gguf_content).hexdigest()
    monkeypatch.setattr(capture_validation, "GENERATION_GGUF_FILE", gguf_name)
    monkeypatch.setattr(capture_validation, "GENERATION_GGUF_BYTES", len(gguf_content))
    monkeypatch.setattr(capture_validation, "GENERATION_GGUF_SHA256", gguf_sha)
    gguf = tmp_path / "models/qwen35" / gguf_name
    gguf.parent.mkdir(parents=True)
    gguf.write_bytes(gguf_content)
    modelfile = gguf.parent / "Modelfile"
    modelfile.write_text("FROM ./test.gguf\n", encoding="utf-8")
    generation = {
        "repo_id": capture_validation.GENERATION_REPO_ID,
        "repo_revision": capture_validation.GENERATION_REPO_REVISION,
        "source_repo_id": capture_validation.GENERATION_REPO_ID,
        "source_revision": capture_validation.GENERATION_SOURCE_REVISION,
        "source_reference_url": (
            f"{capture_validation.MODELSCOPE_ENDPOINT}/models/"
            f"{capture_validation.GENERATION_REPO_ID}/resolve/"
            f"{capture_validation.GENERATION_SOURCE_REVISION}/{gguf_name}"
        ),
        "filename": gguf_name,
        "quantization": capture_validation.GENERATION_QUANTIZATION,
        "artifact_bytes": len(gguf_content), "artifact_sha256": gguf_sha,
        "ollama_tag": capture_validation.DEFAULT_OLLAMA_MODEL,
        "ollama_digest": "expected-digest",
        "runtime_defaults": {"think": False, "num_ctx": 2048,
                             "num_predict": 256, "num_gpu": 0},
        "modelfile_sha256": hashlib.sha256(modelfile.read_bytes()).hexdigest(),
    }
    generation_path = tmp_path / "models/generation-manifest.json"
    generation_path.parent.mkdir(exist_ok=True)
    generation_path.write_text(json.dumps(generation), encoding="utf-8")

    bge_content = b"bge"
    bge_sha = hashlib.sha256(bge_content).hexdigest()
    bge_file = tmp_path / "models/bge-small-zh-v1.5/model.safetensors"
    bge_file.parent.mkdir(parents=True)
    bge_file.write_bytes(bge_content)
    directory_revision = hashlib.sha256(("model.safetensors" + bge_sha).encode()).hexdigest()
    embedding = {
        "model_id": capture_validation.BGE_MODEL_ID,
        "upstream_revision": capture_validation.BGE_REVISION,
        "source_revision": capture_validation.BGE_SOURCE_REVISION,
        "files": [{"path": "model.safetensors", "bytes": len(bge_content), "sha256": bge_sha}],
        "directory_revision": directory_revision,
    }
    (tmp_path / "models/embedding-manifest.json").write_text(json.dumps(embedding), encoding="utf-8")

    for relative in capture_validation.BASE_PATHS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    for relative in ("outputs/lab05/retrieval_semantic.json", "outputs/local-model-probe/result.json"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"mode": "semantic", "model_revision": directory_revision}),
                        encoding="utf-8")
    report = {
        "retrieval_mode": "lexical",
        "embedding_model_id": "character-bigram-tfidf",
        "embedding_model_revision": "coursekit-v1",
        "index_version": "same-index",
        "details": [{"result": {"model_id": capture_validation.DEFAULT_OLLAMA_MODEL,
                                  "model_digest": "wrong-digest"}}],
    }
    for name in ("evaluation_dev_ollama.json", "evaluation_test_ollama.json"):
        (tmp_path / "outputs/lab06" / name).write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(RuntimeError, match="digest does not match"):
        capture_validation.validate_default_model(tmp_path)
