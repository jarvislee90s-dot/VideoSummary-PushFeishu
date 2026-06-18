from videotodoc.pipeline import _transcript_from_external


class TestTranscriptFromExternal:
    def test_seconds_float_list(self):
        data = [{"start": 1.5, "end": 3.0, "text": "hi"}, {"start": 3.0, "end": 4.5, "text": "ok"}]
        t = _transcript_from_external(data, "zh")
        assert t.segments[0].start_ms == 1500
        assert t.segments[0].end_ms == 3000
        assert isinstance(t.segments[0].start_ms, int)

    def test_ms_dict_segments(self):
        data = {"segments": [{"start_ms": 1000, "end_ms": 2000, "text": "x"}]}
        t = _transcript_from_external(data, "zh")
        assert t.segments[0].start_ms == 1000

    def test_empty(self):
        assert _transcript_from_external([], "zh").segments == []
