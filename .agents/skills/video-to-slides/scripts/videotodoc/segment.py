"""时长密度函数 + 分段草案启发式 + confirmed 格式校验。"""
from __future__ import annotations


def capture_interval_for_duration(duration_sec: float) -> int:
    """根据视频时长返回初始截图间隔（秒）。

    duration ≤ 5min  → 15s
    duration ≤ 15min → 20s
    duration ≤ 30min → 30s
    duration > 30min → 40s
    """
    if duration_sec <= 300:
        return 15
    if duration_sec <= 900:
        return 20
    if duration_sec <= 1800:
        return 30
    return 40

from difflib import SequenceMatcher
from typing import Any

from .models import Slide, SlideSet, Transcript

# 步骤词：含这些词的短段强制 keep，不合并
_STEP_WORDS = ("第一步", "第二步", "第三步", "首先", "然后", "接下来", "操作", "步骤", "点击", "输入")


def _text_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _has_step_words(text: str) -> bool:
    return any(w in text for w in _STEP_WORDS)


def generate_pending_segments(
    candidates: SlideSet,
    transcript: Transcript,
    duration_sec: float,
    max_segment_chars: int = 400,
    min_segment_chars: int = 30,
) -> dict[str, Any]:
    """生成分段草案 pending_segments.json 的数据结构。

    启发式规则：
    1. 按候选图 capture_ms 把时间轴切成原始片段
    2. 相邻片段文本相似度 ≥0.85，或时长和 <60s 且无步骤词 → merge
    3. 含步骤词且片段 <20s → 强制 keep，不合并
    4. 单段文字 > max_segment_chars → split
    5. 单段文字 < min_segment_chars 且无独立场景（无候选图）→ merge 到前一段
    """
    interval = capture_interval_for_duration(duration_sec)

    if not transcript.segments:
        return {"video_title": "", "duration_sec": int(duration_sec),
                "capture_interval_sec": interval, "segments": []}

    # 按候选图 capture_ms 切分时间段
    capture_times = sorted({s.capture_ms for s in candidates.slides})
    if not capture_times:
        capture_times = [0]

    boundaries = [0, *capture_times, transcript.segments[-1].end_ms]
    raw_segments = []
    for i in range(len(boundaries) - 1):
        start_ms = boundaries[i]
        end_ms = boundaries[i + 1]
        # 收集该时间段内的 transcript 文本
        texts = [seg.text for seg in transcript.segments
                 if start_ms <= seg.start_ms < end_ms]
        text = "".join(texts)
        if not text:
            continue
        # 该时间段对应的候选图
        slide_ids = [s.slide_index for s in candidates.slides
                     if start_ms <= s.capture_ms < end_ms]
        raw_segments.append({
            "start_ms": start_ms, "end_ms": end_ms,
            "text": text, "slide_ids": slide_ids,
        })

    # 合并相邻片段
    merged = []
    for seg in raw_segments:
        if merged:
            prev = merged[-1]
            combined_text = prev["text"] + seg["text"]
            time_sum = (seg["end_ms"] - prev["start_ms"]) / 1000
            should_merge = (
                _text_similarity(prev["text"], seg["text"]) >= 0.85
                or (time_sum < 60 and not _has_step_words(seg["text"])
                    and not _has_step_words(prev["text"]))
                or (len(seg["text"]) < min_segment_chars and not seg["slide_ids"])
            )
            if should_merge and len(combined_text) <= max_segment_chars:
                prev["end_ms"] = seg["end_ms"]
                prev["text"] = combined_text
                prev["slide_ids"].extend(seg["slide_ids"])
                continue
        merged.append(dict(seg))

    # 生成最终 segment 列表
    segments = []
    for i, seg in enumerate(merged, start=1):
        char_count = len(seg["text"])
        action = "keep"
        extra = {}
        if char_count > max_segment_chars:
            action = "split"
        elif i > 1 and char_count < min_segment_chars and not _has_step_words(seg["text"]) and not seg["slide_ids"]:
            action = "merge"
            extra["merge_into"] = f"s{i - 1:02d}"
        segments.append({
            "id": f"s{i:02d}",
            "start_ms": seg["start_ms"],
            "end_ms": seg["end_ms"],
            "label": seg["text"][:20].strip(),
            "suggested_action": action,
            "candidate_slide_ids": seg["slide_ids"],
            "reason": f"字数{char_count}，时长{(seg['end_ms'] - seg['start_ms']) / 1000:.0f}s",
            "transcript_preview": seg["text"][:80],
            "char_count": char_count,
            **extra,
        })

    return {
        "video_title": "",
        "duration_sec": int(duration_sec),
        "capture_interval_sec": interval,
        "segments": segments,
    }


def validate_confirmed_segments(data: dict[str, Any]) -> bool:
    """校验 agent 写回的 confirmed_segments.json 格式。"""
    segments = data.get("segments")
    if not segments or not isinstance(segments, list):
        return False
    ids = {s.get("id") for s in segments}
    for s in segments:
        if not all(k in s for k in ("id", "start_ms", "end_ms", "label", "suggested_action")):
            return False
        action = s["suggested_action"]
        if action == "merge" and s.get("merge_into") not in ids:
            return False
        if action == "split" and "split_at" not in s:
            return False
    return True
