"""候选点生成 + finalize_segment_slides 测试。"""
from videotodoc.slides import _candidate_points
from videotodoc.config import Settings


class TestCandidatePoints:
    def test_interval_as_minimum_gap(self):
        """场景变化点不产生额外候选，只微调间隔内的 capture_ms。"""
        settings = Settings(fallback_interval_sec=30, capture_mode="audit")
        # 密集场景变化：每 2 秒一个
        change_points = [2000, 4000, 6000, 8000, 10000, 12000, 14000, 16000,
                         18000, 20000, 22000, 24000, 26000, 28000]
        points = _candidate_points(change_points, 60000, settings)
        # 60 秒视频，30 秒间隔 → 只有 1 个间隔点 (30s)
        # 30s 附近的场景变化点 (28s) 微调 capture_ms
        assert len(points) == 1
        assert points[0] == 28000  # 最近的场景变化点

    def test_no_scene_changes_uses_pure_interval(self):
        """无场景变化时，纯按间隔生成候选点。"""
        settings = Settings(fallback_interval_sec=30, capture_mode="audit")
        points = _candidate_points([], 120000, settings)
        assert points == [30000, 60000, 90000]

    def test_scene_change_within_gap_refines_capture(self):
        """间隔内的场景变化点微调 capture_ms 到最近的变化点。"""
        settings = Settings(fallback_interval_sec=30, capture_mode="audit")
        # 0-30s 窗口内有一个场景变化在 25s
        change_points = [25000]
        points = _candidate_points(change_points, 60000, settings)
        # 应该有 1 个点：25s（微调后的间隔点）
        assert 25000 in points
        # 30000 不应在 points 中（被 25000 微调替代）
        assert 30000 not in points

    def test_multiple_intervals_with_refinement(self):
        """多个间隔窗口各自独立微调。"""
        settings = Settings(fallback_interval_sec=30, capture_mode="audit")
        change_points = [25000, 55000]  # 30s 窗口和 60s 窗口各一个
        points = _candidate_points(change_points, 90000, settings)
        # 30s → 25s, 60s → 55s
        assert 25000 in points
        assert 55000 in points
        assert 30000 not in points
        assert 60000 not in points
