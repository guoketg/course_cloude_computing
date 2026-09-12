"""Lab 07: loopback-only teaching HTTP service; role is simulated, not authentication."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import threading
import time
from collections import deque

import httpx
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from .common import DATA, OUT, emit, read_json, sha256, write_json
from .intelligence import StaleIndexError, answer, load_index, validate_index

app = FastAPI(title="校园 AI 数据平台（本机教学身份模拟）")
_CACHE: dict[str, dict] = {}
_LOCK = threading.RLock()
_LATENCIES = deque(maxlen=10000)
_METRICS = {"requests": 0, "errors": 0, "cache_hits": 0, "cache_misses": 0}


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    role: Literal["public", "internal"] = "public"


def cache_key(question: str, role: str, data_version: str, index_version: str,
              generator: str = "extractive", stats_version: str = "") -> str:
    identity = [" ".join(question.split()), role, data_version, index_version, generator, stats_version]
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode("utf-8")).hexdigest()


def stats_payload() -> dict:
    path = DATA / "gold" / "realtime_service.json"
    if not path.exists():
        raise HTTPException(503, "缺少实验04实时汇总，请先运行 lab04")
    return {"tool": "service_stats", "data_version": sha256(path), "rows": read_json(path)}


def ask_payload(question: str, role: str = "public") -> dict:
    try:
        index = load_index()  # Hashes are checked on EVERY request, before any cache lookup.
    except StaleIndexError as exc:
        raise HTTPException(409, str(exc)) from exc
    normalized = " ".join(question.split())
    # Fixed allow-list tool, no arbitrary SQL, paths, URLs or externally visible side effects.
    use_stats = normalized in {"查询实时服务统计", "各服务有多少请求"}
    stats = stats_payload() if use_stats else None
    key = cache_key(normalized, role, index["source_sha256"], index["index_version"],
                    stats_version=stats["data_version"] if stats else "")
    with _LOCK:
        if key in _CACHE:
            _METRICS["cache_hits"] += 1
            return {**copy.deepcopy(_CACHE[key]), "cache_hit": True}
    if stats:
        result = {**stats, "role": role, "question": question, "refused": False,
                  "index_version": index["index_version"], "knowledge_data_version": index["source_sha256"]}
    else:
        result = answer(normalized, role, index=index)
    with _LOCK:
        # Bounded teaching cache; replacement is intentionally simple and visible.
        if len(_CACHE) >= 256:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = copy.deepcopy(result)
        _METRICS["cache_misses"] += 1
    return {**result, "cache_hit": False}


@app.middleware("http")
async def measure_request(request, call_next):
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        with _LOCK:
            _METRICS["requests"] += 1
            _METRICS["errors"] += int(status >= 400)
            _LATENCIES.append((time.perf_counter() - start) * 1000)


@app.get("/health")
def health():
    try:
        manifest = validate_index()
    except StaleIndexError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"status": "ready", "index_version": manifest["index_version"],
            "data_version": manifest["source_sha256"], "authentication": "simulated_role_loopback_only"}


@app.post("/ask")
def ask_endpoint(request: AskRequest):
    return ask_payload(request.question, request.role)


@app.get("/stats")
def stats_endpoint():
    return stats_payload()


@app.get("/metrics")
def metrics():
    with _LOCK:
        values = list(_LATENCIES)
        return {**_METRICS, "latency_sample_n": len(values),
                "latency_p50_ms": float(np.percentile(values, 50)) if values else None,
                "latency_p95_ms": float(np.percentile(values, 95)) if values else None,
                "cache_entries": len(_CACHE), "scope": "当前单进程，含健康检查；耗时窗口最多10000请求"}


def lab07(requests: int = 20) -> dict:
    if requests < 2 or requests > 10000:
        raise ValueError("requests must be between 2 and 10000")
    base = os.environ.get("BDP_SERVICE_URL", "http://127.0.0.1:8000")
    latencies, errors, hits, details = [], 0, 0, []
    with httpx.Client(base_url=base, timeout=30) as client:
        health_response = client.get("/health")
        health_response.raise_for_status()
        before = client.get("/metrics").json()
        started = time.perf_counter()
        for i in range(requests):
            question = "查询实时服务统计" if i % 5 == 0 else "学生每周CPU推理配额是多少分钟？"
            tick = time.perf_counter()
            response = client.post("/ask", json={"question": question, "role": "public"})
            elapsed = (time.perf_counter() - tick) * 1000
            latencies.append(elapsed)
            errors += int(response.status_code >= 400)
            body = response.json()
            hits += int(body.get("cache_hit", False))
            details.append({"request_no": i + 1, "question": question,
                            "status": response.status_code, "latency_ms": elapsed, "response": body})
        seconds = time.perf_counter() - started
        after = client.get("/metrics").json()
    report = {"requests": requests, "concurrency": 1, "errors": errors, "error_rate": errors / requests,
              "wall_seconds": seconds, "throughput_requests_per_second": requests / seconds,
              "p50_ms": float(np.percentile(latencies, 50)), "p95_ms": float(np.percentile(latencies, 95)),
              "cache_hits": hits, "cache_hit_rate": hits / requests,
              "server_metrics_before": before, "server_metrics_after": after,
              "health": health_response.json(), "details": details,
              "limitations": "串行本机HTTP测量，不是最大承载量；摘录服务耗时不是LLM推理耗时。"}
    write_json(OUT / "lab07" / "load_test.json", report)
    return emit("07", "http_benchmark", {k: v for k, v in report.items() if k != "details"})
