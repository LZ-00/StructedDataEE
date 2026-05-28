from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.main import app
from app.services.distillation import storage


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: "tester"
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_distillation_template_download_header_only(client: TestClient):
    resp = client.get("/api/distillation/training-dataset-template")
    assert resp.status_code == 200
    assert resp.text == "passage,ai_predicted_relations,true_correct,true_total\n"


def test_distillation_upload_csv_success_and_visible_in_options(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    monkeypatch.setattr(storage, "_UPLOADS_DIR", tmp_path / "uploads")
    payload = (
        "passage,ai_predicted_relations,true_correct,true_total\n"
        "样本文本,\"field:value\",1,1\n"
    ).encode("utf-8")
    upload = client.post(
        "/api/distillation/upload-training-dataset",
        files={"file": ("demo.csv", payload, "text/csv")},
    )
    assert upload.status_code == 200
    body = upload.json()
    assert body["success"] is True
    uploaded_id = body["dataset"]["value"]

    options = client.get("/api/distillation/options")
    assert options.status_code == 200
    values = [item["value"] for item in options.json()["training_datasets"]]
    assert uploaded_id in values


def test_distillation_upload_legacy_gold_header_rejected(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    monkeypatch.setattr(storage, "_UPLOADS_DIR", tmp_path / "uploads")
    legacy = (
        "passage,gold_relations,ai_predicted_relations,true_correct,true_total\n"
        "p,g,a,1,1\n"
    ).encode("utf-8")
    resp = client.post(
        "/api/distillation/upload-training-dataset",
        files={"file": ("legacy.csv", legacy, "text/csv")},
    )
    assert resp.status_code == 400
    assert "表头" in resp.json()["detail"]


def test_finetune_upload_jsonl_keeps_latest_three(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    monkeypatch.setattr(storage, "_GENERATED_DIR", tmp_path / "generated")
    generated = tmp_path / "generated"
    generated.mkdir(parents=True, exist_ok=True)

    existing = [
        "finetune_old_a_20260101_000000.jsonl",
        "finetune_old_b_20260101_000001.jsonl",
        "finetune_old_c_20260101_000002.jsonl",
    ]
    for i, name in enumerate(existing):
        p = generated / name
        p.write_text('{"Instruction":"i","Input":"x","Output":"y"}\n', encoding="utf-8")
        os.utime(p, (1700000000 + i, 1700000000 + i))

    payload = b'{"Instruction":"ins","Input":"in","Output":"out"}\n'
    resp = client.post(
        "/api/finetune/upload-training-dataset",
        files={"file": ("new.jsonl", payload, "application/json")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["removed"]) == 1

    files = sorted(generated.glob("finetune_*.jsonl"))
    assert len(files) == 3

    list_resp = client.get("/api/distillation/finetune-datasets")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["datasets"]) == 3
