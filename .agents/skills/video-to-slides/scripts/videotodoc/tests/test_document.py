from videotodoc.document import _format_ms


class TestFormatMs:
    def test_int_ms(self):
        assert _format_ms(90000) == "01:30"

    def test_float_ms_does_not_crash(self):
        assert _format_ms(90000.0) == "01:30"

    def test_zero(self):
        assert _format_ms(0) == "00:00"

    def test_negative_clamps(self):
        assert _format_ms(-100) == "00:00"
