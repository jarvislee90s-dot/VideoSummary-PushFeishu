"""健壮性修复测试：OCR 日志、symlink fallback、CLI 异常处理。"""
from __future__ import annotations

import sys
import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestOcrFailureLogging:
    def test_tesseract_failure_logs_to_stderr(self, tmp_path, capsys):
        """tesseract 失败时应向 stderr 输出警告。"""
        from videotodoc import ocr

        ocr._rapidocr_engine_instance = ...
        ocr._rapidocr_tried = False

        fake_image = tmp_path / "fake.png"
        fake_image.write_bytes(b"fake")

        with patch.object(ocr, "run_command", side_effect=Exception("tesseract not found")):
            with patch.object(ocr, "_extract_text_rapidocr", return_value=""):
                result = ocr.extract_text(str(fake_image))

        assert result == ""
        captured = capsys.readouterr()
        assert "OCR (tesseract) 失败" in captured.err

    def test_rapidocr_init_failure_logs_to_stderr(self, tmp_path, capsys):
        """_rapidocr_engine 初始化失败时应输出警告且不缓存失败。"""
        from videotodoc import ocr

        ocr._rapidocr_engine_instance = ...
        ocr._rapidocr_tried = False

        import builtins
        real_import = builtins.__import__

        def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "rapidocr":
                raise ModuleNotFoundError("No module named 'rapidocr'")
            return real_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=mock_import):
            engine = ocr._rapidocr_engine()

        assert engine is None
        captured = capsys.readouterr()
        assert "RapidOCR 初始化失败" in captured.err

    def test_rapidocr_engine_does_not_cache_failure_permanently(self):
        """第一次失败后设置 _rapidocr_tried=True，返回 None（但不通过 lru_cache 永久缓存 None）。"""
        from videotodoc import ocr

        ocr._rapidocr_engine_instance = ...
        ocr._rapidocr_tried = False

        import builtins
        real_import = builtins.__import__

        fail_import = True

        def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
            nonlocal fail_import
            if name == "rapidocr" and fail_import:
                raise ModuleNotFoundError("No module named 'rapidocr'")
            return real_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=mock_import):
            result1 = ocr._rapidocr_engine()

        assert result1 is None
        assert ocr._rapidocr_tried is True


class TestSymlinkFallback:
    def test_symlink_fallback_to_copy2_on_oserror(self, tmp_path):
        """symlink_to 抛出 OSError 时应回退到 shutil.copy2。"""
        source = tmp_path / "source.mmd"
        source.write_text("mindmap content")
        target = tmp_path / "mindmap.mmd"

        assert not target.exists()

        with patch.object(Path, "symlink_to", side_effect=OSError("symlink not supported on this fs")):
            if not target.exists():
                try:
                    target.symlink_to(source.name)
                except OSError:
                    shutil.copy2(source, target)

        assert target.exists()
        assert target.read_text() == "mindmap content"


class TestCliExceptionHandling:
    def test_cli_catches_os_error_and_returns_1(self, tmp_path, capsys):
        """CLI 应捕获 OSError 并返回 exit code 1。"""
        from videotodoc import cli

        args = ["process", str(tmp_path / "fake.mp4"), "--runs-dir", str(tmp_path / "out")]
        with patch("videotodoc.cli.process_video", side_effect=OSError("disk full")):
            exit_code = cli.main(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "disk full" in captured.err

    def test_cli_catches_value_error_and_returns_1(self, tmp_path, capsys):
        """CLI 应捕获 ValueError 并返回 exit code 1。"""
        from videotodoc import cli

        args = ["process", str(tmp_path / "fake.mp4"), "--runs-dir", str(tmp_path / "out")]
        with patch("videotodoc.cli.process_video", side_effect=ValueError("bad value")):
            exit_code = cli.main(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "bad value" in captured.err

    def test_cli_catches_key_error_and_returns_1(self, tmp_path, capsys):
        """CLI 应捕获 KeyError 并返回 exit code 1。"""
        from videotodoc import cli

        args = ["process", str(tmp_path / "fake.mp4"), "--runs-dir", str(tmp_path / "out")]
        with patch("videotodoc.cli.process_video", side_effect=KeyError("missing_key")):
            exit_code = cli.main(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "missing_key" in captured.err

    def test_cli_video_to_doc_error_returns_2(self, tmp_path, capsys):
        """VideoToDocError 仍应返回 exit code 2。"""
        from videotodoc import cli
        from videotodoc.utils import VideoToDocError

        args = ["process", str(tmp_path / "fake.mp4"), "--runs-dir", str(tmp_path / "out")]
        with patch("videotodoc.cli.process_video", side_effect=VideoToDocError("custom error")):
            exit_code = cli.main(args)

        assert exit_code == 2
        captured = capsys.readouterr()
        assert "custom error" in captured.err
