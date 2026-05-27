"""文档级跨分块实验记录合并。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from app.schemas.extraction import ExtractionItem, MaterialRecord, TextChunk

_PROCESS_FIELDS = (
    "welding_power",
    "welding_speed",
    "defocusing_distance",
    "shielding_gas",
    "shielding_gas_flow_rate",
)
_MECHANICS_FIELDS = ("tensile_strength", "yield_strength", "elongation_rate")
_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{1,}")


@dataclass(slots=True)
class MergeStats:
    merged_count: int = 0
    unmatched_count: int = 0
    process_only_count: int = 0
    mechanics_only_count: int = 0
    complete_count: int = 0


@dataclass(slots=True)
class _RecordNode:
    record: MaterialRecord
    chunk_id: str
    chunk_seq: int
    chapter: str
    source_text: str
    item_index: int
    primary_chunk_id: str

    @property
    def process_count(self) -> int:
        return sum(1 for f in _PROCESS_FIELDS if getattr(self.record, f) is not None)

    @property
    def mechanics_count(self) -> int:
        return sum(1 for f in _MECHANICS_FIELDS if getattr(self.record, f) is not None)

    @property
    def kind(self) -> str:
        has_process = self.process_count > 0
        has_mechanics = self.mechanics_count > 0
        if has_process and has_mechanics:
            return "complete"
        if has_process:
            return "process_only"
        if has_mechanics:
            return "mechanics_only"
        return "complete"


def _chunk_sequence(chunk_id: str) -> int:
    try:
        return int(chunk_id.split("-")[-1])
    except Exception:
        return 0


def _to_token_set(text: str) -> set[str]:
    return {m.group(0).lower() for m in _WORD_RE.finditer(text or "") if len(m.group(0)) >= 3}


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def _match_score(left: _RecordNode, right: _RecordNode, max_chunk_distance: int) -> float:
    distance = abs(left.chunk_seq - right.chunk_seq)
    if distance > max_chunk_distance:
        return -1.0

    score = 0.0
    # 邻近块优先
    score += max(0.0, 2.0 - (distance * 0.6))
    # 同章节优先
    if left.chapter and right.chapter and left.chapter == right.chapter:
        score += 0.8
    # 文本锚点重叠
    overlap = _jaccard(_to_token_set(left.source_text), _to_token_set(right.source_text))
    score += min(1.0, overlap * 5.0)
    # 块内原本完整度信号（字段多的一侧更可信）
    score += min(0.6, left.process_count * 0.1)
    score += min(0.6, right.mechanics_count * 0.2)
    return score


def _with_meta(
    record: MaterialRecord,
    *,
    record_kind: str,
    source_chunk_ids: list[str],
    merge_note: str | None,
) -> MaterialRecord:
    copied = record.model_copy(deep=True)
    copied.record_kind = record_kind  # type: ignore[assignment]
    copied.source_chunk_ids = source_chunk_ids
    copied.merge_note = merge_note
    return copied


def _merge_pair(process_node: _RecordNode, mech_node: _RecordNode) -> MaterialRecord:
    base = process_node.record.model_copy(deep=True)
    for field in _MECHANICS_FIELDS:
        val = getattr(base, field)
        if val is None:
            setattr(base, field, getattr(mech_node.record, field))
    for field in _PROCESS_FIELDS:
        val = getattr(base, field)
        if val is None:
            setattr(base, field, getattr(mech_node.record, field))
    return _with_meta(
        base,
        record_kind="merged",
        source_chunk_ids=sorted(
            {process_node.chunk_id, mech_node.chunk_id},
            key=_chunk_sequence,
        ),
        merge_note="cross-chunk merged by proximity and anchor overlap",
    )


def merge_records(
    relevant_chunks: list[TextChunk],
    items: list[ExtractionItem],
    *,
    max_chunk_distance: int = 2,
    min_match_score: float = 1.4,
) -> tuple[list[ExtractionItem], list[MaterialRecord], MergeStats]:
    """
    将跨 chunk 的工艺参数记录与力学性能记录进行文档级对齐合并。
    返回：合并后的 items、扁平 records、统计信息。
    """
    chunk_meta = {c.chunk_id: c for c in relevant_chunks}
    stats = MergeStats()

    nodes: list[_RecordNode] = []
    for item_idx, item in enumerate(items):
        chunk = chunk_meta.get(item.chunk_id)
        chapter = (chunk.chapter or "").strip() if chunk else ""
        seq = _chunk_sequence(item.chunk_id)
        for record in item.records:
            nodes.append(
                _RecordNode(
                    record=record,
                    chunk_id=item.chunk_id,
                    chunk_seq=seq,
                    chapter=chapter,
                    source_text=item.source_text or "",
                    item_index=item_idx,
                    primary_chunk_id=item.chunk_id,
                )
            )

    complete_nodes = [n for n in nodes if n.kind == "complete"]
    process_nodes = [n for n in nodes if n.kind == "process_only"]
    mech_nodes = [n for n in nodes if n.kind == "mechanics_only"]

    stats.complete_count = len(complete_nodes)
    stats.process_only_count = len(process_nodes)
    stats.mechanics_only_count = len(mech_nodes)

    merged_records: list[tuple[int, int, str, MaterialRecord]] = []
    used_mech: set[int] = set()

    for pn in sorted(process_nodes, key=lambda x: x.chunk_seq):
        best_idx = -1
        best_score = -1.0
        for idx, mn in enumerate(mech_nodes):
            if idx in used_mech:
                continue
            score = _match_score(pn, mn, max_chunk_distance=max_chunk_distance)
            if score > best_score:
                best_score = score
                best_idx = idx
        if best_idx >= 0 and best_score >= min_match_score:
            matched = mech_nodes[best_idx]
            used_mech.add(best_idx)
            merged = _merge_pair(pn, matched)
            merged_records.append((pn.chunk_seq, pn.item_index, pn.primary_chunk_id, merged))
            stats.merged_count += 1
        else:
            merged_records.append(
                (
                    pn.chunk_seq,
                    pn.item_index,
                    pn.primary_chunk_id,
                    _with_meta(
                        pn.record,
                        record_kind="process_only",
                        source_chunk_ids=[pn.chunk_id],
                        merge_note="unmatched process parameters",
                    ),
                )
            )
            stats.unmatched_count += 1

    for idx, mn in enumerate(mech_nodes):
        if idx in used_mech:
            continue
        merged_records.append(
            (
                mn.chunk_seq,
                mn.item_index,
                mn.primary_chunk_id,
                _with_meta(
                    mn.record,
                    record_kind="mechanics_only",
                    source_chunk_ids=[mn.chunk_id],
                    merge_note="unmatched mechanical metrics",
                ),
            )
        )
        stats.unmatched_count += 1

    for cn in complete_nodes:
        merged_records.append(
            (
                cn.chunk_seq,
                cn.item_index,
                cn.primary_chunk_id,
                _with_meta(
                    cn.record,
                    record_kind="complete",
                    source_chunk_ids=[cn.chunk_id],
                    merge_note=None,
                ),
            )
        )

    merged_records.sort(key=lambda x: (x[0], x[1]))

    # 重新按 chunk 组装 items，保持 UI 兼容
    item_map: dict[str, ExtractionItem] = {
        item.chunk_id: item.model_copy(update={"records": []}, deep=True) for item in items
    }
    flat: list[MaterialRecord] = []
    for _seq, _idx, chunk_id, rec in merged_records:
        target = item_map.get(chunk_id)
        if target is None and items:
            target = items[0].model_copy(update={"records": []}, deep=True)
            item_map[chunk_id] = target
        if target is not None:
            target.records.append(rec)
        flat.append(rec)

    merged_items = list(item_map.values())
    merged_items.sort(key=lambda x: _chunk_sequence(x.chunk_id))
    return merged_items, flat, stats

