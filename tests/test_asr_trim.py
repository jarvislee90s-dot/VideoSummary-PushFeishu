"""ASR 段驱动截图裁剪 + 跨段去重的单元测试。"""

import unittest
from pathlib import Path
from unittest.mock import patch

from videotodoc.config import Settings
from videotodoc.models import DedupeStats, Slide, SlideSet, Transcript, TranscriptSegment
from videotodoc.slides import (
    _slide_overlaps_segment,
    deduplicate_slides,
    trim_candidates_by_transcript,
)


class SlideOverlapsSegmentTests(unittest.TestCase):
    """测试 _slide_overlaps_segment 辅助函数。"""

    def test_capture_inside_segment(self):
        slide = Slide(1, "a.png", 0, 10000, 5000, 0.8)
        self.assertTrue(_slide_overlaps_segment(slide, 3000, 8000))

    def test_capture_at_segment_start(self):
        slide = Slide(1, "a.png", 0, 10000, 3000, 0.8)
        self.assertTrue(_slide_overlaps_segment(slide, 3000, 8000))

    def test_capture_at_segment_end_excluded(self):
        slide = Slide(1, "a.png", 0, 10000, 8000, 0.8)
        self.assertFalse(_slide_overlaps_segment(slide, 3000, 8000))

    def test_capture_outside_segment(self):
        slide = Slide(1, "a.png", 0, 10000, 5000, 0.8)
        self.assertFalse(_slide_overlaps_segment(slide, 12000, 15000))


class TrimCandidatesByTranscriptTests(unittest.TestCase):
    """测试 trim_candidates_by_transcript 核心逻辑。"""

    def test_trims_multiple_slides_in_same_segment(self):
        """同一 ASR 段内多张候选图，只保留最后一张。"""
        candidates = SlideSet(
            slides=[
                Slide(1, "a.png", 0, 5000, 2000, 0.8),
                Slide(2, "b.png", 5000, 10000, 7000, 0.8),
                Slide(3, "c.png", 10000, 15000, 12000, 0.8),
            ]
        )
        transcript = Transcript(
            backend="mock",
            language="zh",
            segments=[
                TranscriptSegment(0, 10000, "段1", 1.0),
                TranscriptSegment(10000, 15000, "段2", 1.0),
            ],
        )

        result = trim_candidates_by_transcript(
            candidates, transcript,
            video_path=Path("/fake/video.mp4"),
            output_dir=Path("/tmp/test_trim"),
            settings=None,
        )

        self.assertEqual(len(result.slides), 2)
        self.assertEqual(result.slides[0].capture_ms, 7000)
        self.assertEqual(result.slides[1].capture_ms, 12000)

    def test_preserves_one_slide_per_segment(self):
        """每个 ASR 段恰好一张候选图，不需要裁剪。"""
        candidates = SlideSet(
            slides=[
                Slide(1, "a.png", 0, 5000, 3000, 0.8),
                Slide(2, "b.png", 5000, 10000, 8000, 0.8),
            ]
        )
        transcript = Transcript(
            backend="mock",
            language="zh",
            segments=[
                TranscriptSegment(0, 5000, "段1", 1.0),
                TranscriptSegment(5000, 10000, "段2", 1.0),
            ],
        )

        result = trim_candidates_by_transcript(
            candidates, transcript,
            video_path=Path("/fake/video.mp4"),
            output_dir=Path("/tmp/test_trim"),
            settings=None,
        )

        self.assertEqual(len(result.slides), 2)

    def test_empty_transcript_returns_original(self):
        """空转录数据返回原候选集。"""
        candidates = SlideSet(
            slides=[Slide(1, "a.png", 0, 10000, 5000, 0.8)]
        )
        transcript = Transcript(backend="mock", language="zh", segments=[])

        result = trim_candidates_by_transcript(
            candidates, transcript,
            video_path=Path("/fake/video.mp4"),
            output_dir=Path("/tmp/test_trim"),
            settings=None,
        )

        self.assertEqual(len(result.slides), 1)
        self.assertEqual(result.slides[0].image_path, "a.png")

    def test_updates_metadata(self):
        """元数据包含裁剪统计信息。"""
        candidates = SlideSet(
            slides=[Slide(1, "a.png", 0, 10000, 5000, 0.8)]
        )
        transcript = Transcript(
            backend="mock",
            language="zh",
            segments=[TranscriptSegment(0, 10000, "段1", 1.0)],
        )

        result = trim_candidates_by_transcript(
            candidates, transcript,
            video_path=Path("/fake/video.mp4"),
            output_dir=Path("/tmp/test_trim"),
            settings=None,
        )

        self.assertTrue(result.metadata.get("trimmed_by_transcript"))
        self.assertEqual(result.metadata["segment_count"], 1)

    def test_slide_preserves_original_boundaries(self):
        """裁剪后 slide 保留候选图的原始时间边界。"""
        candidates = SlideSet(
            slides=[Slide(1, "a.png", 0, 15000, 7000, 0.8)]
        )
        transcript = Transcript(
            backend="mock",
            language="zh",
            segments=[TranscriptSegment(2000, 12000, "段1", 1.0)],
        )

        result = trim_candidates_by_transcript(
            candidates, transcript,
            video_path=Path("/fake/video.mp4"),
            output_dir=Path("/tmp/test_trim"),
            settings=None,
        )

        self.assertEqual(result.slides[0].start_ms, 0)  # 保留原始 start_ms
        self.assertEqual(result.slides[0].end_ms, 15000)  # 保留原始 end_ms


class DeduplicateSlidesTests(unittest.TestCase):
    """测试 deduplicate_slides 跨段去重逻辑。"""

    def test_empty_candidates(self):
        """空候选集返回空结果。"""
        candidates = SlideSet(slides=[], metadata={})
        settings = Settings()
        result = deduplicate_slides(candidates, settings)
        self.assertEqual(len(result.slides), 0)

    def test_single_slide_preserved(self):
        """单张候选图直接保留。"""
        candidates = SlideSet(
            slides=[Slide(1, "a.png", 0, 5000, 3000, 0.9)],
            metadata={},
        )
        settings = Settings()
        # is_near_duplicate 需要真实图片文件，用 mock 绕过
        result = deduplicate_slides(candidates, settings)
        self.assertEqual(len(result.slides), 1)
        self.assertTrue(result.metadata.get("deduplicated"))

    @patch("videotodoc.slides.is_near_duplicate", return_value=False)
    def test_all_different_preserved(self, mock_dedup):
        """所有图都不同，全部保留。"""
        candidates = SlideSet(
            slides=[
                Slide(1, "a.png", 0, 5000, 3000, 0.9),
                Slide(2, "b.png", 5000, 10000, 8000, 0.9),
                Slide(3, "c.png", 10000, 15000, 12000, 0.9),
            ],
            metadata={},
        )
        settings = Settings()
        result = deduplicate_slides(candidates, settings)
        self.assertEqual(len(result.slides), 3)

    @patch("videotodoc.slides.is_near_duplicate", return_value=True)
    def test_all_duplicates_keeps_last(self, mock_dedup):
        """全部重复，只保留最后一张。"""
        candidates = SlideSet(
            slides=[
                Slide(1, "a.png", 0, 5000, 3000, 0.9),
                Slide(2, "b.png", 5000, 10000, 8000, 0.9),
                Slide(3, "c.png", 10000, 15000, 12000, 0.9),
            ],
            metadata={},
        )
        settings = Settings()
        result = deduplicate_slides(candidates, settings)
        # 所有相邻对都重复，最终只保留 1 张
        self.assertEqual(len(result.slides), 1)
        self.assertEqual(result.slides[0].image_path, "c.png")

    @patch("videotodoc.slides.is_near_duplicate")
    def test_mixed_dedup(self, mock_dedup):
        """部分重复：1≠2, 2=3 → 保留 1 和 3。"""
        mock_dedup.side_effect = [False, True]
        candidates = SlideSet(
            slides=[
                Slide(1, "a.png", 0, 5000, 3000, 0.9),
                Slide(2, "b.png", 5000, 10000, 8000, 0.9),
                Slide(3, "c.png", 10000, 15000, 12000, 0.9),
            ],
            metadata={},
        )
        settings = Settings()
        result = deduplicate_slides(candidates, settings)
        self.assertEqual(len(result.slides), 2)
        self.assertEqual(result.slides[0].image_path, "a.png")
        self.assertEqual(result.slides[1].image_path, "c.png")

    @patch("videotodoc.slides.is_near_duplicate", return_value=True)
    def test_duplicate_inherits_start_ms(self, mock_dedup):
        """重复时后一张继承前一张的 start_ms。"""
        candidates = SlideSet(
            slides=[
                Slide(1, "a.png", 1000, 5000, 3000, 0.9),
                Slide(2, "b.png", 5000, 10000, 8000, 0.9),
            ],
            metadata={},
        )
        settings = Settings()
        result = deduplicate_slides(candidates, settings)
        self.assertEqual(len(result.slides), 1)
        # 保留后一张的 image_path，但继承前一张的 start_ms
        self.assertEqual(result.slides[0].start_ms, 1000)
        self.assertEqual(result.slides[0].image_path, "b.png")


if __name__ == "__main__":
    unittest.main()


class DeduplicateSameImageTests(unittest.TestCase):
    """Critical 3 修复：同一图片路径的多条 slide 不被判为重复合并。"""

    @patch("videotodoc.slides.is_near_duplicate")
    def test_same_image_path_not_merged(self, mock_dedup):
        """两条 slide 指向同一图片，应合并为"一图多段"而非去重丢弃。"""
        candidates = SlideSet(
            slides=[
                Slide(1, "a.png", 0, 5000, 3000, 0.9),
                Slide(2, "a.png", 5000, 10000, 8000, 0.9),  # 同一图片路径
            ],
            metadata={},
        )
        settings = Settings()
        result = deduplicate_slides(candidates, settings)
        # 同一图片路径不调用 is_near_duplicate，直接合并时间范围
        mock_dedup.assert_not_called()
        self.assertEqual(len(result.slides), 1)
        self.assertEqual(result.slides[0].start_ms, 0)
        self.assertEqual(result.slides[0].end_ms, 10000)

    @patch("videotodoc.slides.is_near_duplicate", return_value=True)
    def test_different_image_path_merged(self, mock_dedup):
        """不同图片路径但画面相同，正常去重。"""
        candidates = SlideSet(
            slides=[
                Slide(1, "a.png", 0, 5000, 3000, 0.9),
                Slide(2, "b.png", 5000, 10000, 8000, 0.9),  # 不同图片路径
            ],
            metadata={},
        )
        settings = Settings()
        result = deduplicate_slides(candidates, settings)
        mock_dedup.assert_called_once()
        self.assertEqual(len(result.slides), 1)


class TrimGapsTests(unittest.TestCase):
    """Important 11：ASR 段之间有间隙时的边界测试。"""

    def test_gap_between_segments_drops_candidates(self):
        """ASR 段间隙期间的候选图会被排除。"""
        candidates = SlideSet(
            slides=[
                Slide(1, "a.png", 0, 3000, 2000, 0.8),      # 段1 内
                Slide(2, "b.png", 3000, 7000, 5000, 0.8),    # 间隙期间
                Slide(3, "c.png", 7000, 12000, 9000, 0.8),   # 段2 内
            ]
        )
        transcript = Transcript(
            backend="mock",
            language="zh",
            segments=[
                TranscriptSegment(0, 3000, "段1", 1.0),
                TranscriptSegment(7000, 12000, "段2", 1.0),
            ],
        )

        result = trim_candidates_by_transcript(
            candidates, transcript,
            video_path=Path("/fake/video.mp4"),
            output_dir=Path("/tmp/test_trim"),
            settings=None,
        )

        # 段1 → slide 1 (capture_ms=2000)
        # 间隙 → slide 2 (capture_ms=5000) 被排除
        # 段2 → slide 3 (capture_ms=9000)
        self.assertEqual(len(result.slides), 2)
        self.assertEqual(result.slides[0].image_path, "a.png")
        self.assertEqual(result.slides[1].image_path, "c.png")
