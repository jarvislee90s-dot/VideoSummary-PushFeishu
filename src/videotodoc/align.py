from __future__ import annotations

from .models import Section, SlideSet, Transcript


def align_sections(slides: SlideSet, transcript: Transcript, sync_offset_ms: int = 0) -> list[Section]:
    """将截图与 ASR 转录按时间轴对齐。

    trim_candidates_by_transcript 已保证每个 ASR 段最多对应一张图。
    若跳过 trim 直接调用此函数（旧流程），仍可能出现同一条转录
    重复贴在多张图上的情况。

    一张图可以对应多条 ASR 段（多段之间没有画面切换，这是正确的）。
    """
    sections: list[Section] = []
    for slide in slides.slides:
        matched_text: list[str] = []
        matched_indexes: list[int] = []
        for index, segment in enumerate(transcript.segments):
            seg_start = segment.start_ms + sync_offset_ms
            seg_end = segment.end_ms + sync_offset_ms
            if _overlaps(slide.start_ms, slide.end_ms, seg_start, seg_end):
                matched_text.append(segment.text)
                matched_indexes.append(index)
        notes: list[str] = []
        if not matched_text:
            matched_text.append("本页无讲解。")
            notes.append("empty_transcript_match")
        sections.append(
            Section(
                slide_index=slide.slide_index,
                image_path=slide.image_path,
                start_ms=slide.start_ms,
                end_ms=slide.end_ms,
                capture_ms=slide.capture_ms,
                transcript="\n\n".join(matched_text),
                segment_indexes=matched_indexes,
                notes=notes,
            )
        )
    return sections


def _overlaps(left_start: int, left_end: int, right_start: int, right_end: int) -> bool:
    return max(left_start, right_start) < min(left_end, right_end)
