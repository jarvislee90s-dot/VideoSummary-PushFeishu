"""Task 8: refine_selected_slides 并行化顺序保持测试。"""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from videotodoc.config import Settings
from videotodoc.models import Slide
from videotodoc.slides import refine_selected_slides


def _make_test_image(path: Path, color: tuple = (255, 255, 255)) -> None:
    img = Image.new("RGB", (100, 100), color=color)
    img.save(path)


class TestRefineParallel:
    def test_refine_preserves_order(self, tmp_path):
        """并行 refine 后 slide_index 严格递增，结果顺序与输入一致。"""
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"fake video")
        output_dir = tmp_path / "refined"
        output_dir.mkdir()

        num_slides = 6
        input_slides = []
        for i in range(num_slides):
            input_slides.append(Slide(
                slide_index=i + 1,
                image_path=str(tmp_path / f"input_{i:04d}.png"),
                start_ms=i * 5000,
                end_ms=(i + 1) * 5000,
                capture_ms=i * 5000 + 4000,
                confidence=0.7,
            ))

        def mock_choose_capture_time(vp, start_ms, end_ms, settings, candidates_dir=None):
            return (start_ms + 4500, 0.9)

        def mock_extract_frame(vp, capture_ms, output_path, precise=True):
            _make_test_image(output_path, (128, 128, 128))

        with patch("videotodoc.slides.choose_capture_time", side_effect=mock_choose_capture_time), \
             patch("videotodoc.slides.extract_frame", side_effect=mock_extract_frame):
            result = refine_selected_slides(video_path, input_slides, output_dir, Settings())

        assert len(result) == num_slides
        for i, slide in enumerate(result):
            assert slide.slide_index == i + 1, f"slide_index 应从1连续递增，但第{i}个为{slide.slide_index}"
            assert slide.start_ms == i * 5000
            assert slide.end_ms == (i + 1) * 5000
            assert Path(slide.image_path).name == f"{i + 1:04d}.png"
            assert slide.confidence == 0.9

    def test_refine_parallel_speed(self, tmp_path):
        """带延迟的 choose_capture_time/extract_frame 并行执行应快于串行。"""
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"fake video")
        output_dir = tmp_path / "refined"
        output_dir.mkdir()

        num_slides = 5
        delay = 0.1
        input_slides = [
            Slide(slide_index=i + 1, image_path=str(tmp_path / f"in_{i}.png"),
                  start_ms=i * 3000, end_ms=(i + 1) * 3000,
                  capture_ms=i * 3000 + 2500, confidence=0.7)
            for i in range(num_slides)
        ]

        def mock_choose(vp, s, e, settings, cd=None):
            time.sleep(delay)
            return (s + 2800, 0.9)

        def mock_extract(vp, cm, op, precise=True):
            _make_test_image(op, (100, 100, 100))

        with patch("videotodoc.slides.choose_capture_time", side_effect=mock_choose), \
             patch("videotodoc.slides.extract_frame", side_effect=mock_extract):
            start = time.time()
            result = refine_selected_slides(video_path, input_slides, output_dir, Settings())
            elapsed = time.time() - start

        serial_time = delay * num_slides
        assert elapsed < serial_time * 0.7, (
            f"并行 refine 应快于串行（串行≈{serial_time:.2f}s，实际={elapsed:.2f}s）"
        )
        assert len(result) == num_slides
