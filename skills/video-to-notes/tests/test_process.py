#!/usr/bin/env python3
"""video-to-notes process.py 单元测试

测试可独立验证的纯函数和关键逻辑。
外部命令调用（yt-dlp、ffmpeg、mlx-whisper）不在单元测试范围内。
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# 将脚本目录加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import process  # noqa: E402


class TestSlugify(unittest.TestCase):
    """_slugify 函数测试"""

    def test_removes_dangerous_chars(self):
        """危险字符被替换为下划线"""
        result = process._slugify('hello<>:"/\\|?*world')
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)
        self.assertNotIn(":", result)
        self.assertNotIn('"', result)

    def test_collapses_underscores(self):
        """连续下划线合并为一个"""
        result = process._slugify("a___b")
        self.assertEqual(result, "a_b")

    def test_strips_leading_trailing_underscores(self):
        """首尾下划线被移除"""
        result = process._slugify("_hello_")
        self.assertEqual(result, "hello")

    def test_truncates_to_80_chars(self):
        """超过 80 字符截断"""
        result = process._slugify("a" * 100)
        self.assertLessEqual(len(result), 80)

    def test_empty_string_returns_video(self):
        """空字符串返回默认值 video"""
        result = process._slugify("")
        self.assertEqual(result, "video")

    def test_chinese_preserved(self):
        """中文标题保留（macOS 兼容）"""
        result = process._slugify("期权实盘应该避开的七大误区")
        self.assertIn("期权", result)

    def test_mixed_chinese_english(self):
        """中英混合标题保留"""
        result = process._slugify("Python 入门教程 Lesson 1")
        self.assertIn("Python", result)
        self.assertIn("入门", result)


class TestShortHash(unittest.TestCase):
    """_short_hash 函数测试"""

    def test_returns_12_chars(self):
        """返回 12 字符的 hash"""
        result = process._short_hash("https://example.com/video")
        self.assertEqual(len(result), 12)

    def test_deterministic(self):
        """相同输入返回相同 hash"""
        h1 = process._short_hash("https://example.com/video")
        h2 = process._short_hash("https://example.com/video")
        self.assertEqual(h1, h2)

    def test_different_inputs_different_hashes(self):
        """不同输入返回不同 hash"""
        h1 = process._short_hash("https://example.com/video1")
        h2 = process._short_hash("https://example.com/video2")
        self.assertNotEqual(h1, h2)


class TestFormatBytes(unittest.TestCase):
    """_format_bytes 函数测试"""

    def test_bytes(self):
        self.assertEqual(process._format_bytes(500), "500.0B")

    def test_kibibytes(self):
        result = process._format_bytes(1024)
        self.assertEqual(result, "1.0KiB")

    def test_mebibytes(self):
        result = process._format_bytes(1024 * 1024)
        self.assertEqual(result, "1.0MiB")

    def test_none(self):
        self.assertEqual(process._format_bytes(None), "??")

    def test_zero(self):
        self.assertEqual(process._format_bytes(0), "??")

    def test_negative(self):
        self.assertEqual(process._format_bytes(-1), "??")


class TestFormatSeconds(unittest.TestCase):
    """_format_seconds 函数测试"""

    def test_seconds_only(self):
        self.assertEqual(process._format_seconds(45), "00:45")

    def test_minutes_and_seconds(self):
        self.assertEqual(process._format_seconds(125), "02:05")

    def test_hours(self):
        self.assertEqual(process._format_seconds(3661), "01:01:01")

    def test_none(self):
        self.assertEqual(process._format_seconds(None), "??:??")

    def test_negative(self):
        self.assertEqual(process._format_seconds(-1), "??:??")


class TestGetProxyForUrl(unittest.TestCase):
    """_get_proxy_for_url 函数测试"""

    def test_user_proxy_overrides(self):
        """用户指定代理优先级最高"""
        result = process._get_proxy_for_url("https://example.com", "http://my-proxy:8080")
        self.assertEqual(result, "http://my-proxy:8080")

    def test_env_proxy_map(self):
        """环境变量站点映射生效"""
        import importlib
        old_env = os.environ.get("VIDEO_TO_NOTES_PROXY_MAP")
        try:
            os.environ["VIDEO_TO_NOTES_PROXY_MAP"] = "example.com:127.0.0.1:8080"
            importlib.reload(process)
            result = process._get_proxy_for_url("https://example.com/page")
            self.assertEqual(result, "http://127.0.0.1:8080")
        finally:
            if old_env is not None:
                os.environ["VIDEO_TO_NOTES_PROXY_MAP"] = old_env
            else:
                os.environ.pop("VIDEO_TO_NOTES_PROXY_MAP", None)
            importlib.reload(process)

    def test_no_match_returns_none(self):
        """无匹配返回 None"""
        result = process._get_proxy_for_url("https://youtube.com/watch?v=123")
        self.assertIsNone(result)

    def test_user_proxy_empty_string(self):
        """用户传空字符串视为不用代理"""
        result = process._get_proxy_for_url("https://91nt.com/videos/123", "")
        self.assertEqual(result, "")


class TestCleanup(unittest.TestCase):
    """cleanup 函数测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # 创建模拟产物文件
        for name in ["video.mp4", "audio.wav", "transcript.json", "transcript.txt"]:
            (Path(self.tmpdir) / name).write_text("test", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_cleanup_all_removes_video_and_audio(self):
        """--cleanup all 删除视频和音频，保留转录"""
        cleaned = process.cleanup(Path(self.tmpdir), "all")
        self.assertIn("video.mp4", cleaned)
        self.assertIn("audio.wav", cleaned)
        self.assertNotIn("transcript.json", cleaned)
        self.assertNotIn("transcript.txt", cleaned)
        self.assertFalse((Path(self.tmpdir) / "video.mp4").exists())
        self.assertFalse((Path(self.tmpdir) / "audio.wav").exists())
        self.assertTrue((Path(self.tmpdir) / "transcript.json").exists())
        self.assertTrue((Path(self.tmpdir) / "transcript.txt").exists())

    def test_cleanup_transcript_only_keeps_nothing_but_summary(self):
        """--cleanup transcript-only 只保留 summary.md（虽然本测试中 summary.md 不存在）"""
        cleaned = process.cleanup(Path(self.tmpdir), "transcript-only")
        self.assertIn("video.mp4", cleaned)
        self.assertIn("audio.wav", cleaned)
        self.assertIn("transcript.json", cleaned)
        self.assertIn("transcript.txt", cleaned)
        # 所有文件都应被删除
        for name in ["video.mp4", "audio.wav", "transcript.json", "transcript.txt"]:
            self.assertFalse((Path(self.tmpdir) / name).exists())

    def test_cleanup_returns_cleaned_set(self):
        """cleanup 返回被清理的文件名集合"""
        cleaned = process.cleanup(Path(self.tmpdir), "all")
        self.assertIsInstance(cleaned, set)
        self.assertEqual(len(cleaned), 2)

    def test_cleanup_idempotent(self):
        """重复清理不会报错"""
        process.cleanup(Path(self.tmpdir), "all")
        cleaned = process.cleanup(Path(self.tmpdir), "all")
        # 第二次没有新文件被清理
        self.assertEqual(len(cleaned), 0)


class TestCheckDependencies(unittest.TestCase):
    """check_dependencies 函数测试"""

    @patch("process.run_cmd")
    def test_all_deps_available(self, mock_run_cmd):
        """所有依赖可用时不退出"""
        mock_run_cmd.return_value = None  # 不抛异常
        with patch.dict("sys.modules", {"mlx_whisper": object()}):
            # 不应抛异常
            process.check_dependencies()

    @patch("process.run_cmd")
    def test_missing_yt_dlp_exits(self, mock_run_cmd):
        """缺少 yt-dlp 时退出"""
        mock_run_cmd.side_effect = FileNotFoundError("yt-dlp not found")
        with self.assertRaises(SystemExit) as ctx:
            process.check_dependencies()
        self.assertEqual(ctx.exception.code, 1)

    @patch("process.run_cmd")
    def test_missing_ffmpeg_exits(self, mock_run_cmd):
        """缺少 ffmpeg 时退出"""
        # yt-dlp 检查通过，ffmpeg 失败
        mock_run_cmd.side_effect = [None, FileNotFoundError("ffmpeg not found")]
        with patch.dict("sys.modules", {"mlx_whisper": object()}):
            with self.assertRaises(SystemExit) as ctx:
                process.check_dependencies()
            self.assertEqual(ctx.exception.code, 1)



if __name__ == "__main__":
    unittest.main()
