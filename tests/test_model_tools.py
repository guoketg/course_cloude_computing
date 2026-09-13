import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from coursekit.intelligence import answer, build_index, embedding_model_selection, local_model_revision
from coursekit.model_config import BGE_MODEL_ID
from coursekit import download_policy
from coursekit.model_config import DEFAULT_OLLAMA_MODEL, ollama_runtime_config
from scripts import artifact_manifest, capture_validation, prepare_embedding, prepare_generation


def test_runtime_defaults_and_explicit_gpu(monkeypatch):
    for name in ("BDP_OLLAMA_MODEL", "BDP_OLLAMA_NUM_GPU", "BDP_OLLAMA_NUM_CTX",
                 "BDP_OLLAMA_NUM_PREDICT", "BDP_OLLAMA_NUM_THREAD"):
        monkeypatch.delenv(name, raising=False)
    baseline = ollama_runtime_config()
    assert baseline["model"] == DEFAULT_OLLAMA_MODEL
    assert baseline["options"] == {
        "temperature": 0, "num_predict": 256, "num_gpu": 0, "num_ctx": 2048, "num_thread": 2
    }
    monkeypatch.setenv("BDP_OLLAMA_NUM_GPU", "12")
    assert ollama_runtime_config()["options"]["num_gpu"] == 12


def test_local_embedding_path_has_stable_public_identity(monkeypatch, tmp_path):
    model_dir = tmp_path / "private-profile" / "bge-small-zh-v1.5"
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("BDP_EMBED_MODEL", str(model_dir))
    monkeypatch.delenv("BDP_EMBED_MODEL_ID", raising=False)
    model_id, location, local = embedding_model_selection()
    assert model_id == BGE_MODEL_ID
    assert location == str(model_dir)
    assert local is True
    assert local_model_revision(location) == hashlib.sha256(
        ("config.json" + hashlib.sha256(b"{}").hexdigest()).encode()
    ).hexdigest()


def test_default_ollama_request_fields(monkeypatch, tmp_path):
    source = tmp_path / "documents.jsonl"
    source.write_text(json.dumps({"doc_id": "quota", "title": "配额", "version": 1,
                                  "visibility": "public", "text": "学生每周配额120分钟。"},
                                 ensure_ascii=False) + "\n", encoding="utf-8")
    index = build_index(source, tmp_path / "index.json")
    chunk_id = index["chunks"][0]["chunk_id"]
    captured = {}

    class Response:
        def __init__(self, body):
            self.body = body

        def raise_for_status(self):
            return None

        def json(self):
            return self.body

    def fake_post(url, json, timeout):
        captured.update(url=url, request=json, timeout=timeout)
        return Response({"message": {"content": f"120分钟 [{chunk_id}]"}, "eval_count": 3})

    monkeypatch.setattr("httpx.post", fake_post)
    monkeypatch.setattr("httpx.get", lambda *args, **kwargs: Response(
        {"models": [{"name": DEFAULT_OLLAMA_MODEL, "digest": "digest"}]}
    ))
    result = answer("学生每周配额是多少分钟？", generator="ollama", index=index)
    assert captured["request"]["model"] == DEFAULT_OLLAMA_MODEL
    assert captured["request"]["think"] is False
    assert captured["request"]["options"]["num_gpu"] == 0
    assert captured["request"]["options"]["num_ctx"] == 2048
    assert result["model_digest"] == "digest"


def test_generation_hash_mismatch_is_rejected(monkeypatch, tmp_path):
    artifact = tmp_path / "model.gguf"
    artifact.write_bytes(b"bad!")
    monkeypatch.setattr(prepare_generation, "GENERATION_GGUF_BYTES", 4)
    monkeypatch.setattr(prepare_generation, "GENERATION_GGUF_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="SHA256 mismatch"):
        prepare_generation.verify_gguf(artifact)


def test_school_generation_url_requires_explicit_host(tmp_path):
    with pytest.raises(ValueError, match="requires at least one --allowed-host"):
        prepare_generation.prepare(
            None, tmp_path / "models", tmp_path / "manifest.json",
            "https://mirror.example.edu.cn/model.gguf", set(),
        )


def test_local_generation_prepare_and_verify(monkeypatch, tmp_path):
    content = b"small-test-gguf"
    source = tmp_path / "source.gguf"
    source.write_bytes(content)
    monkeypatch.setattr(prepare_generation, "GENERATION_GGUF_FILE", "test.gguf")
    monkeypatch.setattr(prepare_generation, "GENERATION_GGUF_BYTES", len(content))
    monkeypatch.setattr(prepare_generation, "GENERATION_GGUF_SHA256", hashlib.sha256(content).hexdigest())
    output = tmp_path / "models"
    manifest = tmp_path / "generation-manifest.json"
    prepare_generation.prepare(source, output, manifest)
    verified = prepare_generation.verify_prepared(output, manifest)
    assert verified["source_kind"] == "local-distribution"
    assert verified["source_revision"] == prepare_generation.GENERATION_SOURCE_REVISION
    assert verified["ollama_tag"] == DEFAULT_OLLAMA_MODEL


def test_local_embedding_prepare_and_verify(monkeypatch, tmp_path):
    source = tmp_path / "bge-source"
    source.mkdir()
    (source / "model.safetensors").write_bytes(b"weights")
    (source / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(prepare_embedding, "BGE_FILES", (
        ("config.json", 2, hashlib.sha256(b"{}").hexdigest()),
        ("model.safetensors", 7, hashlib.sha256(b"weights").hexdigest()),
    ))
    target = tmp_path / "bge"
    manifest = tmp_path / "embedding-manifest.json"
    prepare_embedding.prepare(source, target, manifest, "local", None)
    assert prepare_embedding.verify_directory(target, manifest)["source_kind"] == "local"
    (target / "config.json").write_text("changed", encoding="utf-8")
    with pytest.raises(RuntimeError, match="mismatch"):
        prepare_embedding.verify_directory(target, manifest)


def test_artifact_manifest_rejects_tamper(tmp_path):
    directory = tmp_path / "wheelhouse"
    directory.mkdir()
    wheel = directory / "example.whl"
    wheel.write_bytes(b"wheel")
    manifest = tmp_path / "wheelhouse-manifest.json"
    artifact_manifest.create_manifest(directory, manifest)
    artifact_manifest.verify_manifest(directory, manifest)
    wheel.write_bytes(b"tampered")
    with pytest.raises(RuntimeError, match="SHA256 mismatch"):
        artifact_manifest.verify_manifest(directory, manifest)


def test_domestic_download_rejects_foreign_final_host(monkeypatch, tmp_path):
    class Response(io.BytesIO):
        def geturl(self):
            return "https://huggingface.co/foreign/model.bin"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    class Opener:
        def open(self, request, timeout):
            return Response(b"safe")

    monkeypatch.setattr(download_policy.urllib.request, "build_opener", lambda handler: Opener())
    destination = tmp_path / "artifact.bin"
    with pytest.raises(RuntimeError, match="final host is not approved"):
        download_policy.download_verified(
            "https://modelscope.cn/model.bin", destination, 4,
            hashlib.sha256(b"safe").hexdigest(), {"modelscope.cn"},
        )
    assert not destination.exists()
    assert not destination.with_name("artifact.bin.part").exists()


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


@pytest.mark.parametrize("script", [
    "scripts/prepare_embedding.py", "scripts/prepare_generation.py",
    "scripts/capture_validation.py", "scripts/artifact_manifest.py",
])
def test_direct_script_entrypoints(script):
    result = subprocess.run([sys.executable, script, "--help"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
