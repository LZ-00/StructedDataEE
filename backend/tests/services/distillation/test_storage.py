from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.services.distillation import storage


def test_training_template_header_without_gold():
    assert storage.training_template_csv() == "passage,ai_predicted_relations,true_correct,true_total\n"


def test_validate_training_csv_rejects_legacy_gold_header():
    legacy = (
        "passage,gold_relations,ai_predicted_relations,true_correct,true_total\n"
        "p,g,a,1,1\n"
    ).encode("utf-8")
    with pytest.raises(ValueError):
        storage.validate_training_csv_content(legacy)


def test_validate_finetune_jsonl_requires_triplet_fields():
    payload = b'{"Instruction":"a","Input":"b","Output":"c"}\n'
    assert storage.validate_finetune_jsonl(payload) == 1
    bad = b'{"Instruction":"a","Input":"b"}\n'
    with pytest.raises(ValueError):
        storage.validate_finetune_jsonl(bad)


def test_prune_finetune_datasets_keeps_latest_three(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(storage, "_GENERATED_DIR", tmp_path)
    names = [
        "finetune_a_20260101_000000.jsonl",
        "finetune_b_20260101_000001.jsonl",
        "finetune_c_20260101_000002.jsonl",
        "finetune_d_20260101_000003.jsonl",
    ]
    for i, name in enumerate(names):
        p = tmp_path / name
        p.write_text('{"Instruction":"i","Input":"x","Output":"y"}\n', encoding="utf-8")
        # Ensure deterministic mtime ordering
        os.utime(p, (1700000000 + i, 1700000000 + i))

    removed = storage.prune_finetune_datasets(limit=3)
    assert len(removed) == 1
    remain = [p.name for p in storage.list_finetune_jsonl_candidates()]
    assert len(remain) == 3
